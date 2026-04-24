"""Seller Tools — /api/totvsmoda/seller/v2/"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults

logger = logging.getLogger("totvs-moda-mcp.seller")
BASE = "/api/totvsmoda/seller/v2"


class SellerTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_sellers(self, args: dict[str, Any]) -> Any:
        """POST /search — Lista vendedores, empresas e clientes."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE}/search", body)
        return apply_fields(result, args)

    async def get_operational_area(self, args: dict[str, Any]) -> Any:
        """GET /operational-area — Regiões de atuação de vendedores."""
        args = inject_branch_defaults(args)
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/operational-area", params=params or None)

    async def get_operational_area_by_cep(self, args: dict[str, Any]) -> Any:
        """GET /operational-area-cep — Regiões de atuação por CEP."""
        args = inject_branch_defaults(args)
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/operational-area-cep", params=params or None)

    async def get_operational_area_by_city(self, args: dict[str, Any]) -> Any:
        """GET /operational-area-city — Regiões de atuação por cidade."""
        args = inject_branch_defaults(args)
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/operational-area-city", params=params or None)
