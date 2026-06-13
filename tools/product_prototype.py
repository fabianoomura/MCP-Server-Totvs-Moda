"""
Product Prototype Tools
=======================
API Product Prototype v2 - /api/totvsmoda/product-prototype/v2/
"""
from typing import Any

from totvs_client import TotvsClient
from tools._fields import apply_fields


BASE = "/api/totvsmoda/product-prototype/v2"


class ProductPrototypeTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_prototypes(self, args: dict[str, Any]) -> Any:
        """POST /prototypes/search - consulta prototipos."""
        if not args.get("prototypeCodeList"):
            raise ValueError("prototypeCodeList e obrigatorio para buscar prototipos na API TOTVS.")
        body: dict[str, Any] = {
            k: v for k, v in args.items()
            if k not in ("fields",) and v is not None
        }
        body.setdefault("page", 1)
        body.setdefault("pageSize", 100)
        result = await self.client.post(f"{BASE}/prototypes/search", body)
        return apply_fields(result, args)

    async def create_prototype(self, args: dict[str, Any]) -> Any:
        """POST /prototypes - cria prototipo."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/prototypes", body)

    async def update_prototype(self, args: dict[str, Any]) -> Any:
        """POST /prototypes/update - altera prototipo."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/prototypes/update", body)


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_product_prototypes",
        description=(
            "Consulta prototipos de produto por lista de codigos. A API exige prototypeCodeList. Use expand='Destiny' para dados de destino."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "prototypeCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Obrigatorio na API TOTVS; maximo 100 itens."
                },
                "expand": {
                    "type": "string",
                    "description": "Destiny"
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximo 100 no Swagger"
                },
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "prototypeCodeList"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_product_prototype",
        description=(
            "⚠️ ESCRITA — Cria prototipo de produto. Aceita blocos ricos do Swagger como gridQuantities, services, rawMaterials, classifications, images e compositions."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "code": {
                    "type": "integer",
                    "description": "Se omitido, a TOTVS pode gerar sequencia automatica."
                },
                "prototypeDescription": {
                    "type": "string"
                },
                "customerCode": {
                    "type": "integer"
                },
                "customerCpfCnpj": {
                    "type": "string"
                },
                "estimatedStart": {
                    "type": "string"
                },
                "estimatedDeliveryDate": {
                    "type": "string"
                },
                "baseGroupCode": {
                    "type": "integer"
                },
                "gridCode": {
                    "type": [
                        "integer",
                        "string"
                    ]
                },
                "prototypeVersion": {
                    "type": "integer"
                },
                "netWeight": {
                    "type": "number"
                },
                "grossWeight": {
                    "type": "number"
                },
                "instructions": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "gridQuantities": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "services": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "measureTables": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "operationalSequences": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "images": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "rawMaterials": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "rawMaterialsGrid": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "additionalProductFields": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "compositions": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "branchCode"
            ]
        },
    ),
    types.Tool(
        name="totvs_update_product_prototype",
        description="⚠️ ESCRITA — Altera dados de prototipo de produto. Aceita o mesmo contrato rico da criacao.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "code": {
                    "type": "integer"
                },
                "prototypeDescription": {
                    "type": "string"
                },
                "customerCode": {
                    "type": "integer"
                },
                "customerCpfCnpj": {
                    "type": "string"
                },
                "estimatedStart": {
                    "type": "string"
                },
                "estimatedDeliveryDate": {
                    "type": "string"
                },
                "baseGroupCode": {
                    "type": "integer"
                },
                "gridCode": {
                    "type": [
                        "integer",
                        "string"
                    ]
                },
                "prototypeVersion": {
                    "type": "integer"
                },
                "netWeight": {
                    "type": "number"
                },
                "grossWeight": {
                    "type": "number"
                },
                "instructions": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "gridQuantities": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "services": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "measureTables": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "operationalSequences": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "images": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "rawMaterials": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "rawMaterialsGrid": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "additionalProductFields": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "compositions": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "branchCode"
            ]
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_product_prototypes": "search_prototypes",
    "totvs_create_product_prototype": "create_prototype",
    "totvs_update_product_prototype": "update_prototype",
}