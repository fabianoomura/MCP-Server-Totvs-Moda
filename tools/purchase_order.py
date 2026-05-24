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
        # API espera branchCodeList (array)
        if args.get("branchCodeList"):
            flt["branchCodeList"] = args["branchCodeList"]
        elif args.get("branchCode"):
            flt["branchCodeList"] = [args["branchCode"]]

        filter_fields = (
            "change",
            "orderCodeList",
            "supplierOrderCodeList",
            "supplierCodeList",
            "supplierCpfCnpjList",
            "orderStatusList",
            "operationCodeList",
            "startBasePaymentDate",
            "endBasePaymentDate",
            "startDeliveryForecastDate",
            "endDeliveryForecastDate",
            "startDeliveryDeadlineDate",
            "endDeliveryDeadlineDate",
            "productCodeList",
        )
        for field in filter_fields:
            if args.get(field) is not None:
                flt[field] = args[field]

        # Backward-compatible aliases used by earlier MCP versions.
        if args.get("statusList") is not None and "orderStatusList" not in flt:
            flt["orderStatusList"] = args["statusList"]
        if args.get("startDate") is not None or args.get("endDate") is not None:
            flt.setdefault("change", {})
            if args.get("startDate") is not None:
                flt["change"]["startDate"] = args["startDate"]
            if args.get("endDate") is not None:
                flt["change"]["endDate"] = args["endDate"]

        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        if args.get("expand"):
            body["expand"] = args["expand"]
        if args.get("order"):
            body["order"] = args["order"]
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
