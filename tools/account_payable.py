"""
Account Payable Tools
=====================
API Accounts Payable v2 — /api/totvsmoda/accounts-payable/v2/
"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.account-payable")
BASE = "/api/totvsmoda/accounts-payable/v2"


class AccountPayableTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_duplicates(self, args: dict[str, Any]) -> Any:
        """POST /duplicates/search — Consulta de duplicatas."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/duplicates/search", body)

    async def search_commissions_paid(self, args: dict[str, Any]) -> Any:
        """POST /comissions-paid/search — Fechamento de comissão."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/comissions-paid/search", body)

    async def create_duplicate(self, args: dict[str, Any]) -> Any:
        """POST /duplicates — ⚠️ Inclusão de duplicata."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/duplicates", body)
