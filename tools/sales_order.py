"""
Sales Order Tools
=================
Implements all MCP tools for the TOTVS Moda Sales Order API V2.
Endpoint base: /api/totvsmoda/sales-order/v2/
"""

import logging
from typing import Any

from totvs_client import TotvsClient

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

        return await self.client.post(f"{BASE}/orders/search", body)

    async def get_order_invoices(self, args: dict[str, Any]) -> Any:
        """
        GET /invoices?branchCode=X&orderCode=Y
        Retorna notas fiscais vinculadas ao pedido.
        """
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
        params = {"branchCode": args["branchCode"]}
        return await self.client.get(f"{BASE}/discount-type", params=params)

    async def get_billing_suggestions(self, args: dict[str, Any]) -> Any:
        """
        GET /billing-suggestions?branchCode=X&orderCode=Y
        Consulta sugestões de faturamento.
        """
        params: dict[str, Any] = {"branchCode": args["branchCode"]}
        if "orderCode" in args:
            params["orderCode"] = args["orderCode"]
        return await self.client.get(f"{BASE}/billing-suggestions", params=params)

    async def get_classifications(self, args: dict[str, Any]) -> Any:
        """
        GET /classifications?branchCode=X
        Consulta classificações disponíveis.
        """
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
        body: dict[str, Any] = {
            "branchCode": args["branchCode"],
            "orderCode": args["orderCode"],
            "reasonCancellationCode": args["reasonCancellationCode"],
        }
        return await self.client.post(f"{BASE}/orders/cancel", body)

    async def change_order_status(self, args: dict[str, Any]) -> Any:
        """
        POST /orders/change-status
        Altera a situação de um pedido de venda. newStatus é obrigatório.
        """
        body = {
            "branchCode": args["branchCode"],
            "orderCode": args["orderCode"],
            "newStatus": args["newStatus"],
        }
        return await self.client.post(f"{BASE}/orders/change-status", body)

    async def update_order_header(self, args: dict[str, Any]) -> Any:
        """
        POST /header
        Altera dados de capa do pedido.
        """
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/header", body)

    async def update_order_items_price(self, args: dict[str, Any]) -> Any:
        """
        POST /price-items
        Altera preço de itens do pedido.
        """
        body = {
            "branchCode": args["branchCode"],
            "orderCode": args["orderCode"],
            "items": args["items"],
        }
        return await self.client.post(f"{BASE}/price-items", body)
