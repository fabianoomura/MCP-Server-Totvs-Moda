"""Voucher Tools — /api/totvsmoda/voucher/v2/"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.voucher")
BASE = "/api/totvsmoda/voucher/v2"


class VoucherTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_vouchers(self, args: dict[str, Any]) -> Any:
        """POST /search — Lista vouchers."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/search", body)

    async def get_voucher(self, args: dict[str, Any]) -> Any:
        """GET /{id} — Retorna voucher por ID."""
        voucher_id = args.get("id")
        return await self.client.get(f"{BASE}/{voucher_id}")
