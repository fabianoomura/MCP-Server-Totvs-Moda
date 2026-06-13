"""
Voucher Tools
=============
API Voucher v2 — /api/totvsmoda/voucher/v2/
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults
import response_cache as cache

logger = logging.getLogger("totvs-moda-mcp.voucher")
BASE = "/api/totvsmoda/voucher/v2"


class VoucherTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    def _invalidate_after_write(self) -> None:
        for prefix in (
            "receivable",
            "dashboard",
            "customer360",
            "overdue_financial",
            "cash_flow",
        ):
            cache.invalidate(prefix)

    async def search_voucher(self, args: dict[str, Any]) -> Any:
        """GET /search — Lista vouchers por filtro (query params)."""
        params = {k: v for k, v in args.items() if k not in ("fields",) and v is not None}
        result = await self.client.get(f"{BASE}/search", params=params or None)
        return apply_fields(result, args)

    async def get_voucher(self, args: dict[str, Any]) -> Any:
        """GET /{id} — Retorna voucher por ID."""
        return await self.client.get(f"{BASE}/{args['id']}")

    async def create_voucher(self, args: dict[str, Any]) -> Any:
        """POST /create — ⚠️ Inclui voucher."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/create", body)
        self._invalidate_after_write()
        return result

    async def update_voucher(self, args: dict[str, Any]) -> Any:
        """POST /update — ⚠️ Altera voucher."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/update", body)
        self._invalidate_after_write()
        return result

    async def create_customer_vouchers(self, args: dict[str, Any]) -> Any:
        """POST /customer/create — ⚠️ Cria vouchers para lista de clientes."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/customer/create", body)
        self._invalidate_after_write()
        return result


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

WRITE_TOOL_ANNOTATIONS: dict[str, bool] = {
    "destructiveHint": True,
    "idempotentHint": False,
    "readOnlyHint": False,
    "openWorldHint": True,
}

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_voucher",
        description="Consulta vouchers/cupons. Use fields para reduzir tokens.",
        inputSchema={
            "type": "object",
            "properties": {
                "voucherCode": {
                    "type": "string"
                },
                "customerCode": {
                    "type": "integer"
                },
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
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
        name="totvs_create_voucher",
        description="⚠️ ESCRITA — Cria voucher/cupom.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "value": {
                    "type": "number"
                },
                "expirationDate": {
                    "type": "string"
                },
                "customerCode": {
                    "type": "integer"
                }
            },
            "required": [
                "branchCode",
                "value"
            ]
        },
        annotations=WRITE_TOOL_ANNOTATIONS,
    ),
    types.Tool(
        name="totvs_update_voucher",
        description="⚠️ Altera dados de um voucher existente.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "voucherCode": {
                    "type": "integer"
                },
                "value": {
                    "type": "number"
                },
                "expirationDate": {
                    "type": "string"
                }
            },
            "required": [
                "branchCode",
                "voucherCode"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_customer_vouchers",
        description="⚠️ Cria vouchers em lote para uma lista de clientes.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "customerCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "value": {
                    "type": "number"
                },
                "expirationDate": {
                    "type": "string"
                }
            },
            "required": [
                "branchCode",
                "customerCodeList",
                "value"
            ]
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_voucher": "search_voucher",
    "totvs_create_voucher": "create_voucher",
    "totvs_update_voucher": "update_voucher",
    "totvs_create_customer_vouchers": "create_customer_vouchers",
}