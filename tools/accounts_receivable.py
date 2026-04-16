"""
Accounts Receivable Tools
=========================
API Accounts Receivable v2 — /api/totvsmoda/accounts-receivable/v2/
Contas a receber, boletos, PIX, limite de cliente, cheque presente.
"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.accounts-receivable")
BASE = "/api/totvsmoda/accounts-receivable/v2"


class AccountsReceivableTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_customer_financial_balance(self, args: dict[str, Any]) -> Any:
        """POST /customer-financial-balance/search — Limite financeiro do cliente."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/customer-financial-balance/search", body)

    async def search_documents(self, args: dict[str, Any]) -> Any:
        """POST /documents/search — Documentos de contas a receber."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/documents/search", body)

    async def search_printed_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-print/search — Boletos já impressos."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices-print/search", body)

    async def get_gift_check_balances(self, args: dict[str, Any]) -> Any:
        """GET /gift-check-balances — Saldo de cheque presente."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/gift-check-balances", params=params or None)

    async def get_bank_slip(self, args: dict[str, Any]) -> Any:
        """POST /bank-slip — Retorna base64 do boleto bancário."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/bank-slip", body)

    async def get_payment_link(self, args: dict[str, Any]) -> Any:
        """POST /payment-link — Retorna link de pagamento PIX da fatura."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/payment-link", body)

    # ── WRITE ──────────────────────────────────────────────────────────────

    async def settle_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-settle/create — ⚠️ Liquidar faturas."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices-settle/create", body)

    async def create_invoice(self, args: dict[str, Any]) -> Any:
        """POST /invoices — ⚠️ Incluir fatura em aberto."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices", body)

    async def renegotiate_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-renegotiate — ⚠️ Renegociar faturas."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices-renegotiate", body)

    async def pay_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-payment — ⚠️ Baixa de faturas."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices-payment", body)

    async def create_gift_check(self, args: dict[str, Any]) -> Any:
        """POST /gift-checks — ⚠️ Incluir cheque presente."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/gift-checks", body)
