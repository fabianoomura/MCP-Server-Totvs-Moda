"""
Management, Location, and Production Order Tools
=================================================
"""
import logging
from typing import Any
import response_cache as cache
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

    async def create_production_order(self, args: dict[str, Any]) -> Any:
        """POST /orders — ⚠️ Inclui ordem de produção.

        O contrato tem pares mutuamente exclusivos (produto x código de barras,
        consumo unitário x total, programação por código x por locais). A API
        não documenta qual prevalece quando os dois vêm, então rejeitamos antes.
        """
        args = inject_branch_defaults(args)

        def exactly_one(obj: dict[str, Any], a: str, b: str, where: str) -> None:
            has_a, has_b = obj.get(a) is not None, obj.get(b) is not None
            if has_a == has_b:
                raise ValueError(f"{where}: informe {a} ou {b} (exatamente um).")

        def at_most_one(obj: dict[str, Any], a: str, b: str, where: str) -> None:
            if obj.get(a) is not None and obj.get(b) is not None:
                raise ValueError(f"{where}: informe {a} ou {b}, não os dois.")

        if not args.get("items"):
            raise ValueError("items: informe ao menos um produto para a OP.")
        for i, item in enumerate(args["items"], 1):
            exactly_one(item, "productCode", "barCode", f"items[{i}]")
            for j, mat in enumerate(item.get("materials") or [], 1):
                where = f"items[{i}].materials[{j}]"
                exactly_one(mat, "materialCode", "barCode", where)
                exactly_one(mat, "quantityConsumption", "totalQuantityConsumption", where)
            for j, svc in enumerate(item.get("services") or [], 1):
                at_most_one(svc, "quantity", "totalQuantity", f"items[{i}].services[{j}]")

        programming = args.get("programming")
        if programming:
            by_code = programming.get("programmingCode") is not None
            if by_code == bool(programming.get("locations")):
                raise ValueError(
                    "programming: informe programmingCode (programação existente) "
                    "ou locations (locais), não os dois nem nenhum."
                )
            if by_code:
                programming.setdefault("branchCode", args["branchCode"])

        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{self.BASE}/orders", body)
        cache.invalidate("open_production_orders")
        return result


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
    types.Tool(
        name="totvs_create_production_order",
        description=(
            "⚠️ ESCRITA — Inclui ordem de produção (POST /production-order/v2/orders). "
            "Exige confirmação explícita. O número da OP é gerado pela API. "
            "Obrigatórios: branchCode, cycleCode, personCode (cliente da OP), finalizationOperation, "
            "rawMaterialRemovalOperation, rawMaterialReturnOperation, status (5=Bloqueada, "
            "10=Aguardando liberação) e items[]. Em cada item informe productCode OU barCode; em cada "
            "matéria-prima, materialCode OU barCode e quantityConsumption (unitário, multiplicado pela "
            "quantidade do item) OU totalQuantityConsumption. Pares informados juntos são rejeitados."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {"type": "integer", "description": "Empresa da OP"},
                "cycleCode": {"type": "integer", "description": "Ciclo da OP"},
                "personOrderCode": {"type": "string", "description": "Código da OP do cliente"},
                "personCode": {"type": "integer", "description": "Cliente da OP"},
                "finalizationOperation": {"type": "integer", "description": "Operação de finalização da OP"},
                "rawMaterialRemovalOperation": {"type": "integer", "description": "Operação de baixa de MP"},
                "rawMaterialReturnOperation": {"type": "integer", "description": "Operação de retorno de MP"},
                "startMovimentDate": {"type": "string", "description": "Data do movimento inicial (YYYY-MM-DD)"},
                "estimatedDeliveryDate": {"type": "string", "description": "Previsão de entrega (YYYY-MM-DD)"},
                "priority": {"type": "integer", "description": "Código de prioridade"},
                "status": {"type": "integer", "enum": [5, 10], "description": "5=Bloqueada, 10=Aguardando liberação"},
                "category": {"type": "integer", "description": "Código de categoria"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "productCode": {"type": "integer", "description": "SKU TOTVS do produto (ou barCode)"},
                            "barCode": {"type": "string", "description": "Código de barras do produto (ou productCode)"},
                            "quantity": {"type": "number"},
                            "materials": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "materialCode": {"type": "integer", "description": "SKU TOTVS da MP (ou barCode)"},
                                        "barCode": {"type": "string", "description": "Código de barras da MP (ou materialCode)"},
                                        "quantityConsumption": {"type": "number", "description": "Consumo unitário (ou totalQuantityConsumption)"},
                                        "totalQuantityConsumption": {"type": "number", "description": "Consumo total (ou quantityConsumption)"}
                                    }
                                }
                            },
                            "services": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "serviceCode": {"type": "integer"},
                                        "quantity": {"type": "number", "description": "Quantidade unitária (ou totalQuantity)"},
                                        "totalQuantity": {"type": "number", "description": "Quantidade total (ou quantity)"},
                                        "value": {"type": "number", "description": "Valor unitário do serviço"}
                                    }
                                }
                            }
                        },
                        "required": ["quantity"]
                    }
                },
                "programming": {
                    "type": "object",
                    "description": "Programação: programmingCode (existente) OU locations[] (locais), não os dois",
                    "properties": {
                        "branchCode": {"type": "integer", "description": "Empresa da programação (default: a da OP)"},
                        "programmingCode": {"type": "integer"},
                        "locations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "orderSequence": {"type": "integer"},
                                    "locationCode": {"type": "integer"}
                                }
                            }
                        }
                    }
                },
                "salesOrders": {
                    "type": "array",
                    "description": "Pedidos de venda vinculados",
                    "items": {
                        "type": "object",
                        "properties": {"branchCode": {"type": "integer"}, "orderCode": {"type": "integer"}}
                    }
                },
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"typeCode": {"type": "integer"}, "classificationCode": {"type": "string"}}
                    }
                },
                "observations": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"observation": {"type": "string"}}}
                }
            },
            "required": [
                "branchCode", "cycleCode", "personCode", "finalizationOperation",
                "rawMaterialRemovalOperation", "rawMaterialReturnOperation", "status", "items"
            ]
        },
    ),
]

PRODUCTION_ORDER_ROUTES: dict[str, str] = {
    "totvs_search_production_orders": "search_production_orders",
    "totvs_get_pending_material_consumption": "get_pending_material_consumption",
    "totvs_create_material_movement": "create_material_movement",
    "totvs_create_production_order": "create_production_order",
}