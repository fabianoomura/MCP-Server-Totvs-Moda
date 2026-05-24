"""
Product Prototype Tools
=======================
API Product Prototype v2 - /api/totvsmoda/product-prototype/v2/
"""
from typing import Any

from totvs_client import TotvsClient
from tools._fields import apply_fields


BASE = "/api/totvsmoda/product-prototype/v2"


class ProductPrototypeTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_prototypes(self, args: dict[str, Any]) -> Any:
        """POST /prototypes/search - consulta prototipos."""
        if not args.get("prototypeCodeList"):
            raise ValueError("prototypeCodeList e obrigatorio para buscar prototipos na API TOTVS.")
        body: dict[str, Any] = {
            k: v for k, v in args.items()
            if k not in ("fields",) and v is not None
        }
        body.setdefault("page", 1)
        body.setdefault("pageSize", 100)
        result = await self.client.post(f"{BASE}/prototypes/search", body)
        return apply_fields(result, args)

    async def create_prototype(self, args: dict[str, Any]) -> Any:
        """POST /prototypes - cria prototipo."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/prototypes", body)

    async def update_prototype(self, args: dict[str, Any]) -> Any:
        """POST /prototypes/update - altera prototipo."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/prototypes/update", body)
