"""Purchase Order Tools — /api/totvsmoda/purchase-order/v2/"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults

logger = logging.getLogger("totvs-moda-mcp.purchase-order")
BASE = "/api/totvsmoda/purchase-order/v2"


class PurchaseOrderTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_purchase_orders(self, args: dict[str, Any]) -> Any:
        """POST /search — Consulta pedidos de compra."""
        args = inject_branch_defaults(args)
        flt: dict[str, Any] = {}
        for field in ("branchCode", "orderCodeList", "startDate", "endDate", "statusList",
                      "supplierCodeList", "operationCodeList"):
            if args.get(field) is not None:
                flt[field] = args[field]
        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        result = await self.client.post(f"{BASE}/search", body)
        return apply_fields(result, args)

    async def create_purchase_order(self, args: dict[str, Any]) -> Any:
        """POST /orders — ⚠️ Inclui pedido de compra."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/orders", body)

    async def cancel_purchase_order(self, args: dict[str, Any]) -> Any:
        """POST /orders/cancel — ⚠️ Cancela pedido de compra."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/orders/cancel", body)

    async def change_purchase_order_status(self, args: dict[str, Any]) -> Any:
        """POST /orders/change-status — ⚠️ Altera situação do pedido de compra."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/orders/change-status", body)
