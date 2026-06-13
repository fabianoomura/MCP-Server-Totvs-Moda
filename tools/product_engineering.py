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


def _pascal_params(args: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for field in fields:
        value = args.get(field)
        if value is None:
            value = args.get(field[:1].lower() + field[1:])
        if value is not None:
            params[field] = value
    return params


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

    async def search_services(self, args: dict[str, Any]) -> Any:
        """POST /services/search."""
        top_level = {"filter", "page", "pageSize", "expand", "order", "fields"}
        flt = dict(args.get("filter") or {})
        for key, value in args.items():
            if key not in top_level and value is not None:
                flt[key] = value
        if not flt:
            raise ValueError("Informe ao menos um filtro para services/search, como status, serviceCodeList, serviceName ou change.")

        body: dict[str, Any] = {
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        body["filter"] = flt
        if args.get("expand"):
            body["expand"] = args["expand"]
        if args.get("order"):
            body["order"] = args["order"]

        result = await self.client.post(f"{BASE}/services/search", body)
        return apply_fields(result, args)

    async def get_operations(self, args: dict[str, Any]) -> Any:
        """GET /operations."""
        params = _pascal_params(
            args,
            (
                "StartChangeDate",
                "EndChangeDate",
                "OperationCodeList",
                "OperationTypeList",
                "Page",
                "PageSize",
                "Order",
            ),
        )
        params.setdefault("Page", args.get("page", 1))
        params.setdefault("PageSize", args.get("pageSize", 100))
        result = await self.client.get(f"{BASE}/operations", params=params)
        return apply_fields(result, args)

    async def search_applications(self, args: dict[str, Any]) -> Any:
        """GET /applications/search."""
        params = _pascal_params(
            args,
            (
                "StartChangeDate",
                "EndChangeDate",
                "ApplicationCodeList",
                "ApplicationTypeList",
                "Page",
                "PageSize",
                "Order",
            ),
        )
        params.setdefault("Page", args.get("page", 1))
        params.setdefault("PageSize", args.get("pageSize", 100))
        result = await self.client.get(f"{BASE}/applications/search", params=params)
        return apply_fields(result, args)

    async def search_engineering_default(self, args: dict[str, Any]) -> Any:
        """POST /engineering-default/search."""
        excluded = ("page", "pageSize", "fields")
        body = {k: v for k, v in args.items() if k not in excluded and v is not None}
        body["page"] = args.get("page", 1)
        body["pageSize"] = args.get("pageSize", 100)
        result = await self.client.post(f"{BASE}/engineering-default/search", body)
        return apply_fields(result, args)

    async def get_engineering_configurations(self, args: dict[str, Any]) -> Any:
        """GET /engineering-configurations."""
        params = _pascal_params(
            args,
            ("BranchCode", "PurposeType", "ClassificationCodeList", "ClassificationType"),
        )
        result = await self.client.get(f"{BASE}/engineering-configurations", params=params)
        return apply_fields(result, args)

    async def create_references_from_engineering(self, args: dict[str, Any]) -> Any:
        """POST /references - cadastra produto a partir da engenharia padrao."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/references", body)


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_consumption_sheet",
        description=(
            "Ficha de consumo de produto (matéria-prima + serviços). Retorna items[] com: productCode, productName, referenceCode, colorCode, size, rawMaterials[]={rawMaterialCode, rawMaterialDescription, consumptionQuantity, applicationCode, applicationDescription}, services[]={serviceCode, serviceDescription, serviceApplication, serviceAmount}. Use fields para reduzir tokens."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "productCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Lista de códigos de produto"
                },
                "referenceCode": {
                    "type": "string",
                    "description": "Código de referência do produto"
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
                    },
                    "description": "Lista opcional de campos a retornar. Reduz tokens."
                }
            }
        },
    ),
    types.Tool(
        name="totvs_search_engineering_services",
        description=(
            "Servicos de engenharia de produto. Requer ao menos um filtro; para consulta ampla use status=true. Use expand='dataProviders,dataLevelGroup' quando precisar de fornecedores/niveis."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "object",
                    "description": "ServiceFilterModel completo"
                },
                "change": {
                    "type": "object",
                    "description": "{startDate,endDate}"
                },
                "startServiceCode": {
                    "type": "integer"
                },
                "endServiceCode": {
                    "type": "integer"
                },
                "serviceCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "serviceName": {
                    "type": "string"
                },
                "codeTypeService": {
                    "type": "integer"
                },
                "providerInfo": {
                    "type": "object"
                },
                "status": {
                    "type": "boolean"
                },
                "expand": {
                    "type": "string",
                    "description": "dataProviders,dataLevelGroup"
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
        name="totvs_get_engineering_operations",
        description="Operacoes de engenharia de produto.",
        inputSchema={
            "type": "object",
            "properties": {
                "startChangeDate": {
                    "type": "string"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "operationCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "operationTypeList": {
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
                "order": {
                    "type": "string"
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
        name="totvs_search_engineering_applications",
        description="Aplicacoes de engenharia de produto.",
        inputSchema={
            "type": "object",
            "properties": {
                "startChangeDate": {
                    "type": "string"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "applicationCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "applicationTypeList": {
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
                "order": {
                    "type": "string"
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
        name="totvs_search_engineering_default",
        description="Estrutura base de engenharia por produto/grupo/referencia.",
        inputSchema={
            "type": "object",
            "properties": {
                "startChangeDate": {
                    "type": "string"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "rawMaterialColorBranchCodes": {
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
                "groupCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "referenceCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
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
                    }
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_engineering_configurations",
        description="Configuracoes de engenharia por classificacao de produto.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "purposeType": {
                    "type": "integer"
                },
                "classificationCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "classificationType": {
                    "type": "integer"
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
        name="totvs_create_engineering_references",
        description="⚠️ ESCRITA — Cadastra produto a partir da engenharia padrão.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "references": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
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
    "totvs_search_consumption_sheet": "search_consumption_sheet",
    "totvs_search_engineering_services": "search_services",
    "totvs_get_engineering_operations": "get_operations",
    "totvs_search_engineering_applications": "search_applications",
    "totvs_search_engineering_default": "search_engineering_default",
    "totvs_get_engineering_configurations": "get_engineering_configurations",
    "totvs_create_engineering_references": "create_references_from_engineering",
}