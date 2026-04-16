"""Purchase Order Tools — /api/totvsmoda/purchase-order/v2/"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.purchase-order")
BASE = "/api/totvsmoda/purchase-order/v2"


class PurchaseOrderTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_purchase_orders(self, args: dict[str, Any]) -> Any:
        """POST /search — Consulta pedidos de compra."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/search", body)

    async def create_purchase_order(self, args: dict[str, Any]) -> Any:
        """POST /orders — ⚠️ Inclui pedido de compra."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/orders", body)

    async def cancel_purchase_order(self, args: dict[str, Any]) -> Any:
        """POST /orders/cancel — ⚠️ Cancela pedido de compra."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/orders/cancel", body)

    async def change_purchase_order_status(self, args: dict[str, Any]) -> Any:
        """POST /orders/change-status — ⚠️ Altera situação do pedido de compra."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/orders/change-status", body)
