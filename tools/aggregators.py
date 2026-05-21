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
from collections import defaultdict
from datetime import datetime, date
from typing import Any

from totvs_client import TotvsClient
from tools._defaults import inject_branch_defaults

logger = logging.getLogger("totvs-moda-mcp.aggregators")

BASE_SALES = "/api/totvsmoda/sales-order/v2"
BASE_PRODUCT = "/api/totvsmoda/product/v2"
BASE_AR = "/api/totvsmoda/accounts-receivable/v2"
BASE_AP = "/api/totvsmoda/accounts-payable/v2"


def _parse_iso_date(s: str) -> datetime:
    """Parse ISO date string tolerant to both 'YYYY-MM-DD' and 'YYYY-MM-DDTHH:MM:SS'."""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return datetime.strptime(s[:10], "%Y-%m-%d")


class AggregatorTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

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
            "option": {"balances": [{"branchCode": branch, "stockCodeList": [1]}]},
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
            resp = await self.client.post(f"{BASE_AR}/receivable-installments/search", body)
            items = resp.get("items", []) if isinstance(resp, dict) else []
            total = sum(float(i.get("installmentValue", 0) or 0) for i in items)
            return {
                "count": len(items),
                "totalValue": total,
                "items": [
                    {
                        "customerCpfCnpj": i.get("customerCpfCnpj"),
                        "installmentValue": float(i.get("installmentValue", 0) or 0),
                        "paidValue": float(i.get("paidValue", 0) or 0),
                        "bearerName": i.get("bearerName"),
                    }
                    for i in items
                ],
            }

        async def _payable():
            body = {
                "filter": {
                    "branchCodeList": branches,
                    "startExpiredDate": target,
                    "endExpiredDate": target,
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

        sales, receivable, payable = await asyncio.gather(_sales(), _receivable(), _payable())
        return {"date": target, "sales": sales, "receivable": receivable, "payable": payable}

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

        return {
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
            minStock (optional, default 1): saldo mínimo para incluir

        Returns:
            {branchCode, totalSkus, totalUnits, products: [{productCode,
             productName, colorName, sizeName, stock, salesOrder}]}
        """
        args = inject_branch_defaults(args)
        branch = args.get("branchCode", 1)
        min_stock = args.get("minStock", 1)

        flt: dict[str, Any] = {}
        if args.get("productCodeList"):
            flt["productCodeList"] = args["productCodeList"]
        if args.get("referenceCodeList"):
            flt["referenceCodeList"] = args["referenceCodeList"]

        all_products = []
        page = 1
        while True:
            body = {
                "filter": flt,
                "option": {"balances": [{"branchCode": branch, "stockCodeList": [1]}]},
                "page": page,
                "pageSize": 1000,
            }
            resp = await self.client.post(f"{BASE_PRODUCT}/balances/search", body)
            items = resp.get("items", []) if isinstance(resp, dict) else []

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

            has_next = resp.get("hasNext", False) if isinstance(resp, dict) else False
            if not has_next:
                break
            page += 1
            if page > 50:  # safety limit
                break

        all_products.sort(key=lambda x: x["productName"])
        total_units = sum(p["stock"] for p in all_products)

        return {
            "branchCode": branch,
            "totalSkus": len(all_products),
            "totalUnits": total_units,
            "products": all_products,
        }
