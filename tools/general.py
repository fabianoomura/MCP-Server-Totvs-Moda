"""
General Tools
=============
API General v2 — /api/totvsmoda/general/v2/
Condições de pagamento, operações, devoluções, transações, contagens.
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._defaults import inject_branch_defaults
from tools._fields import apply_fields
import response_cache as cache

logger = logging.getLogger("totvs-moda-mcp.general")
BASE = "/api/totvsmoda/general/v2"


def _pascal_params(args: dict[str, Any]) -> dict[str, Any]:
    special = {"customerCpfCnpjList": "CustomerCPFCNPJList"}
    params: dict[str, Any] = {}
    for key, value in args.items():
        if value is None or key in {"branchCode", "fields"}:
            continue
        params[special.get(key, key[:1].upper() + key[1:])] = value
    return params


class GeneralTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def get_payment_conditions(self, args: dict[str, Any]) -> Any:
        """GET /payment-conditions — Condições de pagamento disponíveis."""
        params = {k: v for k, v in args.items() if v is not None and k != "fields"}
        cached = cache.get("payment_cond", params, cache.REFERENCE)
        if cached is not None:
            return apply_fields(cached, args)
        result = await self.client.get(f"{BASE}/payment-conditions", params=params or None)
        cache.put("payment_cond", params, result)
        return apply_fields(result, args)

    async def get_operations(self, args: dict[str, Any]) -> Any:
        """GET /operations — Operações disponíveis."""
        params = {k: v for k, v in args.items() if v is not None and k != "fields"}
        cached = cache.get("operations", params, cache.REFERENCE)
        if cached is not None:
            return apply_fields(cached, args)
        result = await self.client.get(f"{BASE}/operations", params=params or None)
        cache.put("operations", params, result)
        return apply_fields(result, args)

    async def get_payment_plans(self, args: dict[str, Any]) -> Any:
        """GET /payment-plans — Planos de pagamento ativos."""
        result = await self.client.get(f"{BASE}/payment-plans")
        return apply_fields(result, args)

    async def simulate_payment_plan(self, args: dict[str, Any]) -> Any:
        """POST /payment-plan-simulate — Simula cálculo de plano de pagamento."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/payment-plan-simulate", body)

    async def search_devolutions(self, args: dict[str, Any]) -> Any:
        """GET /devolutions/search — Dados de devolução por estágio."""
        args = inject_branch_defaults(args)
        params = {k: v for k, v in args.items() if v is not None and k != "fields"}
        result = await self.client.get(f"{BASE}/devolutions/search", params=params or None)
        return apply_fields(result, args)

    async def get_transactions(self, args: dict[str, Any]) -> Any:
        """GET /transactions — Dados de uma transação."""
        params = {k: v for k, v in args.items() if v is not None and k != "fields"}
        result = await self.client.get(f"{BASE}/transactions", params=params or None)
        return apply_fields(result, args)

    async def get_classifications(self, args: dict[str, Any]) -> Any:
        """GET /classifications — Classificações disponíveis."""
        result = await self.client.get(f"{BASE}/classifications")
        return apply_fields(result, args)

    async def search_transactions(self, args: dict[str, Any]) -> Any:
        """GET /transactions/search - lista transacoes por filial, cliente, data e alteracao."""
        args = inject_branch_defaults(args)
        args = dict(args)
        if not args.get("branchCodeList") and args.get("branchCode") is not None:
            args["branchCodeList"] = [args["branchCode"]]
        if not args.get("branchCodeList"):
            raise ValueError("branchCode ou branchCodeList e obrigatorio.")
        result = await self.client.get(f"{BASE}/transactions/search", params=_pascal_params(args))
        return apply_fields(result, args)

    async def create_devolution(self, args: dict[str, Any]) -> Any:
        """POST /devolutions/create — ⚠️ Grava dados de devolução."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/devolutions/create", body)

    async def create_transaction(self, args: dict[str, Any]) -> Any:
        """POST /transactions — ⚠️ Inclui transação."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/transactions", body)

    async def create_product_count(self, args: dict[str, Any]) -> Any:
        """POST /product-counts — ⚠️ Criação de contagem com produtos."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product-counts", body)

    async def create_financial_compensation(self, args: dict[str, Any]) -> Any:
        """POST /financial-compensations - write financeiro."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/financial-compensations", body)

    async def add_product_count_additional_count(self, args: dict[str, Any]) -> Any:
        """POST /product-counts/additional-count - adiciona contagem complementar."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product-counts/additional-count", body)

    async def create_relationship_counts(self, args: dict[str, Any]) -> Any:
        """POST /relationship-counts - relaciona contagens a transacao."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/relationship-counts", body)

    async def create_transaction_classification_relationship(self, args: dict[str, Any]) -> Any:
        """POST /transaction-classification-relationship/create - vincula classificacoes a transacao."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/transaction-classification-relationship/create", body)


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_get_payment_conditions",
        description="Condições de pagamento disponíveis.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_operations",
        description="Operações disponíveis (entrada/saída). Requer ao menos um filtro.",
        inputSchema={
            "type": "object",
            "properties": {
                "operationCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "operationTypeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "E - Entrada, S - Saída"
                },
                "startChangeDate": {
                    "type": "string"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "isInactive": {
                    "type": "boolean",
                    "description": "true=inativas, false=ativas"
                },
                "pageSize": {
                    "type": "integer",
                    "default": 1000
                }
            }
        },
    ),
    types.Tool(
        name="totvs_simulate_payment_plan",
        description="Simula cálculo de plano de pagamento.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "paymentPlanCode": {
                    "type": "integer"
                },
                "totalAmount": {
                    "type": "number"
                }
            },
            "required": [
                "branchCode",
                "paymentPlanCode",
                "totalAmount"
            ]
        },
    ),
    types.Tool(
        name="totvs_search_devolutions",
        description="Consulta dados de devolução por código.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "devolutionCode": {
                    "type": "integer"
                },
                "expand": {
                    "type": "string",
                    "description": "classifications, items"
                }
            },
            "required": [
                "branchCode",
                "devolutionCode"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_payment_plans",
        description="Planos de pagamento ativos disponíveis.",
        inputSchema={
            "type": "object",
            "properties": {}
        },
    ),
    types.Tool(
        name="totvs_get_transactions",
        description="Dados de uma transação por filial e código.",
        inputSchema={
            "type": "object",
            "properties": {
                "BranchCode": {
                    "type": "integer"
                },
                "TransactionCode": {
                    "type": "integer"
                },
                "TransactionDate": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_search_transactions",
        description=(
            "Lista transacoes por filial, cliente, data, alteracao e expansao. Use para consultar movimentos/transacoes sem saber o codigo exato."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Filial; usado para montar branchCodeList quando branchCodeList nao vier"
                },
                "branchCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Obrigatorio no Swagger"
                },
                "transactionCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "transactionDate": {
                    "type": "string"
                },
                "customerCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "customerCpfCnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "startChangeDate": {
                    "type": "string"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "expand": {
                    "type": "string",
                    "description": "itemPromotionalEngines,originDestination,additionalInformation"
                },
                "order": {
                    "type": "string",
                    "description": "branchCode,transactionCode,transactionDate,maxChangeFilterDate"
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximo 500 no Swagger"
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
        name="totvs_get_classifications",
        description="Classificações de produto disponíveis.",
        inputSchema={
            "type": "object",
            "properties": {}
        },
    ),
    types.Tool(
        name="totvs_create_devolution",
        description="⚠️ Grava dados de devolução.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "devolutionCode": {
                    "type": "integer"
                },
                "stage": {
                    "type": "string"
                }
            },
            "required": [
                "branchCode",
                "devolutionCode"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_transaction",
        description="⚠️ Inclui uma transação.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "transactionCode": {
                    "type": "integer"
                },
                "transactionDate": {
                    "type": "string"
                }
            },
            "required": [
                "branchCode",
                "transactionCode"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_product_count",
        description="⚠️ Cria contagem de produtos no estoque.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "branchCode",
                "products"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_financial_compensation",
        description="⚠️ ESCRITA — Cria compensacao financeira conforme payload oficial do Swagger.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
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
    types.Tool(
        name="totvs_add_product_count_additional_count",
        description="⚠️ ESCRITA — Adiciona contagem complementar a uma contagem de produto.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "countNumber": {
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
    types.Tool(
        name="totvs_create_relationship_counts",
        description="⚠️ ESCRITA — Relaciona contagens a uma transacao.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "transactionCode": {
                    "type": "integer"
                },
                "transactionDate": {
                    "type": "string"
                },
                "counts": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            }
        },
    ),
    types.Tool(
        name="totvs_create_transaction_classification_relationship",
        description="⚠️ ESCRITA — Vincula classificacoes a uma transacao.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "transactionCode": {
                    "type": "integer"
                },
                "transactionDate": {
                    "type": "string"
                },
                "classifications": {
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
    "totvs_get_payment_conditions": "get_payment_conditions",
    "totvs_get_operations": "get_operations",
    "totvs_simulate_payment_plan": "simulate_payment_plan",
    "totvs_search_devolutions": "search_devolutions",
    "totvs_get_payment_plans": "get_payment_plans",
    "totvs_get_transactions": "get_transactions",
    "totvs_search_transactions": "search_transactions",
    "totvs_get_classifications": "get_classifications",
    "totvs_create_devolution": "create_devolution",
    "totvs_create_transaction": "create_transaction",
    "totvs_create_product_count": "create_product_count",
    "totvs_create_financial_compensation": "create_financial_compensation",
    "totvs_add_product_count_additional_count": "add_product_count_additional_count",
    "totvs_create_relationship_counts": "create_relationship_counts",
    "totvs_create_transaction_classification_relationship": "create_transaction_classification_relationship",
}