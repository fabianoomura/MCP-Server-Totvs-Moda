"""
Management, Location, and Production Order Tools
=================================================
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults

logger = logging.getLogger("totvs-moda-mcp.other")


"""Management Tools — /api/totvsmoda/management/v2/"""


class ManagementTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client
        self.BASE = "/api/totvsmoda/management/v2"

    async def get_users(self, args: dict[str, Any]) -> Any:
        """GET /users — Lista usuários do sistema."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{self.BASE}/users", params=params or None)

    async def get_global_parameters(self, args: dict[str, Any]) -> Any:
        """GET /global-parameter — Parâmetros corporativos. ParameterCodeList obrigatório."""
        params: dict[str, Any] = {"ParameterCodeList": args["parameterCodeList"]}
        return await self.client.get(f"{self.BASE}/global-parameter", params=params)

    async def get_branch_parameters(self, args: dict[str, Any]) -> Any:
        """GET /branch-parameter — Parâmetros por empresa. BranchCodeList e ParameterCodeList obrigatórios."""
        params: dict[str, Any] = {
            "BranchCodeList": args["branchCodeList"],
            "ParameterCodeList": args["parameterCodeList"],
        }
        return await self.client.get(f"{self.BASE}/branch-parameter", params=params)


"""Global / Location Tools — /api/totvsmoda/location/v2/"""


class GlobalTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client
        self.BASE = "/api/totvsmoda/location/v2"

    async def get_cep(self, args: dict[str, Any]) -> Any:
        """GET /ceps/{cep} — Dados de endereço pelo CEP."""
        cep = args["cep"]
        return await self.client.get(f"{self.BASE}/ceps/{cep}")

    async def get_countries(self, args: dict[str, Any]) -> Any:
        """GET /country — Lista países."""
        return await self.client.get(f"{self.BASE}/country")

    async def get_states(self, args: dict[str, Any]) -> Any:
        """GET /state — Lista estados."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{self.BASE}/state", params=params or None)

    async def get_cities(self, args: dict[str, Any]) -> Any:
        """GET /city — Lista cidades."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{self.BASE}/city", params=params or None)


"""Production Order Tools — /api/totvsmoda/production-order/v2/"""


class ProductionOrderTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client
        self.BASE = "/api/totvsmoda/production-order/v2"

    async def search_production_orders(self, args: dict[str, Any]) -> Any:
        """POST /orders/search — Consulta ordens de produção."""
        args = inject_branch_defaults(args)
        filter_fields = (
            "change",
            "branchCodeList",
            "cycleCodeList",
            "orderCodeList",
            "statusList",
            "placeCodeList",
            "materialClassificationList",
        )
        flt = {k: v for k, v in args.items() if k in filter_fields and v is not None}
        # API espera branchCodeList (array)
        if "branchCodeList" not in flt:
            if args.get("branchCode"):
                flt["branchCodeList"] = [args["branchCode"]]

        # Backward-compatible aliases used by earlier MCP versions.
        if args.get("startDate") is not None or args.get("endDate") is not None:
            flt.setdefault("change", {})
            if args.get("startDate") is not None:
                flt["change"]["startDate"] = args["startDate"]
            if args.get("endDate") is not None:
                flt["change"]["endDate"] = args["endDate"]

        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("expand"):
            body["expand"] = args["expand"]
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{self.BASE}/orders/search", body)
        return apply_fields(result, args)

    async def get_pending_material_consumption(self, args: dict[str, Any]) -> Any:
        """POST /pending-material-consumption — Fichas de consumo pendentes."""
        required_filters = ("rawMaterialCodeList", "materialClassificationList")
        if not any(args.get(key) for key in required_filters):
            raise ValueError(
                "Informe rawMaterialCodeList ou materialClassificationList para consultar consumo pendente."
            )
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        return await self.client.post(f"{self.BASE}/pending-material-consumption", body)

    async def create_material_movement(self, args: dict[str, Any]) -> Any:
        """POST /materials/movement — ⚠️ Movimentação de matéria prima."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{self.BASE}/materials/movement", body)


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

MANAGEMENT_TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_get_users",
        description="Lista usuários do TOTVS Moda.",
        inputSchema={
            "type": "object",
            "properties": {}
        },
    ),
    types.Tool(
        name="totvs_get_global_parameters",
        description="Parâmetros corporativos do TOTVS por código.",
        inputSchema={
            "type": "object",
            "properties": {
                "parameterCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Códigos dos parâmetros (obrigatório)"
                }
            },
            "required": [
                "parameterCodeList"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_branch_parameters",
        description="Parâmetros de filial por código.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos das filiais (obrigatório)"
                },
                "parameterCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Códigos dos parâmetros (obrigatório)"
                }
            },
            "required": [
                "branchCodeList",
                "parameterCodeList"
            ]
        },
    ),
]

MANAGEMENT_ROUTES: dict[str, str] = {
    "totvs_get_users": "get_users",
    "totvs_get_global_parameters": "get_global_parameters",
    "totvs_get_branch_parameters": "get_branch_parameters",
}


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

GLOBAL_TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_get_cep",
        description="Endereço completo pelo CEP.",
        inputSchema={
            "type": "object",
            "properties": {
                "cep": {
                    "type": "string",
                    "description": "Somente dígitos ex: 86020040"
                }
            },
            "required": [
                "cep"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_countries",
        description="Lista de países disponíveis.",
        inputSchema={
            "type": "object",
            "properties": {}
        },
    ),
    types.Tool(
        name="totvs_get_states",
        description="Lista de estados/UFs.",
        inputSchema={
            "type": "object",
            "properties": {
                "countryCode": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_cities",
        description="Lista de cidades.",
        inputSchema={
            "type": "object",
            "properties": {
                "stateCode": {
                    "type": "string"
                },
                "countryCode": {
                    "type": "string"
                }
            }
        },
    ),
]

GLOBAL_ROUTES: dict[str, str] = {
    "totvs_get_cep": "get_cep",
    "totvs_get_countries": "get_countries",
    "totvs_get_states": "get_states",
    "totvs_get_cities": "get_cities",
}


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

PRODUCTION_ORDER_TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_production_orders",
        description=(
            "Ordens de produção por filtro. Use expand para carregar grupos como items, materials, locations e productionNotes. Use fields para reduzir tokens."
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
                    "description": "Lista de empresas"
                },
                "change": {
                    "type": "object",
                    "description": "Filtro oficial por alteração: {startDate,endDate}. Quando informado, use branchCodeList."
                },
                "cycleCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Lista de ciclos"
                },
                "orderCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Lista de ordens de produção"
                },
                "statusList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Status: 5=Bloqueada, 10=Aguardando liberação, 20=Em andamento, 30=Finalizada, 40=Cancelada"
                },
                "placeCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Lista de locais da OP"
                },
                "materialClassificationList": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    },
                    "description": "Classificações de matéria-prima: [{typeCode, classificationCodeList}]"
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
                    "description": "Expansões suportadas: observations,classifications,references,locations,programmings,items,materials,relationships,relationshipItems,productionNotes,productFinishedQuantitiesTypes,orderFinishedQuantitiesTypes"
                },
                "order": {
                    "type": "string",
                    "description": "Ordenação suportada: branchCode, cycleCode, orderCode, maxChangeFilterDate. Use - para desc."
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100,
                    "description": "Máximo 500 no Swagger"
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
        name="totvs_get_pending_material_consumption",
        description="Fichas de consumo de matéria-prima pendentes em ordens de produção.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "startDate": {
                    "type": "string"
                },
                "endDate": {
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
        name="totvs_create_material_movement",
        description="⚠️ Movimentação de matéria-prima em ordem de produção.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "movementDate": {
                    "type": "string"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "branchCode",
                "orderCode",
                "movementDate",
                "items"
            ]
        },
    ),
]

PRODUCTION_ORDER_ROUTES: dict[str, str] = {
    "totvs_search_production_orders": "search_production_orders",
    "totvs_get_pending_material_consumption": "get_pending_material_consumption",
    "totvs_create_material_movement": "create_material_movement",
}