"""
Logistics Tools
===============
API Logistics v2 — /api/totvsmoda/logistics/v2/
Armazenagem física de produtos e movimentação de embalagens.

Validated in production (MOOUI scripts):
- product-storages/search: consulta em qual local físico o produto está
- product-packagings/add-quantity: adiciona produto a uma embalagem
- product-packagings/subtract-quantity: remove produto de uma embalagem
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._defaults import inject_branch_defaults

logger = logging.getLogger("totvs-moda-mcp.logistics")
BASE = "/api/totvsmoda/logistics/v2"


class LogisticsTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_product_storage(self, args: dict[str, Any]) -> Any:
        """POST /product-storages/search — Consulta armazenagem (local físico) de produtos.

        Retorna em quais locais/depósitos cada produto está armazenado.
        """
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order") and v is not None}
        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        if args.get("order"):
            body["order"] = args["order"]
        return await self.client.post(f"{BASE}/product-storages/search", body)

    async def add_product_packaging(self, args: dict[str, Any]) -> Any:
        """POST /product-packagings/add-quantity — ⚠️ Adiciona quantidade de produto em embalagem."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product-packagings/add-quantity", body)

    async def subtract_product_packaging(self, args: dict[str, Any]) -> Any:
        """POST /product-packagings/subtract-quantity — ⚠️ Remove quantidade de produto de embalagem."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product-packagings/subtract-quantity", body)
