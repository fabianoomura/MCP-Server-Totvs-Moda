"""
Material Request Tools
======================
API Material Request v2 - /api/totvsmoda/material-request/v2/
"""
from typing import Any

from totvs_client import TotvsClient
from tools._defaults import inject_branch_defaults
from tools._fields import apply_fields


BASE = "/api/totvsmoda/material-request/v2"


class MaterialRequestTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_material_requests(self, args: dict[str, Any]) -> Any:
        """POST /search - consulta requisicoes/solicitacoes de material."""
        args = inject_branch_defaults(args)
        top_level = {"filter", "expand", "order", "page", "pageSize", "fields"}
        filter_fields = {
            "change",
            "startRequestDate",
            "endRequestDate",
            "branchCodeList",
            "requestCodeList",
            "personList",
            "costCenterList",
            "productList",
            "buyerList",
            "purposeCodeList",
            "statusTypeList",
            "operationCodeList",
            "classifications",
        }

        flt = dict(args.get("filter") or {})
        for key, value in args.items():
            if key in filter_fields and value is not None:
                flt[key] = value

        if "branchCodeList" not in flt and args.get("branchCode") is not None:
            flt["branchCodeList"] = [args["branchCode"]]
        if "branchCodeList" not in flt:
            # inject_branch_defaults normally supplies this, but keep a direct
            # guard because the Swagger requires branchCodeList.
            raise ValueError("branchCodeList e obrigatorio para buscar requisicoes de material.")

        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        for key in ("expand", "order"):
            if args.get(key) is not None:
                body[key] = args[key]

        result = await self.client.post(f"{BASE}/search", body)
        return apply_fields(result, args)

    async def create_material_request(self, args: dict[str, Any]) -> Any:
        """POST /requests - cria uma solicitacao de material."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/requests", body)

    async def add_items(self, args: dict[str, Any]) -> Any:
        """POST /items - inclui itens em solicitacao existente."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/items", body)

    async def modify_header(self, args: dict[str, Any]) -> Any:
        """POST /headers/modify - altera capa da solicitacao."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/headers/modify", body)

    async def modify_items(self, args: dict[str, Any]) -> Any:
        """POST /items/modify - altera itens da solicitacao."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/items/modify", body)

    async def remove_items(self, args: dict[str, Any]) -> Any:
        """POST /items/remove - remove itens da solicitacao."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/items/remove", body)

    async def cancel_items(self, args: dict[str, Any]) -> Any:
        """POST /items/cancel - cancela quantidade de itens da solicitacao."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/items/cancel", body)

    async def approve(self, args: dict[str, Any]) -> Any:
        """POST /approve - aprova ou reprova solicitacao de material."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/approve", body)

    async def move_items(self, args: dict[str, Any]) -> Any:
        """POST /items/movement - movimenta/baixa itens da solicitacao."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/items/movement", body)


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_material_requests",
        description=(
            "Consulta requisicoes/solicitacoes de material. Use expand='items,classifications,observations'. Status: 0=Pendente, 1=Liberada, 2=Nao liberada, 3=Aprovada, 4=Atendida, 5=Nao atendida, 6=Cancelada."
        ),
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
                    },
                    "description": "Obrigatorio no Swagger; default vem do contexto quando omitido"
                },
                "change": {
                    "type": "object",
                    "description": "{startDate,endDate}"
                },
                "startRequestDate": {
                    "type": "string"
                },
                "endRequestDate": {
                    "type": "string"
                },
                "requestCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "personList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Pessoa responsavel"
                },
                "costCenterList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "productList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Produtos/materiais nos itens"
                },
                "buyerList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "purposeCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "statusTypeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "0=Pendente,1=Liberada,2=Nao liberada,3=Aprovada,4=Atendida,5=Nao atendida,6=Cancelada"
                },
                "operationCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "classificationTypeCode": {
                                "type": "integer"
                            },
                            "classificationCode": {
                                "type": "string"
                            }
                        }
                    }
                },
                "expand": {
                    "type": "string",
                    "description": "items,classifications,observations"
                },
                "order": {
                    "type": "string",
                    "description": "branchCode,requestDate,requestCode,maxChangeFilterDate. Use - para desc."
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
        name="totvs_create_material_request",
        description=(
            "⚠️ ESCRITA — Cria uma solicitacao de material no TOTVS. Use somente quando o usuario confirmar filial, finalidade, solicitante e itens."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Empresa. Campo Empresa do CMCFM006."
                },
                "requestDate": {
                    "type": "string",
                    "description": "Data de emissao da solicitacao, formato YYYY-MM-DD."
                },
                "purposeCode": {
                    "type": "integer",
                    "description": "Finalidade da solicitacao."
                },
                "requester": {
                    "type": "integer",
                    "description": "Solicitante."
                },
                "costCenter": {
                    "type": "integer",
                    "description": "Centro de custo da capa."
                },
                "bridgeCode": {
                    "type": "string",
                    "description": "Codigo de integracao externo."
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sequence": {
                                "type": "integer"
                            },
                            "productCode": {
                                "type": "integer"
                            },
                            "requestQuantity": {
                                "type": "number"
                            },
                            "costCenter": {
                                "type": "integer"
                            },
                            "expense": {
                                "type": "integer"
                            },
                            "cost": {
                                "type": "number"
                            }
                        },
                        "required": [
                            "sequence"
                        ]
                    }
                },
                "observations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "observation": {
                                "type": "string"
                            }
                        }
                    }
                }
            },
            "required": [
                "branchCode",
                "purposeCode",
                "requester"
            ]
        },
    ),
    types.Tool(
        name="totvs_add_material_request_items",
        description="⚠️ ESCRITA — Inclui itens em uma solicitacao de material existente.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "requestDate": {
                    "type": "string"
                },
                "requestCode": {
                    "type": "integer"
                },
                "integrationCode": {
                    "type": "string"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sequence": {
                                "type": "integer"
                            },
                            "productCode": {
                                "type": "integer"
                            },
                            "requestQuantity": {
                                "type": "number"
                            },
                            "costCenter": {
                                "type": "integer"
                            },
                            "expense": {
                                "type": "integer"
                            },
                            "cost": {
                                "type": "number"
                            }
                        },
                        "required": [
                            "sequence"
                        ]
                    }
                }
            }
        },
    ),
    types.Tool(
        name="totvs_modify_material_request_header",
        description="⚠️ ESCRITA — Altera a capa de uma solicitacao de material.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "requestDate": {
                    "type": "string"
                },
                "requestCode": {
                    "type": "integer"
                },
                "integrationCode": {
                    "type": "string"
                },
                "purposeCode": {
                    "type": "integer"
                },
                "costCenter": {
                    "type": "integer"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_modify_material_request_items",
        description="⚠️ ESCRITA — Altera itens de uma solicitacao de material existente.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "requestDate": {
                    "type": "string"
                },
                "requestCode": {
                    "type": "integer"
                },
                "integrationCode": {
                    "type": "string"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sequence": {
                                "type": "integer"
                            },
                            "productCode": {
                                "type": "integer"
                            },
                            "requestQuantity": {
                                "type": "number"
                            },
                            "costCenter": {
                                "type": "integer"
                            },
                            "expense": {
                                "type": "integer"
                            },
                            "cost": {
                                "type": "number"
                            }
                        },
                        "required": [
                            "sequence"
                        ]
                    }
                }
            }
        },
    ),
    types.Tool(
        name="totvs_remove_material_request_items",
        description="⚠️ ESCRITA/DESTRUTIVA — Remove itens de uma solicitacao de material existente.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "requestDate": {
                    "type": "string"
                },
                "requestCode": {
                    "type": "integer"
                },
                "integrationCode": {
                    "type": "string"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sequence": {
                                "type": "integer"
                            }
                        },
                        "required": [
                            "sequence"
                        ]
                    }
                }
            }
        },
    ),
    types.Tool(
        name="totvs_cancel_material_request_items",
        description="⚠️ ESCRITA/DESTRUTIVA — Cancela quantidade de itens de uma solicitacao de material.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "requestDate": {
                    "type": "string"
                },
                "requestCode": {
                    "type": "integer"
                },
                "integrationCode": {
                    "type": "string"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sequence": {
                                "type": "integer"
                            },
                            "cancelQuantity": {
                                "type": "number"
                            },
                            "reason": {
                                "type": "integer"
                            },
                            "descriptions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "description": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        },
                        "required": [
                            "sequence"
                        ]
                    }
                }
            }
        },
    ),
    types.Tool(
        name="totvs_approve_material_request",
        description="⚠️ ESCRITA — Aprova ou reprova solicitacao de material.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "requestDate": {
                    "type": "string"
                },
                "requestCode": {
                    "type": "integer"
                },
                "approverUser": {
                    "type": "integer"
                },
                "approved": {
                    "type": "boolean"
                },
                "reportDescription": {
                    "type": "string"
                },
                "reasonCode": {
                    "type": "integer"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_move_material_request_items",
        description="⚠️ ESCRITA/DESTRUTIVA — Movimenta/baixa itens de solicitacao de material. Pode afetar estoque.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "requestDate": {
                    "type": "string"
                },
                "requestCode": {
                    "type": "integer"
                },
                "integrationCode": {
                    "type": "string"
                },
                "operationCode": {
                    "type": "integer"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sequence": {
                                "type": "integer"
                            },
                            "movementQuantity": {
                                "type": "number"
                            },
                            "batchItems": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                }
                            }
                        },
                        "required": [
                            "sequence",
                            "movementQuantity"
                        ]
                    }
                },
                "descriptions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string"
                            }
                        }
                    }
                }
            },
            "required": [
                "operationCode",
                "items"
            ]
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_material_requests": "search_material_requests",
    "totvs_create_material_request": "create_material_request",
    "totvs_add_material_request_items": "add_items",
    "totvs_modify_material_request_header": "modify_header",
    "totvs_modify_material_request_items": "modify_items",
    "totvs_remove_material_request_items": "remove_items",
    "totvs_cancel_material_request_items": "cancel_items",
    "totvs_approve_material_request": "approve",
    "totvs_move_material_request_items": "move_items",
}