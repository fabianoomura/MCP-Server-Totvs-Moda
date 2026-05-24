"""
Aggregator Tools
================
High-level tools that compose multiple TOTVS API calls + aggregation
to answer common business questions in a single LLM turn.

Each tool here replaces what would otherwise require 3-6 sequential
API calls + manual aggregation by the model. Benefits:

1. Deterministic output shape — model doesn't guess field names
2. Small response — already aggregated, not raw lists of thousands
3. Clear semantic — one tool per business question

None of these contain company-specific logic. They answer questions
that any fashion/apparel retailer using TOTVS Moda would ask.
"""
import logging
import asyncio
from collections import defaultdict
from datetime import datetime, date, timedelta
from typing import Any

from totvs_client import TotvsClient
from tools._defaults import (
    get_default_cost_codes,
    get_default_price_codes,
    get_default_stock_codes,
    get_purchase_order_open_statuses,
    inject_branch_defaults,
)
import response_cache as cache

logger = logging.getLogger("totvs-moda-mcp.aggregators")

BASE_SALES = "/api/totvsmoda/sales-order/v2"
BASE_PRODUCT = "/api/totvsmoda/product/v2"
BASE_AR = "/api/totvsmoda/accounts-receivable/v2"
BASE_AP = "/api/totvsmoda/accounts-payable/v2"
BASE_PO = "/api/totvsmoda/purchase-order/v2"
BASE_PROD_ORDER = "/api/totvsmoda/production-order/v2"
BASE_FISCAL = "/api/totvsmoda/fiscal/v2"
BASE_ENG = "/api/totvsmoda/product-engineering/v2"


def _parse_iso_date(s: str) -> datetime:
    """Parse ISO date string tolerant to both 'YYYY-MM-DD' and 'YYYY-MM-DDTHH:MM:SS'."""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return datetime.strptime(s[:10], "%Y-%m-%d")


class AggregatorTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def _safe(self, coro: Any) -> Any:
        try:
            return await coro
        except Exception as exc:
            return {"error": str(exc)}

    @staticmethod
    def _items(resp: Any) -> list[dict[str, Any]]:
        return resp.get("items", []) if isinstance(resp, dict) else []

    @staticmethod
    def _count_collection(resp: Any, *keys: str) -> int:
        if isinstance(resp, list):
            return len(resp)
        if isinstance(resp, dict):
            for key in ("items", *keys):
                if isinstance(resp.get(key), list):
                    return len(resp[key])
        return 0

    async def get_products_sold(self, args: dict[str, Any]) -> Any:
        """Agrega vendas de produtos em um período.

        Args:
            startDate (required): "YYYY-MM-DD"
            endDate (required): "YYYY-MM-DD"
            branchCodeList (optional): filtrar por filial(is)
            categoryCode (optional): filtrar por categoria
            topN (optional, default 10): limitar aos N mais vendidos
            orderBy (optional, default "quantity"): "quantity" | "value"

        Returns:
            {
              "period": {"start": "...", "end": "..."},
              "totalOrders": N,
              "topProducts": [
                {"productCode": int, "name": str, "totalQuantity": float,
                 "totalValue": float, "orderCount": int}
              ]
            }
        """
        args = inject_branch_defaults(args)
        start = args["startDate"]
        end = args["endDate"]
        top_n = args.get("topN", 10)
        order_by = args.get("orderBy", "quantity")

        flt: dict[str, Any] = {"startOrderDate": start, "endOrderDate": end}
        if args.get("branchCodeList"):
            flt["branchCodeList"] = args["branchCodeList"]

        body = {
            "filter": flt,
            "expand": "items",
            "page": 1,
            "pageSize": 500,
        }

        orders_response = await self.client.post(f"{BASE_SALES}/orders/search", body)
        orders = orders_response.get("items", []) if isinstance(orders_response, dict) else []

        aggregated: dict[int, dict[str, Any]] = defaultdict(
            lambda: {"productCode": 0, "name": "", "totalQuantity": 0.0, "totalValue": 0.0, "orderCount": 0}
        )
        order_count_per_product: dict[int, set[Any]] = defaultdict(set)

        for order in orders:
            order_code = order.get("orderCode")
            for item in order.get("items", []):
                pc = item.get("productCode")
                if pc is None:
                    continue
                qty = float(item.get("quantity", 0) or 0)
                price = float(item.get("price", 0) or 0)
                name = item.get("name") or item.get("productName") or ""
                if args.get("categoryCode") and item.get("categoryCode") != args["categoryCode"]:
                    continue
                agg = aggregated[pc]
                agg["productCode"] = pc
                agg["name"] = name or agg["name"]
                agg["totalQuantity"] += qty
                agg["totalValue"] += qty * price
                order_count_per_product[pc].add(order_code)

        for pc, ocs in order_count_per_product.items():
            aggregated[pc]["orderCount"] = len(ocs)

        sort_key = "totalValue" if order_by == "value" else "totalQuantity"
        top = sorted(aggregated.values(), key=lambda x: x[sort_key], reverse=True)[:top_n]

        return {
            "period": {"start": start, "end": end},
            "totalOrders": len(orders),
            "topProducts": top,
        }

    async def sales_summary_by_period(self, args: dict[str, Any]) -> Any:
        """Resumo de vendas agregado por filial, status ou dia.

        Args:
            startDate, endDate (required): "YYYY-MM-DD"
            groupBy (optional, default "branch"): "branch" | "status" | "day"
            branchCodeList (optional)

        Returns:
            {
              "period": {...},
              "totalValue": float,
              "totalOrders": int,
              "groups": [
                {"key": "...", "label": "...", "orderCount": N, "totalValue": N}
              ]
            }
        """
        args = inject_branch_defaults(args)
        start = args["startDate"]
        end = args["endDate"]
        group_by = args.get("groupBy", "branch")

        flt: dict[str, Any] = {"startOrderDate": start, "endOrderDate": end}
        if args.get("branchCodeList"):
            flt["branchCodeList"] = args["branchCodeList"]

        body = {"filter": flt, "page": 1, "pageSize": 500}
        orders_response = await self.client.post(f"{BASE_SALES}/orders/search", body)
        orders = orders_response.get("items", []) if isinstance(orders_response, dict) else []

        groups: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"key": "", "label": "", "orderCount": 0, "totalValue": 0.0}
        )
        total_value = 0.0

        for order in orders:
            if group_by == "branch":
                key = str(order.get("branchCode", ""))
                label = f"Filial {key}"
            elif group_by == "status":
                key = str(order.get("statusOrder", "unknown"))
                label = key
            elif group_by == "day":
                date = order.get("orderDate", "")[:10]
                key = date
                label = date
            else:
                key = "all"
                label = "All"

            value = float(order.get("totalAmountOrder", 0) or 0)
            g = groups[key]
            g["key"] = key
            g["label"] = label
            g["orderCount"] += 1
            g["totalValue"] += value
            total_value += value

        return {
            "period": {"start": start, "end": end},
            "groupBy": group_by,
            "totalValue": total_value,
            "totalOrders": len(orders),
            "groups": sorted(groups.values(), key=lambda x: x["totalValue"], reverse=True),
        }

    async def top_customers(self, args: dict[str, Any]) -> Any:
        """Top N clientes por faturamento em um período.

        Args:
            startDate, endDate (required)
            topN (optional, default 10)
            branchCodeList (optional)

        Returns:
            {
              "period": {...},
              "customers": [
                {"customerCode": int, "customerName": str, "customerCpfCnpj": str,
                 "orderCount": int, "totalValue": float, "averageOrderValue": float}
              ]
            }
        """
        args = inject_branch_defaults(args)
        start = args["startDate"]
        end = args["endDate"]
        top_n = args.get("topN", 10)

        flt: dict[str, Any] = {"startOrderDate": start, "endOrderDate": end}
        if args.get("branchCodeList"):
            flt["branchCodeList"] = args["branchCodeList"]

        body = {"filter": flt, "page": 1, "pageSize": 500}
        orders_response = await self.client.post(f"{BASE_SALES}/orders/search", body)
        orders = orders_response.get("items", []) if isinstance(orders_response, dict) else []

        by_customer: dict[Any, dict[str, Any]] = defaultdict(
            lambda: {"customerCode": 0, "customerName": "", "customerCpfCnpj": "",
                     "orderCount": 0, "totalValue": 0.0}
        )

        for order in orders:
            cc = order.get("customerCode")
            if cc is None:
                continue
            c = by_customer[cc]
            c["customerCode"] = cc
            c["customerName"] = order.get("customerName", c["customerName"])
            c["customerCpfCnpj"] = order.get("customerCpfCnpj", c["customerCpfCnpj"])
            c["orderCount"] += 1
            c["totalValue"] += float(order.get("totalAmountOrder", 0) or 0)

        for c in by_customer.values():
            c["averageOrderValue"] = c["totalValue"] / c["orderCount"] if c["orderCount"] else 0

        top = sorted(by_customer.values(), key=lambda x: x["totalValue"], reverse=True)[:top_n]
        return {"period": {"start": start, "end": end}, "customers": top}

    async def low_stock_alert(self, args: dict[str, Any]) -> Any:
        """Produtos com saldo abaixo de um threshold.

        Args:
            threshold (required): quantidade mínima
            branchCode (required): filial para consulta de estoque
            productCodeList (optional): restringir a produtos específicos
            topN (optional, default 50): máximo de produtos a retornar

        Returns:
            {
              "threshold": N,
              "branchCode": N,
              "lowStockCount": N,
              "products": [
                {"productCode": int, "name": str, "balance": float,
                 "productSku": str}
              ]
            }
        """
        args = inject_branch_defaults(args)
        threshold = args["threshold"]
        branch = args["branchCode"]
        top_n = args.get("topN", 50)

        flt: dict[str, Any] = {}
        if args.get("productCodeList"):
            flt["productCodeList"] = args["productCodeList"]

        body = {
            "filter": flt,
            "option": {"balances": [{"branchCode": branch, "stockCodeList": get_default_stock_codes()}]},
            "page": 1,
            "pageSize": 500,
        }
        response = await self.client.post(f"{BASE_PRODUCT}/balances/search", body)
        items = response.get("items", []) if isinstance(response, dict) else []

        low = []
        for item in items:
            balance = float(item.get("balance", 0) or 0)
            if balance < threshold:
                low.append({
                    "productCode": item.get("productCode"),
                    "name": item.get("name", "") or item.get("productName", ""),
                    "productSku": item.get("productSku", ""),
                    "balance": balance,
                })

        low.sort(key=lambda x: x["balance"])
        return {
            "threshold": threshold,
            "branchCode": branch,
            "lowStockCount": len(low),
            "products": low[:top_n],
        }

    async def orders_by_status_summary(self, args: dict[str, Any]) -> Any:
        """Contagem e valor de pedidos por status em um período.

        Args:
            startDate, endDate (required)
            branchCodeList (optional)

        Returns:
            {
              "period": {...},
              "totalOrders": N,
              "totalValue": N,
              "byStatus": [
                {"status": str, "orderCount": int, "totalValue": float, "percentage": float}
              ]
            }
        """
        args = inject_branch_defaults(args)
        start = args["startDate"]
        end = args["endDate"]

        flt: dict[str, Any] = {"startOrderDate": start, "endOrderDate": end}
        if args.get("branchCodeList"):
            flt["branchCodeList"] = args["branchCodeList"]

        body = {"filter": flt, "page": 1, "pageSize": 500}
        orders_response = await self.client.post(f"{BASE_SALES}/orders/search", body)
        orders = orders_response.get("items", []) if isinstance(orders_response, dict) else []

        by_status: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"status": "", "orderCount": 0, "totalValue": 0.0}
        )
        total_value = 0.0

        for order in orders:
            status = str(order.get("statusOrder", "unknown"))
            value = float(order.get("totalAmountOrder", 0) or 0)
            s = by_status[status]
            s["status"] = status
            s["orderCount"] += 1
            s["totalValue"] += value
            total_value += value

        status_list = list(by_status.values())
        for s in status_list:
            s["percentage"] = (s["totalValue"] / total_value * 100) if total_value else 0

        status_list.sort(key=lambda x: x["totalValue"], reverse=True)
        return {
            "period": {"start": start, "end": end},
            "totalOrders": len(orders),
            "totalValue": total_value,
            "byStatus": status_list,
        }

    # ------------------------------------------------------------------
    # daily_dashboard
    # ------------------------------------------------------------------
    async def daily_dashboard(self, args: dict[str, Any]) -> Any:
        """Painel do dia: vendas + contas a receber + contas a pagar.

        Faz 3 consultas internas em paralelo e retorna tudo num único objeto.

        Args:
            date (optional): "YYYY-MM-DD", default=hoje
            branchCodeList (optional)

        Returns:
            {date, sales: {totalOrders, totalValue, orders: [{orderCode, integrationCode,
             customerName, statusOrder, totalAmountOrder}], byStatus: [{status, count, value}]},
             receivable: {count, totalValue, items: [{customerCpfCnpj, installmentValue, bearerName}]},
             payable: {count, totalOpen, totalPaid, open: [{expenseName, dueDate, duplicateValue}],
                       paid: [{expenseName, dueDate, duplicateValue}]}}
        """
        import asyncio
        args = inject_branch_defaults(args)
        target = args.get("date") or date.today().isoformat()
        branches = args.get("branchCodeList", [1])

        async def _sales():
            flt: dict[str, Any] = {"startOrderDate": target, "endOrderDate": target}
            if branches:
                flt["branchCodeList"] = branches
            body = {"filter": flt, "page": 1, "pageSize": 500}
            resp = await self.client.post(f"{BASE_SALES}/orders/search", body)
            orders = resp.get("items", []) if isinstance(resp, dict) else []
            by_status: dict[str, dict] = defaultdict(lambda: {"status": "", "count": 0, "value": 0.0})
            order_list = []
            total = 0.0
            for o in orders:
                val = float(o.get("totalAmountOrder", 0) or 0)
                total += val
                st = str(o.get("statusOrder", ""))
                s = by_status[st]
                s["status"] = st
                s["count"] += 1
                s["value"] += val
                order_list.append({
                    "orderCode": o.get("orderCode"),
                    "integrationCode": o.get("integrationCode"),
                    "customerName": o.get("customerName"),
                    "statusOrder": st,
                    "totalAmountOrder": val,
                })
            return {
                "totalOrders": len(orders),
                "totalValue": total,
                "orders": sorted(order_list, key=lambda x: x["totalAmountOrder"], reverse=True),
                "byStatus": sorted(by_status.values(), key=lambda x: x["value"], reverse=True),
            }

        async def _receivable():
            body = {
                "filter": {
                    "branchCodeList": branches,
                    "startExpiredDate": target,
                    "endExpiredDate": target,
                    "statusList": [1],
                    "hasOpenInvoices": True,
                },
                "page": 1, "pageSize": 100,
            }
            resp = await self.client.post(f"{BASE_AR}/documents/search", body)
            items = resp.get("items", []) if isinstance(resp, dict) else []
            total = sum(float(i.get("installmentValue", i.get("documentValue", 0)) or 0) for i in items)
            return {
                "count": len(items),
                "totalValue": total,
                "items": [
                    {
                        "customerCpfCnpj": i.get("customerCpfCnpj"),
                        "customerName": i.get("customerName"),
                        "documentCode": i.get("documentCode") or i.get("receivableCode"),
                        "dueDate": (i.get("expiredDate") or i.get("dueDate") or "")[:10],
                        "installmentValue": float(i.get("installmentValue", i.get("documentValue", 0)) or 0),
                        "paidValue": float(i.get("paidValue", 0) or 0),
                        "bearerName": i.get("bearerName"),
                    }
                    for i in items
                ],
            }

        async def _payable():
            end_expired = (date.fromisoformat(target[:10]) + timedelta(days=1)).isoformat()
            body = {
                "filter": {
                    "branchCodeList": branches,
                    "startExpiredDate": target,
                    "endExpiredDate": end_expired,
                    "status": "Normal",
                },
                "page": 1, "pageSize": 100,
            }
            resp = await self.client.post(f"{BASE_AP}/duplicates/search", body)
            items = resp.get("items", []) if isinstance(resp, dict) else []
            open_items = []
            paid_items = []
            total_open = 0.0
            total_paid = 0.0
            for i in items:
                val = float(i.get("duplicateValue", 0) or 0)
                paid = float(i.get("paidValue", 0) or 0)
                expense = i.get("expense", [{}])
                expense_name = expense[0].get("expenseName", "") if expense else ""
                entry = {
                    "expenseName": expense_name,
                    "dueDate": (i.get("dueDate") or "")[:10],
                    "duplicateValue": val,
                }
                if paid >= val and val > 0:
                    paid_items.append(entry)
                    total_paid += val
                else:
                    open_items.append(entry)
                    total_open += val
            return {
                "count": len(items),
                "totalOpen": total_open,
                "totalPaid": total_paid,
                "open": sorted(open_items, key=lambda x: x["duplicateValue"], reverse=True),
                "paid": sorted(paid_items, key=lambda x: x["duplicateValue"], reverse=True),
            }

        cache_key = {"fn": "daily_dashboard", "date": target, "branches": branches}
        cached = cache.get("dashboard", cache_key, cache.SALES)
        if cached is not None:
            return cached

        sales, receivable, payable = await asyncio.gather(
            self._safe(_sales()),
            self._safe(_receivable()),
            self._safe(_payable()),
        )
        result = {"date": target, "sales": sales, "receivable": receivable, "payable": payable}
        cache.put("dashboard", cache_key, result)
        return result

    # ------------------------------------------------------------------
    # customer_360
    # ------------------------------------------------------------------
    async def customer_360(self, args: dict[str, Any]) -> Any:
        """Visão 360 do cliente: dados + histórico de pedidos + recompra.

        Args:
            customerCode (optional): código do cliente
            customerCpfCnpj (optional): CPF/CNPJ do cliente
            (pelo menos um é obrigatório)

        Returns:
            {customer: {code, name, cpfCnpj}, orders: {count, totalValue,
             firstOrder, lastOrder, items: [{orderCode, orderDate, totalAmountOrder,
             statusOrder}]}, isRepeatBuyer: bool, averageTicket: float}
        """
        import asyncio
        code = args.get("customerCode")
        cpf = args.get("customerCpfCnpj")

        # Buscar pedidos do cliente
        flt: dict[str, Any] = {"startOrderDate": "2020-01-01", "endOrderDate": date.today().isoformat()}
        if code:
            flt["customerCodeList"] = [code] if not isinstance(code, list) else code
        elif cpf:
            flt["customerCpfCnpjList"] = [cpf] if not isinstance(cpf, list) else cpf
        else:
            return {"error": "customerCode ou customerCpfCnpj obrigatório"}

        body = {"filter": flt, "page": 1, "pageSize": 500, "order": "-orderDate"}
        resp = await self.client.post(f"{BASE_SALES}/orders/search", body)
        orders = resp.get("items", []) if isinstance(resp, dict) else []

        cache_key = {"fn": "customer_360", "code": code, "cpf": cpf}
        cached = cache.get("customer360", cache_key, cache.CATALOG)
        if cached is not None:
            return cached

        if not orders:
            return {"customer": {"code": code, "cpfCnpj": cpf}, "orders": {"count": 0}, "isRepeatBuyer": False}

        first = orders[-1]
        customer_info = {
            "code": first.get("customerCode"),
            "name": first.get("customerName"),
            "cpfCnpj": first.get("customerCpfCnpj"),
        }

        order_list = []
        total_value = 0.0
        for o in orders:
            val = float(o.get("totalAmountOrder", 0) or 0)
            total_value += val
            order_list.append({
                "orderCode": o.get("orderCode"),
                "orderDate": (o.get("orderDate") or "")[:10],
                "totalAmountOrder": val,
                "statusOrder": o.get("statusOrder"),
                "integrationCode": o.get("integrationCode"),
            })

        result = {
            "customer": customer_info,
            "orders": {
                "count": len(orders),
                "totalValue": total_value,
                "firstOrder": order_list[-1]["orderDate"],
                "lastOrder": order_list[0]["orderDate"],
                "items": order_list,
            },
            "isRepeatBuyer": len(orders) > 1,
            "averageTicket": total_value / len(orders) if orders else 0,
        }
        cache.put("customer360", cache_key, result)
        return result

    # ------------------------------------------------------------------
    # stock_available
    # ------------------------------------------------------------------
    async def stock_available(self, args: dict[str, Any]) -> Any:
        """Produtos com estoque disponível (saldo > 0), já filtrado.

        Pagina internamente e retorna apenas SKUs com stock > 0.

        Args:
            branchCode (optional, default 1)
            referenceCodeList (optional): filtrar por referências
            productCodeList (optional): filtrar por códigos
            productKind (optional): all | finished | raw_material | bulk
            onlyActive (optional, default true for productKind != all)
            minStock (optional, default 1): saldo mínimo para incluir

        Returns:
            {branchCode, totalSkus, totalUnits, products: [{productCode,
             productName, colorName, sizeName, stock, salesOrder}]}
        """
        args = inject_branch_defaults(args)
        branch = args.get("branchCode", 1)
        min_stock = args.get("minStock", 1)
        product_kind = args.get("productKind", "all")
        only_active = args.get("onlyActive")
        if only_active is None:
            only_active = product_kind != "all"

        cache_key = {"fn": "stock_available", "branch": branch, "min": min_stock,
                     "products": args.get("productCodeList"), "refs": args.get("referenceCodeList"),
                     "productKind": product_kind, "onlyActive": only_active}
        cached = cache.get("stock", cache_key, cache.STOCK)
        if cached is not None:
            return cached

        flt: dict[str, Any] = {}
        if args.get("productCodeList"):
            flt["productCodeList"] = args["productCodeList"]
        if args.get("referenceCodeList"):
            flt["referenceCodeList"] = args["referenceCodeList"]
        branch_info: dict[str, Any] = {"branchCode": branch}
        if only_active is not None:
            branch_info["isActive"] = bool(only_active)
        if product_kind == "finished":
            branch_info.update({"isFinishedProduct": True, "isRawMaterial": False, "isBulkMaterial": False})
        elif product_kind == "raw_material":
            branch_info.update({"isRawMaterial": True})
        elif product_kind == "bulk":
            branch_info.update({"isBulkMaterial": True})
        elif product_kind != "all":
            return {"error": "productKind must be one of: all, finished, raw_material, bulk"}
        if len(branch_info) > 1:
            flt["branchInfo"] = branch_info

        all_products = []
        body = {
            "filter": flt,
            "option": {"balances": [{"branchCode": branch, "stockCodeList": get_default_stock_codes()}]},
        }
        items, pages = await self._fetch_all_pages(
            f"{BASE_PRODUCT}/balances/search",
            body,
            page_size=int(args.get("pageSize", 1000)),
            concurrency=int(args.get("concurrency", 10)),
            max_pages=int(args.get("maxPages", 100)),
        )

        for item in items:
            balances = item.get("balances", [])
            stock = float(balances[0].get("stock", 0)) if balances else 0
            sales_order = balances[0].get("salesOrder") if balances else None
            if stock >= min_stock:
                all_products.append({
                    "productCode": item.get("productCode"),
                    "productName": item.get("productName", ""),
                    "colorName": item.get("colorName", ""),
                    "sizeName": item.get("sizeName", ""),
                    "stock": stock,
                    "salesOrder": float(sales_order) if sales_order else 0,
                })

        all_products.sort(key=lambda x: x["productName"])
        total_units = sum(p["stock"] for p in all_products)

        result = {
            "branchCode": branch,
            "productKind": product_kind,
            "onlyActive": only_active,
            "totalSkus": len(all_products),
            "totalUnits": total_units,
            "pageStats": {"pages": pages, "pageSize": int(args.get("pageSize", 1000)), "concurrency": int(args.get("concurrency", 10))},
            "products": all_products,
        }
        cache.put("stock", cache_key, result)
        return result

    async def product_360(self, args: dict[str, Any]) -> Any:
        """Product overview in one call: base data, stock, prices, costs and engineering."""
        args = inject_branch_defaults(args)
        code = args.get("productCode") or args.get("code")
        if code is None:
            return {"error": "productCode is required"}

        branch = args.get("branchCode", 1)
        price_codes = args.get("priceCodeList") or get_default_price_codes()
        cost_codes = args.get("costCodeList") or get_default_cost_codes()
        stock_codes = args.get("stockCodeList") or get_default_stock_codes()
        page_size = int(args.get("pageSize", 100))

        cache_key = {
            "fn": "product_360",
            "productCode": code,
            "branch": branch,
            "priceCodeList": price_codes,
            "costCodeList": cost_codes,
            "stockCodeList": stock_codes,
            "pageSize": page_size,
        }
        cached = cache.get("product360_full", cache_key, cache.STOCK)
        if cached is not None:
            return cached

        product_task = self.client.get(f"{BASE_PRODUCT}/products/{code}/{branch}")
        balance_task = self.client.post(f"{BASE_PRODUCT}/balances/search", {
            "filter": {"productCodeList": [code]},
            "option": {"balances": [{"branchCode": branch, "stockCodeList": stock_codes}]},
            "page": 1,
            "pageSize": page_size,
        })
        price_task = self.client.post(f"{BASE_PRODUCT}/prices/search", {
            "filter": {"productCodeList": [code]},
            "option": {"prices": [{
                "branchCode": branch,
                "priceCodeList": [int(c) for c in price_codes],
                "page": 1,
                "pageSize": page_size,
            }]},
        })
        cost_task = self.client.post(f"{BASE_PRODUCT}/costs/search", {
            "filter": {
                "productCodeList": [code],
                "hasCost": True,
                "branchCostCodeList": [branch],
                "costCodeList": [int(c) for c in cost_codes],
            },
            "option": {"costs": [{"branchCode": branch, "costCodeList": [int(c) for c in cost_codes]}]},
            "page": 1,
            "pageSize": page_size,
        })
        composition_task = self.client.post(f"{BASE_PRODUCT}/compositions", {
            "filter": {"productCodeList": [code]},
            "page": 1,
            "pageSize": page_size,
        })
        consumption_task = self.client.post(f"{BASE_ENG}/consumption-sheet/search", {
            "productCodeList": [code],
            "page": 1,
            "pageSize": page_size,
        })

        product, balances, prices, costs, compositions, consumption = await asyncio.gather(
            self._safe(product_task),
            self._safe(balance_task),
            self._safe(price_task),
            self._safe(cost_task),
            self._safe(composition_task),
            self._safe(consumption_task),
        )

        balance_items = self._items(balances)
        cost_items = self._items(costs)
        price_items = self._items(prices)
        result = {
            "productCode": code,
            "branchCode": branch,
            "product": product,
            "summary": {
                "balanceItems": len(balance_items),
                "priceItems": len(price_items),
                "costItems": len(cost_items),
                "compositionItems": len(self._items(compositions)),
                "consumptionItems": len(self._items(consumption)),
            },
            "balances": balances,
            "prices": prices,
            "costs": costs,
            "compositions": compositions,
            "consumptionSheet": consumption,
        }
        cache.put("product360_full", cache_key, result)
        return result

    async def raw_material_360(self, args: dict[str, Any]) -> Any:
        """Raw material overview plus consumption-sheet usage."""
        args = inject_branch_defaults(args)
        code = args.get("rawMaterialCode") or args.get("productCode") or args.get("code")
        if code is None:
            return {"error": "rawMaterialCode is required"}

        result = await self.product_360({**args, "productCode": code})
        usage = await self._safe(self.client.post(f"{BASE_ENG}/consumption-sheet/search", {
            "rawMaterialCodeList": [code],
            "materialCodeList": [code],
            "page": 1,
            "pageSize": int(args.get("pageSize", 100)),
        }))
        result["rawMaterialCode"] = code
        result["usageInConsumptionSheet"] = usage
        result["summary"]["usageItems"] = len(self._items(usage))
        return result

    async def order_360(self, args: dict[str, Any]) -> Any:
        """Sales order overview: header/items, invoices and pending items."""
        explicit_branch = args.get("branchCode")
        args = inject_branch_defaults(args)
        order_code = args.get("orderCode")
        if order_code is None:
            return {"error": "orderCode is required"}

        branch = explicit_branch
        cache_key = {"fn": "order_360", "orderCode": order_code, "branchCode": branch}
        cached = cache.get("order360_full", cache_key, cache.SALES)
        if cached is not None:
            return cached

        order_filter: dict[str, Any] = {"orderCodeList": [order_code]}
        if args.get("branchCodeList"):
            order_filter["branchCodeList"] = args["branchCodeList"]
        order_resp = await self.client.post(f"{BASE_SALES}/orders/search", {
            "filter": order_filter,
            "expand": args.get("expand", "items"),
            "page": 1,
            "pageSize": 10,
        })
        order_items = self._items(order_resp)
        if not order_items:
            return {"orderCode": order_code, "order": order_resp, "found": False}

        order = order_items[0]
        branch = branch or order.get("branchCode") or order.get("orderBranchCode") or 1
        params = {"branchCode": branch, "orderCode": order_code}
        invoices, pending = await asyncio.gather(
            self._safe(self.client.get(f"{BASE_SALES}/invoices", params=params)),
            self._safe(self.client.get(f"{BASE_SALES}/pending-items", params=params)),
        )
        result = {
            "orderCode": order_code,
            "branchCode": branch,
            "found": True,
            "order": order_resp,
            "invoices": invoices,
            "pendingItems": pending,
            "summary": {
                "invoiceCount": self._count_collection(invoices, "invoices"),
                "pendingItemCount": self._count_collection(pending),
            },
        }
        cache.put("order360_full", cache_key, result)
        return result

    async def invoice_360(self, args: dict[str, Any]) -> Any:
        """Fiscal invoice overview: invoice header and products."""
        args = inject_branch_defaults(args)
        invoice_code = args.get("invoiceCode") or args.get("code")
        invoice_sequence = args.get("invoiceSequence")
        if invoice_code is None and invoice_sequence is None:
            return {"error": "invoiceCode or invoiceSequence is required"}

        flt: dict[str, Any] = {"branchCodeList": args.get("branchCodeList", [1])}
        if invoice_code is not None:
            flt["invoiceCodeList"] = [invoice_code]
        if invoice_sequence is not None:
            flt["invoiceSequenceList"] = [invoice_sequence]

        cache_key = {"fn": "invoice_360", "filter": flt}
        cached = cache.get("invoice360_full", cache_key, cache.FINANCIAL)
        if cached is not None:
            return cached

        invoice_task = self.client.post(f"{BASE_FISCAL}/invoices/search", {
            "filter": flt,
            "page": 1,
            "pageSize": args.get("pageSize", 20),
        })
        products_task = self.client.post(f"{BASE_FISCAL}/invoice-products/search", {
            "filter": flt,
            "page": 1,
            "pageSize": args.get("productPageSize", 100),
        })
        invoice, products = await asyncio.gather(self._safe(invoice_task), self._safe(products_task))
        result = {
            "invoiceCode": invoice_code,
            "invoiceSequence": invoice_sequence,
            "invoice": invoice,
            "products": products,
            "summary": {
                "invoiceCount": len(self._items(invoice)),
                "productCount": len(self._items(products)),
            },
        }
        cache.put("invoice360_full", cache_key, result)
        return result

    async def sales_today_summary(self, args: dict[str, Any]) -> Any:
        """Fast sales summary for one date."""
        args = inject_branch_defaults(args)
        target = args.get("date") or date.today().isoformat()
        branches = args.get("branchCodeList", [1])
        top_n = int(args.get("topN", 50))
        body = {
            "filter": {"branchCodeList": branches, "startOrderDate": target, "endOrderDate": target},
            "page": 1,
            "pageSize": int(args.get("pageSize", 500)),
        }
        cache_key = {"fn": "sales_today_summary", "date": target, "branches": branches, "topN": top_n}
        cached = cache.get("sales_today_summary", cache_key, cache.SALES)
        if cached is not None:
            return cached

        resp = await self.client.post(f"{BASE_SALES}/orders/search", body)
        orders = self._items(resp)
        by_status: dict[str, dict[str, Any]] = defaultdict(lambda: {"status": "", "count": 0, "totalValue": 0.0})
        total = 0.0
        compact = []
        for order in orders:
            value = float(order.get("totalAmountOrder", 0) or 0)
            status = str(order.get("statusOrder", ""))
            total += value
            group = by_status[status]
            group["status"] = status
            group["count"] += 1
            group["totalValue"] += value
            compact.append({
                "orderCode": order.get("orderCode"),
                "customerCode": order.get("customerCode"),
                "customerName": order.get("customerName"),
                "statusOrder": status,
                "totalAmountOrder": value,
            })
        result = {
            "date": target,
            "branchCodeList": branches,
            "totalOrders": len(orders),
            "totalValue": total,
            "byStatus": sorted(by_status.values(), key=lambda x: x["totalValue"], reverse=True),
            "orders": sorted(compact, key=lambda x: x["totalAmountOrder"], reverse=True)[:top_n],
        }
        cache.put("sales_today_summary", cache_key, result)
        return result

    async def new_customers_today(self, args: dict[str, Any]) -> Any:
        """Customers whose first known purchase happened on the target date."""
        args = inject_branch_defaults(args)
        target = args.get("date") or date.today().isoformat()
        branches = args.get("branchCodeList", [1])
        lookback_start = args.get("lookbackStartDate", "2020-01-01")
        concurrency = max(1, min(int(args.get("concurrency", 10)), 20))

        today_resp = await self.client.post(f"{BASE_SALES}/orders/search", {
            "filter": {"branchCodeList": branches, "startOrderDate": target, "endOrderDate": target},
            "page": 1,
            "pageSize": int(args.get("pageSize", 500)),
        })
        today_orders = self._items(today_resp)
        by_customer: dict[Any, dict[str, Any]] = {}
        for order in today_orders:
            code = order.get("customerCode")
            if code is None:
                continue
            entry = by_customer.setdefault(code, {
                "customerCode": code,
                "customerName": order.get("customerName"),
                "customerCpfCnpj": order.get("customerCpfCnpj"),
                "todayOrderCount": 0,
                "todayTotalValue": 0.0,
            })
            entry["todayOrderCount"] += 1
            entry["todayTotalValue"] += float(order.get("totalAmountOrder", 0) or 0)

        sem = asyncio.Semaphore(concurrency)

        async def _history_count(customer_code: Any) -> tuple[Any, int]:
            async with sem:
                resp = await self.client.post(f"{BASE_SALES}/orders/search", {
                    "filter": {
                        "branchCodeList": branches,
                        "customerCodeList": [customer_code],
                        "startOrderDate": lookback_start,
                        "endOrderDate": target,
                    },
                    "page": 1,
                    "pageSize": 1,
                })
            count = int(resp.get("count") or len(self._items(resp))) if isinstance(resp, dict) else 0
            return customer_code, count

        histories = await asyncio.gather(*(_history_count(code) for code in by_customer))
        new_codes = {code for code, count in histories if count == by_customer[code]["todayOrderCount"]}
        customers = [by_customer[code] for code in new_codes]
        result = {
            "date": target,
            "branchCodeList": branches,
            "lookbackStartDate": lookback_start,
            "todayCustomerCount": len(by_customer),
            "newCustomerCount": len(customers),
            "customers": sorted(customers, key=lambda x: x["todayTotalValue"], reverse=True),
        }
        return result

    async def _fetch_all_pages(
        self,
        path: str,
        base_body: dict[str, Any],
        *,
        page_size: int,
        concurrency: int,
        max_pages: int = 100,
    ) -> tuple[list[dict[str, Any]], int]:
        page_size = max(1, min(int(page_size or 100), 1000))
        concurrency = max(1, min(int(concurrency or 10), 20))
        max_pages = max(1, int(max_pages or 100))

        async def _fetch(page: int) -> list[dict[str, Any]]:
            body = {**base_body, "page": page, "pageSize": page_size}
            resp = await self.client.post(path, body)
            return resp.get("items", []) if isinstance(resp, dict) else []

        first_body = {**base_body, "page": 1, "pageSize": page_size}
        first = await self.client.post(path, first_body)
        if not isinstance(first, dict):
            return [], 1

        items = list(first.get("items", []) or [])
        count = int(first.get("count") or first.get("totalItems") or len(items))
        total_pages = first.get("totalPages")
        if total_pages is None:
            total_pages = ((count + page_size - 1) // page_size) if count else 1
        total_pages = max(1, min(int(total_pages), max_pages))

        if total_pages <= 1:
            return items, total_pages

        sem = asyncio.Semaphore(concurrency)

        async def _guarded_fetch(page: int) -> list[dict[str, Any]]:
            async with sem:
                return await _fetch(page)

        pages = await asyncio.gather(*(_guarded_fetch(page) for page in range(2, total_pages + 1)))
        for page_items in pages:
            items.extend(page_items)
        return items, total_pages

    async def open_purchase_orders(self, args: dict[str, Any]) -> Any:
        """Fast summary of open purchase orders using parallel pagination."""
        args = inject_branch_defaults(args)
        branches = args.get("branchCodeList", [1])
        open_statuses = [int(s) for s in (args.get("openStatusList") or get_purchase_order_open_statuses())]
        open_status_set = set(open_statuses)
        page_size = int(args.get("pageSize", 100))
        concurrency = int(args.get("concurrency", 10))
        top_n = int(args.get("topN", 20))
        max_pages = int(args.get("maxPages", 100))

        cache_key = {
            "fn": "open_purchase_orders",
            "branches": branches,
            "openStatusList": open_statuses,
            "pageSize": page_size,
            "concurrency": concurrency,
            "topN": top_n,
            "maxPages": max_pages,
        }
        cached = cache.get("open_purchase_orders", cache_key, cache.FINANCIAL)
        if cached is not None:
            return cached

        body = {"filter": {"branchCodeList": branches}}
        items, pages = await self._fetch_all_pages(
            f"{BASE_PO}/search",
            body,
            page_size=page_size,
            concurrency=concurrency,
            max_pages=max_pages,
        )

        open_items = [item for item in items if int(item.get("status") or 0) in open_status_set]
        open_total = sum(float(item.get("totalAmountOrder", 0) or 0) for item in open_items)

        by_status: dict[int, dict[str, Any]] = defaultdict(lambda: {"status": 0, "count": 0, "totalValue": 0.0})
        for item in open_items:
            status = int(item.get("status") or 0)
            value = float(item.get("totalAmountOrder", 0) or 0)
            group = by_status[status]
            group["status"] = status
            group["count"] += 1
            group["totalValue"] += value

        def _compact(item: dict[str, Any]) -> dict[str, Any]:
            return {
                "orderCode": item.get("orderCode"),
                "supplierCode": item.get("supplierCode"),
                "supplierName": item.get("supplierName"),
                "status": item.get("status"),
                "totalAmountOrder": float(item.get("totalAmountOrder", 0) or 0),
            }

        latest = sorted(open_items, key=lambda x: int(x.get("orderCode") or 0), reverse=True)[:top_n]
        largest = sorted(open_items, key=lambda x: float(x.get("totalAmountOrder", 0) or 0), reverse=True)[:top_n]

        result = {
            "branchCodeList": branches,
            "openRule": f"status in {open_statuses}",
            "openStatusList": open_statuses,
            "totalScanned": len(items),
            "openCount": len(open_items),
            "openTotalValue": open_total,
            "byStatus": sorted(by_status.values(), key=lambda x: x["status"]),
            "latestOpen": [_compact(item) for item in latest],
            "largestOpen": [_compact(item) for item in largest],
            "pageStats": {"pages": pages, "pageSize": page_size, "concurrency": concurrency},
        }
        cache.put("open_purchase_orders", cache_key, result)
        return result

    async def open_production_orders(self, args: dict[str, Any]) -> Any:
        """Fast summary of open production orders using parallel pagination."""
        args = inject_branch_defaults(args)
        branches = args.get("branchCodeList", [1])
        page_size = int(args.get("pageSize", 100))
        concurrency = int(args.get("concurrency", 10))
        top_n = int(args.get("topN", 20))
        max_pages = int(args.get("maxPages", 100))
        as_of_date = args.get("asOfDate") or date.today().isoformat()

        cache_key = {
            "fn": "open_production_orders",
            "branches": branches,
            "pageSize": page_size,
            "concurrency": concurrency,
            "topN": top_n,
            "maxPages": max_pages,
            "asOfDate": as_of_date,
        }
        cached = cache.get("open_production_orders", cache_key, cache.STOCK)
        if cached is not None:
            return cached

        body = {"filter": {"branchCodeList": branches}}
        items, pages = await self._fetch_all_pages(
            f"{BASE_PROD_ORDER}/orders/search",
            body,
            page_size=page_size,
            concurrency=concurrency,
            max_pages=max_pages,
        )

        open_items = [
            item for item in items
            if float(item.get("pendingQuantity", 0) or 0) > 0 and not item.get("endDate")
        ]

        by_status: dict[int, dict[str, Any]] = defaultdict(
            lambda: {"status": 0, "count": 0, "pendingQuantity": 0.0}
        )
        overdue_count = 0
        for item in open_items:
            status = int(item.get("status") or 0)
            pending = float(item.get("pendingQuantity", 0) or 0)
            group = by_status[status]
            group["status"] = status
            group["count"] += 1
            group["pendingQuantity"] += pending

            estimate = (item.get("estimatedEndDate") or item.get("endForecastDate") or item.get("deliveryDate") or "")[:10]
            if estimate and estimate < as_of_date:
                overdue_count += 1

        def _compact(item: dict[str, Any]) -> dict[str, Any]:
            return {
                "orderCode": item.get("orderCode"),
                "productionOrderCode": item.get("productionOrderCode"),
                "productCode": item.get("productCode"),
                "productName": item.get("productName"),
                "status": item.get("status"),
                "quantity": float(item.get("quantity", 0) or 0),
                "finishedQuantity": float(item.get("finishedQuantity", 0) or 0),
                "pendingQuantity": float(item.get("pendingQuantity", 0) or 0),
                "estimatedEndDate": item.get("estimatedEndDate") or item.get("endForecastDate"),
            }

        latest = sorted(
            open_items,
            key=lambda x: int(x.get("orderCode") or x.get("productionOrderCode") or 0),
            reverse=True,
        )[:top_n]
        largest = sorted(open_items, key=lambda x: float(x.get("pendingQuantity", 0) or 0), reverse=True)[:top_n]

        result = {
            "branchCodeList": branches,
            "openRule": "pendingQuantity > 0 and endDate is null",
            "asOfDate": as_of_date,
            "totalScanned": len(items),
            "openCount": len(open_items),
            "totalQuantity": sum(float(item.get("quantity", 0) or 0) for item in open_items),
            "finishedQuantity": sum(float(item.get("finishedQuantity", 0) or 0) for item in open_items),
            "pendingQuantity": sum(float(item.get("pendingQuantity", 0) or 0) for item in open_items),
            "byStatus": sorted(by_status.values(), key=lambda x: x["status"]),
            "overdueCount": overdue_count,
            "latestOpen": [_compact(item) for item in latest],
            "largestPending": [_compact(item) for item in largest],
            "pageStats": {"pages": pages, "pageSize": page_size, "concurrency": concurrency},
        }
        cache.put("open_production_orders", cache_key, result)
        return result
