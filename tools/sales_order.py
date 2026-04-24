"""
Sales Order Tools
=================
Implements all MCP tools for the TOTVS Moda Sales Order API V2.
Endpoint base: /api/totvsmoda/sales-order/v2/
"""

import logging
from typing import Any

from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults

logger = logging.getLogger("totvs-moda-mcp.sales-order")

BASE = "/api/totvsmoda/sales-order/v2"


class SalesOrderTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    # ------------------------------------------------------------------ #
    # READ operations                                                      #
    # ------------------------------------------------------------------ #

    async def search_orders(self, args: dict[str, Any]) -> Any:
        """
        POST /orders/search
        Busca pedidos de venda com filtros flexíveis.
        """
        args = inject_branch_defaults(args)
        # Build filter object from flat args
        filter_fields = [
            "startOrderDate",
            "endOrderDate",
            "branchCodeList",
            "orderCodeList",
            "orderIdList",
            "customerOrderCodeList",
            "integrationCodeList",
            "customerCodeList",
            "customerCpfCnpjList",
            "representativeCodeList",
            "representativeCpfCnpjList",
            "orderStatusList",
            "operationCodeList",
            "startBillingForecastDate",
            "endBillingForecastDate",
            "hasShippingCompany",
            "hasPdvTransaction",
            "hasFinancialProcessed",
        ]

        order_filter = {}
        for field in filter_fields:
            if field in args and args[field] is not None:
                order_filter[field] = args[field]

        body: dict[str, Any] = {}

        if order_filter:
            body["filter"] = order_filter

        if "expand" in args:
            body["expand"] = args["expand"]

        if "order" in args:
            body["order"] = args["order"]

        body["page"] = args.get("page", 1)
        body["pageSize"] = args.get("pageSize", 100)

        result = await self.client.post(f"{BASE}/orders/search", body)
        return apply_fields(result, args)

    async def get_order_invoices(self, args: dict[str, Any]) -> Any:
        """
        GET /invoices?branchCode=X&orderCode=Y
        Retorna notas fiscais vinculadas ao pedido.
        """
        args = inject_branch_defaults(args)
        params = {
            "branchCode": args["branchCode"],
            "orderCode": args["orderCode"],
        }
        return await self.client.get(f"{BASE}/invoices", params=params)

    async def get_pending_items(self, args: dict[str, Any]) -> Any:
        """
        GET /pending-items?branchCode=X&orderCode=Y
        Retorna itens pendentes (não faturados) do pedido.
        """
        args = inject_branch_defaults(args)
        params = {
            "branchCode": args["branchCode"],
            "orderCode": args["orderCode"],
        }
        return await self.client.get(f"{BASE}/pending-items", params=params)

    async def get_discount_types(self, args: dict[str, Any]) -> Any:
        """
        GET /discount-type?branchCode=X
        Consulta tipos de desconto disponíveis.
        """
        args = inject_branch_defaults(args)
        params = {"branchCode": args["branchCode"]}
        return await self.client.get(f"{BASE}/discount-type", params=params)

    async def get_billing_suggestions(self, args: dict[str, Any]) -> Any:
        """
        GET /billing-suggestions?branchCode=X&orderCode=Y
        Consulta sugestões de faturamento.
        """
        args = inject_branch_defaults(args)
        params: dict[str, Any] = {"branchCode": args["branchCode"]}
        if "orderCode" in args:
            params["orderCode"] = args["orderCode"]
        return await self.client.get(f"{BASE}/billing-suggestions", params=params)

    async def get_classifications(self, args: dict[str, Any]) -> Any:
        """
        GET /classifications?branchCode=X
        Consulta classificações disponíveis.
        """
        args = inject_branch_defaults(args)
        params = {"branchCode": args["branchCode"]}
        return await self.client.get(f"{BASE}/classifications", params=params)

    # ------------------------------------------------------------------ #
    # WRITE operations                                                     #
    # ------------------------------------------------------------------ #

    async def create_order(self, args: dict[str, Any]) -> Any:
        """
        POST /b2c-orders
        Cria um novo pedido de venda B2C.
        """
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/b2c-orders", body)

    async def cancel_order(self, args: dict[str, Any]) -> Any:
        """
        POST /orders/cancel
        Cancela um pedido de venda. reasonCancellationCode é obrigatório (integer).
        """
        args = inject_branch_defaults(args)
        body: dict[str, Any] = {
            "branchCode": args["branchCode"],
            "orderCode": args["orderCode"],
            "reasonCancellationCode": args["reasonCancellationCode"],
        }
        return await self.client.post(f"{BASE}/orders/cancel", body)

    async def change_order_status(self, args: dict[str, Any]) -> Any:
        """POST /orders/change-status — Altera a situação do pedido."""
        args = inject_branch_defaults(args)
        # Accept both swagger field (statusOrder) and legacy alias (newStatus)
        status = args.get("statusOrder") or args.get("newStatus")
        if not status:
            raise ValueError("statusOrder é obrigatório (ou newStatus como alias legado)")
        body = {k: v for k, v in args.items() if v is not None and k != "newStatus"}
        body["statusOrder"] = status
        body.pop("newStatus", None)
        return await self.client.post(f"{BASE}/orders/change-status", body)

    async def add_order_items(self, args: dict[str, Any]) -> Any:
        """POST /items — ⚠️ Adiciona itens a pedido existente."""
        if not args.get("items"):
            raise ValueError("'items' é obrigatório")
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/items", body)

    async def remove_order_item(self, args: dict[str, Any]) -> Any:
        """DELETE /items — ⚠️ Remove item de pedido (query params PascalCase)."""
        params: dict[str, Any] = {}
        for field, param in (
            ("branchCode", "BranchCode"), ("orderCode", "OrderCode"),
            ("productCode", "ProductCode"), ("productSku", "ProductSku"),
        ):
            if args.get(field) is not None:
                params[param] = args[field]
        return await self.client.delete(f"{BASE}/items", params=params)

    async def cancel_order_items(self, args: dict[str, Any]) -> Any:
        """POST /cancel-items — ⚠️ Cancela quantidades de itens."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/cancel-items", body)

    async def change_order_item_quantity(self, args: dict[str, Any]) -> Any:
        """POST /quantity-items — ⚠️ Altera quantidade de itens."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/quantity-items", body)

    async def update_order_items_additional(self, args: dict[str, Any]) -> Any:
        """POST /additional-items — ⚠️ Altera dados adicionais de itens."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/additional-items", body)

    async def add_order_observation(self, args: dict[str, Any]) -> Any:
        """POST /observations-order — ⚠️ Adiciona observação ao pedido."""
        if not args.get("observation"):
            raise ValueError("'observation' é obrigatório")
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/observations-order", body)

    async def update_order_shipping(self, args: dict[str, Any]) -> Any:
        """POST /shipping-order — ⚠️ Altera dados de transporte do pedido."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/shipping-order", body)

    async def update_order_additional(self, args: dict[str, Any]) -> Any:
        """POST /additional-order — ⚠️ Altera dados adicionais do pedido."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/additional-order", body)

    async def search_batch_items(self, args: dict[str, Any]) -> Any:
        """GET /batch-items — Lista lotes de itens (query params PascalCase)."""
        params: dict[str, Any] = {}
        for field, param in (
            ("status", "Status"), ("startChangeDate", "StartChangeDate"),
            ("endChangeDate", "EndChangeDate"), ("branchCode", "BranchCode"),
        ):
            if args.get(field) is not None:
                params[param] = args[field]
        return await self.client.get(f"{BASE}/batch-items", params=params or None)

    async def create_order_relationship_counts(self, args: dict[str, Any]) -> Any:
        """POST /relationship-counts — ⚠️ Cria contagens de relacionamento de pedido."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/relationship-counts", body)

    async def update_order_header(self, args: dict[str, Any]) -> Any:
        """
        POST /header
        Altera dados de capa do pedido.
        """
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/header", body)

    async def update_order_items_price(self, args: dict[str, Any]) -> Any:
        """
        POST /price-items
        Altera preço de itens do pedido.
        """
        args = inject_branch_defaults(args)
        body = {
            "branchCode": args["branchCode"],
            "orderCode": args["orderCode"],
            "items": args["items"],
        }
        return await self.client.post(f"{BASE}/price-items", body)
