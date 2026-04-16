"""
Product Tools
=============
API Product v2 — /api/totvsmoda/product/v2/
Catálogo, preços, saldos, grades, cores, referências, lotes.
"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.product")
BASE = "/api/totvsmoda/product/v2"


class ProductTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_products(self, args: dict[str, Any]) -> Any:
        """POST /products/search — Busca produtos por filtro geral."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/products/search", body)

    async def get_product(self, args: dict[str, Any]) -> Any:
        """GET /products/{code}/{branchCode} — Dados de produto/pack por código."""
        code = args["code"]
        branch = args.get("branchCode", 1)
        return await self.client.get(f"{BASE}/products/{code}/{branch}")

    async def search_product_codes(self, args: dict[str, Any]) -> Any:
        """POST /product-codes/search — Lista de produtos por filtro geral."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product-codes/search", body)

    async def search_balances(self, args: dict[str, Any]) -> Any:
        """POST /balances/search — Saldos de estoque por filtro geral."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/balances/search", body)

    async def search_prices(self, args: dict[str, Any]) -> Any:
        """POST /prices/search — Preços de produtos por filtro geral."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/prices/search", body)

    async def search_price_tables(self, args: dict[str, Any]) -> Any:
        """POST /price-tables/search — Preços baseados em tabela de preço."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/price-tables/search", body)

    async def get_price_tables_headers(self, args: dict[str, Any]) -> Any:
        """GET /price-tables-headers — Dados de tabelas de preço."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/price-tables-headers", params=params or None)

    async def search_costs(self, args: dict[str, Any]) -> Any:
        """POST /costs/search — Custos de produtos."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/costs/search", body)

    async def search_references(self, args: dict[str, Any]) -> Any:
        """POST /references/search — Dados de referências de produtos."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/references/search", body)

    async def get_grid(self, args: dict[str, Any]) -> Any:
        """GET /grid — Dados de grade (tamanhos)."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/grid", params=params or None)

    async def get_category(self, args: dict[str, Any]) -> Any:
        """GET /category — Dados de categorias de produto."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/category", params=params or None)

    async def search_colors(self, args: dict[str, Any]) -> Any:
        """POST /colors/search — Dados de cores."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/colors/search", body)

    async def get_classifications(self, args: dict[str, Any]) -> Any:
        """GET /classifications — Classificações de produto."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/classifications", params=params or None)

    async def search_batch(self, args: dict[str, Any]) -> Any:
        """POST /batch/search — Dados de lote de produto."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/batch/search", body)

    async def get_measurement_units(self, args: dict[str, Any]) -> Any:
        """GET /measurement-unit — Unidades de medida."""
        return await self.client.get(f"{BASE}/measurement-unit")

    async def get_kardex_movement(self, args: dict[str, Any]) -> Any:
        """GET /kardex-movement — Movimentação kardex de produto."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/kardex-movement", params=params or None)

    async def search_compositions(self, args: dict[str, Any]) -> Any:
        """POST /compositions — Composições de produto."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/compositions", body)

    async def search_omni_changed_balances(self, args: dict[str, Any]) -> Any:
        """POST /omni-changed-balances — Saldos alterados (omni-channel)."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/omni-changed-balances", body)

    # ── WRITE ──────────────────────────────────────────────────────────────

    async def update_product_price(self, args: dict[str, Any]) -> Any:
        """POST /values/update — ⚠️ Altera preço ou custo de produto."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/values/update", body)

    async def update_promotion_price(self, args: dict[str, Any]) -> Any:
        """POST /promotion-values/update — ⚠️ Altera preço de promoção."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/promotion-values/update", body)

    async def update_product_data(self, args: dict[str, Any]) -> Any:
        """PUT /data — ⚠️ Altera dados gerais de produto."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/data", body)

    async def create_barcode(self, args: dict[str, Any]) -> Any:
        """POST /barcodes — ⚠️ Inclui código de barras para produto."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/barcodes", body)

    async def create_batch(self, args: dict[str, Any]) -> Any:
        """POST /batch/create — ⚠️ Inclui lote e item de lote de produto."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/batch/create", body)
