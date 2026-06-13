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
from tools._fields import apply_fields

logger = logging.getLogger("totvs-moda-mcp.logistics")
BASE = "/api/totvsmoda/logistics/v2"


def _with_branch_code(args: dict[str, Any]) -> dict[str, Any]:
    out = inject_branch_defaults(args)
    out.pop("branchCodeList", None)
    return out


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
        result = await self.client.post(f"{BASE}/product-storages/search", body)
        return apply_fields(result, args)

    async def upsert_product_packaging(self, args: dict[str, Any]) -> Any:
        """POST /product-packagings - manutencao de produto em embalagem."""
        args = _with_branch_code(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product-packagings", body)

    async def add_product_packaging(self, args: dict[str, Any]) -> Any:
        """POST /product-packagings/add-quantity — ⚠️ Adiciona quantidade de produto em embalagem."""
        args = _with_branch_code(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product-packagings/add-quantity", body)

    async def subtract_product_packaging(self, args: dict[str, Any]) -> Any:
        """POST /product-packagings/subtract-quantity — ⚠️ Remove quantidade de produto de embalagem."""
        args = _with_branch_code(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product-packagings/subtract-quantity", body)


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_product_storage",
        description="Consulta armazenagem fisica/localizacao logistica de produtos.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Filial unica; alternativa a branchCodeList"
                },
                "branchCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "productCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "referenceCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "barCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "addressCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "order": {
                    "type": "string"
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100
                }
            }
        },
    ),
    types.Tool(
        name="totvs_upsert_product_packaging",
        description="⚠️ ESCRITA — Manutencao de produto em embalagem logistica.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "packagingNumber": {
                    "type": "integer"
                },
                "productCode": {
                    "type": "integer"
                },
                "quantity": {
                    "type": "number"
                }
            },
            "required": [
                "branchCode",
                "packagingNumber",
                "productCode",
                "quantity"
            ]
        },
    ),
    types.Tool(
        name="totvs_add_product_packaging_quantity",
        description="⚠️ ESCRITA — Adiciona quantidade de produto a uma embalagem logistica.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "packagingNumber": {
                    "type": "integer"
                },
                "productCode": {
                    "type": "integer"
                },
                "quantity": {
                    "type": "number"
                }
            },
            "required": [
                "branchCode",
                "packagingNumber",
                "productCode",
                "quantity"
            ]
        },
    ),
    types.Tool(
        name="totvs_subtract_product_packaging_quantity",
        description="⚠️ ESCRITA — Subtrai quantidade de produto de uma embalagem logistica.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "packagingNumber": {
                    "type": "integer"
                },
                "productCode": {
                    "type": "integer"
                },
                "quantity": {
                    "type": "number"
                }
            },
            "required": [
                "branchCode",
                "packagingNumber",
                "productCode",
                "quantity"
            ]
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_product_storage": "search_product_storage",
    "totvs_upsert_product_packaging": "upsert_product_packaging",
    "totvs_add_product_packaging_quantity": "add_product_packaging",
    "totvs_subtract_product_packaging_quantity": "subtract_product_packaging",
}