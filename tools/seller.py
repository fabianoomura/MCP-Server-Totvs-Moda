"""Seller Tools — /api/totvsmoda/seller/v2/"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults

logger = logging.getLogger("totvs-moda-mcp.seller")
BASE = "/api/totvsmoda/seller/v2"


def _pascal_params(args: dict[str, Any]) -> dict[str, Any]:
    return {k[:1].upper() + k[1:]: v for k, v in args.items() if v is not None and k != "fields"}


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

    async def get_operational_area_state(self, args: dict[str, Any]) -> Any:
        """GET /operational-area-state - regioes de atuacao de vendedores por estado."""
        result = await self.client.get(f"{BASE}/operational-area-state", params=_pascal_params(args) or None)
        return apply_fields(result, args)


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_sellers",
        description="Lista vendedores e empresas vinculadas. Use fields para reduzir tokens.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "sellerCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100
                },
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_seller_operational_area",
        description="Regiões de atuação de vendedores.",
        inputSchema={
            "type": "object",
            "properties": {
                "sellerCode": {
                    "type": "integer"
                },
                "branchCode": {
                    "type": "integer"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_seller_operational_area_state",
        description="Regiões de atuação de vendedores por estado.",
        inputSchema={
            "type": "object",
            "properties": {
                "startChangeDate": {
                    "type": "string"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "operationalAreaCode": {
                    "type": "integer"
                },
                "order": {
                    "type": "string",
                    "description": "operationalAreaCode,maxChangeFilterDate"
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 1000
                },
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_seller_area_by_cep",
        description="Vendedor responsável por um CEP.",
        inputSchema={
            "type": "object",
            "properties": {
                "cep": {
                    "type": "string",
                    "description": "CEP (somente dígitos)"
                },
                "branchCode": {
                    "type": "integer"
                }
            },
            "required": [
                "cep"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_seller_area_by_city",
        description="Vendedor responsável por uma cidade.",
        inputSchema={
            "type": "object",
            "properties": {
                "cityCode": {
                    "type": "integer"
                },
                "branchCode": {
                    "type": "integer"
                }
            },
            "required": [
                "cityCode"
            ]
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_sellers": "search_sellers",
    "totvs_get_seller_operational_area": "get_operational_area",
    "totvs_get_seller_operational_area_state": "get_operational_area_state",
    "totvs_get_seller_area_by_cep": "get_operational_area_by_cep",
    "totvs_get_seller_area_by_city": "get_operational_area_by_city",
}