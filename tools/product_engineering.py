"""
Product Engineering Tools
=========================
API Product Engineering v2 — /api/totvsmoda/product-engineering/v2/
Fichas de consumo (matéria-prima + serviços).
"""
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields

BASE = "/api/totvsmoda/product-engineering/v2"


class ProductEngineeringTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_consumption_sheet(self, args: dict[str, Any]) -> Any:
        """POST /consumption-sheet/search — Ficha de consumo (matéria-prima + serviços)."""
        excluded = ("page", "pageSize", "fields")
        flt = {k: v for k, v in args.items() if k not in excluded and v is not None}

        body: dict[str, Any] = {
            **flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 1000),
        }

        result = await self.client.post(f"{BASE}/consumption-sheet/search", body)
        return apply_fields(result, args)
