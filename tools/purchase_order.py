"""Purchase Order Tools — /api/totvsmoda/purchase-order/v2/"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults
from tools._dates import normalize_day_ranges

logger = logging.getLogger("totvs-moda-mcp.purchase-order")
BASE = "/api/totvsmoda/purchase-order/v2"


class PurchaseOrderTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_purchase_orders(self, args: dict[str, Any]) -> Any:
        """POST /search — Consulta pedidos de compra."""
        args = inject_branch_defaults(args)
        args = normalize_day_ranges(args)
        flt: dict[str, Any] = {}
        # API espera branchCodeList (array)
        if args.get("branchCodeList"):
            flt["branchCodeList"] = args["branchCodeList"]
        elif args.get("branchCode"):
            flt["branchCodeList"] = [args["branchCode"]]

        filter_fields = (
            "change",
            "orderCodeList",
            "supplierOrderCodeList",
            "supplierCodeList",
            "supplierCpfCnpjList",
            "orderStatusList",
            "operationCodeList",
            "startBasePaymentDate",
            "endBasePaymentDate",
            "startDeliveryForecastDate",
            "endDeliveryForecastDate",
            "startDeliveryDeadlineDate",
            "endDeliveryDeadlineDate",
            "productCodeList",
        )
        for field in filter_fields:
            if args.get(field) is not None:
                flt[field] = args[field]

        # Backward-compatible aliases used by earlier MCP versions.
        if args.get("statusList") is not None and "orderStatusList" not in flt:
            flt["orderStatusList"] = args["statusList"]
        if args.get("startDate") is not None or args.get("endDate") is not None:
            flt.setdefault("change", {})
            if args.get("startDate") is not None:
                flt["change"]["startDate"] = args["startDate"]
            if args.get("endDate") is not None:
                flt["change"]["endDate"] = args["endDate"]

        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        if args.get("expand"):
            body["expand"] = args["expand"]
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE}/search", body)
        return apply_fields(result, args)

    async def create_purchase_order(self, args: dict[str, Any]) -> Any:
        """POST /orders — ⚠️ Inclui pedido de compra."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/orders", body)

    async def cancel_purchase_order(self, args: dict[str, Any]) -> Any:
        """POST /orders/cancel — ⚠️ Cancela pedido de compra."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/orders/cancel", body)

    async def change_purchase_order_status(self, args: dict[str, Any]) -> Any:
        """POST /orders/change-status — ⚠️ Altera situação do pedido de compra."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/orders/change-status", body)

    async def link_purchase_order_batch(self, args: dict[str, Any]) -> Any:
        """POST /purchase-order/batch-link - cria/atualiza vinculo de lote com pedido e NF."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/purchase-order/batch-link", body)

    async def update_purchase_order_item_quantities(self, args: dict[str, Any]) -> Any:
        """POST /quantity-items - altera quantidade solicitada dos itens."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/quantity-items", body)


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_purchase_orders",
        description=(
            "Pedidos de compra por filtro. Use expand='items' para carregar itens. Use fields para reduzir tokens."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "branchCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Lista de códigos de empresa"
                },
                "change": {
                    "type": "object",
                    "description": "Filtro oficial por alteração: {startDate,endDate}. Quando informado, use branchCodeList."
                },
                "orderCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos dos pedidos de compra"
                },
                "supplierOrderCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Números de pedido do fornecedor"
                },
                "supplierCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos dos fornecedores"
                },
                "supplierCpfCnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "CPF/CNPJ dos fornecedores"
                },
                "orderStatusList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Situação do pedido: 1=Em andamento, 2=Liberado baixa, 3=Parcialmente recebido, 4=Atendido, 5=Bloqueado, 6=Cancelado, 7=Distribuído, 8=Pré-pedido"
                },
                "statusList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Alias legado de orderStatusList"
                },
                "operationCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "startBasePaymentDate": {
                    "type": "string"
                },
                "endBasePaymentDate": {
                    "type": "string"
                },
                "startDeliveryForecastDate": {
                    "type": "string"
                },
                "endDeliveryForecastDate": {
                    "type": "string"
                },
                "startDeliveryDeadlineDate": {
                    "type": "string"
                },
                "endDeliveryDeadlineDate": {
                    "type": "string"
                },
                "productCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "startDate": {
                    "type": "string",
                    "description": "Alias legado para change.startDate"
                },
                "endDate": {
                    "type": "string",
                    "description": "Alias legado para change.endDate"
                },
                "expand": {
                    "type": "string",
                    "description": "Expansões suportadas pelo Swagger: items"
                },
                "order": {
                    "type": "string",
                    "description": "Ordenação suportada: branchCode, orderCode, maxChangeFilterDate. Use - para desc."
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
        name="totvs_create_purchase_order",
        description="⚠️ Inclui pedido de compra.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "supplierCode": {
                    "type": "integer"
                },
                "operationCode": {
                    "type": "integer"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "orderDate": {
                    "type": "string"
                }
            },
            "required": [
                "branchCode",
                "supplierCode",
                "operationCode",
                "items"
            ]
        },
    ),
    types.Tool(
        name="totvs_cancel_purchase_order",
        description="⚠️ Cancela pedido de compra.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "reasonCancellationCode": {
                    "type": "integer"
                }
            },
            "required": [
                "branchCode",
                "orderCode"
            ]
        },
    ),
    types.Tool(
        name="totvs_change_purchase_order_status",
        description="⚠️ Altera situação do pedido de compra.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "newStatus": {
                    "type": "string"
                }
            },
            "required": [
                "branchCode",
                "orderCode",
                "newStatus"
            ]
        },
    ),
    types.Tool(
        name="totvs_link_purchase_order_batch",
        description="⚠️ ESCRITA — Cria ou atualiza vinculo de item de lote com pedido de compra e nota fiscal.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "batchCode": {
                    "type": "integer"
                },
                "sequence": {
                    "type": "integer"
                },
                "batchItemBarCode": {
                    "type": "string"
                },
                "orderCode": {
                    "type": "integer"
                },
                "invoice": {
                    "type": "object"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_update_purchase_order_item_quantities",
        description="⚠️ ESCRITA — Altera quantidade solicitada dos itens de um pedido de compra.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            }
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_purchase_orders": "search_purchase_orders",
    "totvs_create_purchase_order": "create_purchase_order",
    "totvs_cancel_purchase_order": "cancel_purchase_order",
    "totvs_change_purchase_order_status": "change_purchase_order_status",
    "totvs_link_purchase_order_batch": "link_purchase_order_batch",
    "totvs_update_purchase_order_item_quantities": "update_purchase_order_item_quantities",
}