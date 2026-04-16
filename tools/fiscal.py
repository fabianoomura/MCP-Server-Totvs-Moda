"""
Fiscal Tools
============
API Fiscal v2 — /api/totvsmoda/fiscal/v2/
Notas fiscais, XML NF-e, DANFE, certificado digital, centro de custo.
"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.fiscal")
BASE = "/api/totvsmoda/fiscal/v2"


class FiscalTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices/search — Lista NF-e por filtro geral."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices/search", body)

    async def get_xml_content(self, args: dict[str, Any]) -> Any:
        """GET /xml-contents/{accessKey} — XML da NF-e pela chave de acesso."""
        access_key = args["accessKey"]
        return await self.client.get(f"{BASE}/xml-contents/{access_key}")

    async def get_invoice_item_detail(self, args: dict[str, Any]) -> Any:
        """GET /invoices/item-detail-search — Detalhe de itens da NF-e."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/invoices/item-detail-search", params=params or None)

    async def get_danfe(self, args: dict[str, Any]) -> Any:
        """POST /danfe-search — Base64 do DANFE via XML."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/danfe-search", body)

    async def search_invoice_products(self, args: dict[str, Any]) -> Any:
        """POST /invoice-products/search — Produtos de NF-e por filtro geral."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoice-products/search", body)

    async def get_digital_certificates(self, args: dict[str, Any]) -> Any:
        """GET /digital-certificates — Dados de certificados digitais."""
        return await self.client.get(f"{BASE}/digital-certificates")

    async def get_cost_center(self, args: dict[str, Any]) -> Any:
        """GET /cost-center — Centros de custo."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/cost-center", params=params or None)

    async def get_pending_conditional_products(self, args: dict[str, Any]) -> Any:
        """GET /invoices/pending-conditional-products — Saldo de produto em condicional."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/invoices/pending-conditional-products", params=params or None)

    async def get_disabled_invoices(self, args: dict[str, Any]) -> Any:
        """GET /invoices/disable — NF-e inutilizadas."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/invoices/disable", params=params or None)

    async def print_transaction(self, args: dict[str, Any]) -> Any:
        """POST /transaction/print — Base64 da impressão da transação em PDF."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/transaction/print", body)

    async def create_manifestation(self, args: dict[str, Any]) -> Any:
        """POST /invoices/manifestations — ⚠️ Manifestação do destinatário NF-e."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices/manifestations", body)
