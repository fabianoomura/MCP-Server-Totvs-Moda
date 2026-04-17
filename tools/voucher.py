"""
Voucher Tools
=============
API Voucher v2 — /api/totvsmoda/voucher/v2/
"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.voucher")
BASE = "/api/totvsmoda/voucher/v2"


class VoucherTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_voucher(self, args: dict[str, Any]) -> Any:
        """POST /search — Lista vouchers por filtro."""
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        return await self.client.post(f"{BASE}/search", body)

    async def get_voucher(self, args: dict[str, Any]) -> Any:
        """GET /{id} — Retorna voucher por ID."""
        return await self.client.get(f"{BASE}/{args['id']}")

    async def create_voucher(self, args: dict[str, Any]) -> Any:
        """POST /create — ⚠️ Inclui voucher."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/create", body)

    async def update_voucher(self, args: dict[str, Any]) -> Any:
        """POST /update — ⚠️ Altera voucher."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/update", body)

    async def create_customer_vouchers(self, args: dict[str, Any]) -> Any:
        """POST /customer/create — ⚠️ Cria vouchers para lista de clientes."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/customer/create", body)
