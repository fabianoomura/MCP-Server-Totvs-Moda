"""
Data Package Tools
==================
API Data Package v2 — /api/totvsmoda/data-package/v2/
Gerenciamento de pacotes de dados (importação/exportação).
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields

logger = logging.getLogger("totvs-moda-mcp.data-package")
BASE = "/api/totvsmoda/data-package/v2"


class DataPackageTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def create_input_package(self, args: dict[str, Any]) -> Any:
        """POST /input-packages — ⚠️ Inclui pacote de dados para importação."""
        body: dict[str, Any] = {
            "modelCode": args["modelCode"],
            "source": args["source"],
            "target": args["target"],
            "movementDate": args["movementDate"],
            "content": args["content"],
        }
        for field in ("id", "name", "priority"):
            if args.get(field) is not None:
                body[field] = args[field]
        return await self.client.post(f"{BASE}/input-packages", body)

    async def list_input_packages(self, args: dict[str, Any]) -> Any:
        """GET /input-packages — Lista pacotes de importação de dados."""
        params: dict[str, Any] = {}
        for field in (
            "Target", "Status", "ModelCode", "ModelCodeList",
            "Source", "InitialInsertDate", "FinalInsertDate",
            "InitialMovementDate", "FinalMovementDate",
            "Page", "PageSize", "Order",
        ):
            if args.get(field) is not None:
                params[field] = args[field]
        result = await self.client.get(f"{BASE}/input-packages", params=params or None)
        return apply_fields(result, args)

    async def get_package(self, args: dict[str, Any]) -> Any:
        """GET /packages/{packageId} — Dados de um pacote de dados."""
        result = await self.client.get(f"{BASE}/packages/{args['packageId']}")
        return apply_fields(result, args)

    async def get_package_content(self, args: dict[str, Any]) -> Any:
        """GET /content-packages/{packageId} — Conteúdo de um pacote de dados."""
        result = await self.client.get(f"{BASE}/content-packages/{args['packageId']}")
        return apply_fields(result, args)

    async def list_output_packages(self, args: dict[str, Any]) -> Any:
        """GET /output-packages — Lista pacotes de exportação de dados (Target obrigatório)."""
        params: dict[str, Any] = {"Target": args["target"]}
        for field in (
            "ModelCode", "ModelCodeList", "Source",
            "InitialInsertDate", "FinalInsertDate",
            "InitialMovementDate", "FinalMovementDate",
            "Page", "PageSize", "Order",
        ):
            if args.get(field) is not None:
                params[field] = args[field]
        result = await self.client.get(f"{BASE}/output-packages", params=params)
        return apply_fields(result, args)

    async def receive_output_package(self, args: dict[str, Any]) -> Any:
        """POST /output-packages/receive — ⚠️ Marca pacote de exportação como recebido."""
        return await self.client.post(f"{BASE}/output-packages/receive", {"packageId": args["packageId"]})

    async def reactivate_package(self, args: dict[str, Any]) -> Any:
        """POST /packages/reactivate — ⚠️ Reativa pacote rejeitado para 'Em andamento'."""
        return await self.client.post(f"{BASE}/packages/reactivate", {"packageId": args["packageId"]})


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_list_input_packages",
        description=(
            "Lista pacotes de importação de dados (data-package). Filtra por destinatário, status, modelo e período."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "Target": {
                    "type": "string",
                    "description": "Identificador do destinatário"
                },
                "Status": {
                    "type": "string",
                    "description": "Status: Active, Rejected, Finished, RestrictionFinished, Canceled"
                },
                "ModelCode": {
                    "type": "integer",
                    "description": "Código do modelo de pacote"
                },
                "ModelCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Lista de códigos de modelo"
                },
                "Source": {
                    "type": "string",
                    "description": "Identificador da origem"
                },
                "InitialInsertDate": {
                    "type": "string",
                    "description": "Data inicial de inclusão (ISO 8601)"
                },
                "FinalInsertDate": {
                    "type": "string",
                    "description": "Data final de inclusão"
                },
                "InitialMovementDate": {
                    "type": "string",
                    "description": "Data inicial de movimento"
                },
                "FinalMovementDate": {
                    "type": "string",
                    "description": "Data final de movimento"
                },
                "Page": {
                    "type": "integer",
                    "default": 1
                },
                "PageSize": {
                    "type": "integer",
                    "default": 1000
                },
                "Order": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_package",
        description="Retorna informações de um pacote de dados pelo ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "packageId": {
                    "type": "string",
                    "description": "Identificador único do pacote"
                }
            },
            "required": [
                "packageId"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_package_content",
        description="Retorna o conteúdo (Base64) de um pacote de dados pelo ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "packageId": {
                    "type": "string",
                    "description": "Identificador único do pacote"
                }
            },
            "required": [
                "packageId"
            ]
        },
    ),
    types.Tool(
        name="totvs_list_output_packages",
        description="Lista pacotes de exportação de dados. Requer identificador do destinatário (target).",
        inputSchema={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Identificador do destinatário (obrigatório)"
                },
                "ModelCode": {
                    "type": "integer",
                    "description": "Código do modelo de pacote"
                },
                "ModelCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "Source": {
                    "type": "string",
                    "description": "Identificador da origem"
                },
                "InitialInsertDate": {
                    "type": "string",
                    "description": "Data inicial de inclusão (ISO 8601)"
                },
                "FinalInsertDate": {
                    "type": "string",
                    "description": "Data final de inclusão"
                },
                "InitialMovementDate": {
                    "type": "string",
                    "description": "Data inicial de movimento"
                },
                "FinalMovementDate": {
                    "type": "string",
                    "description": "Data final de movimento"
                },
                "Page": {
                    "type": "integer",
                    "default": 1
                },
                "PageSize": {
                    "type": "integer",
                    "default": 1000
                }
            },
            "required": [
                "target"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_input_package",
        description="⚠️ ESCRITA — Inclui pacote de dados para importação. O conteúdo deve estar em Base64.",
        inputSchema={
            "type": "object",
            "properties": {
                "modelCode": {
                    "type": "integer",
                    "description": "Código do modelo de pacote"
                },
                "source": {
                    "type": "string",
                    "description": "Identificador da origem"
                },
                "target": {
                    "type": "string",
                    "description": "Identificador do destinatário"
                },
                "movementDate": {
                    "type": "string",
                    "description": "Data de movimento (ISO 8601)"
                },
                "content": {
                    "type": "string",
                    "description": "Conteúdo do pacote em Base64"
                },
                "id": {
                    "type": "string",
                    "description": "ID único do pacote (gerado automaticamente se omitido)"
                },
                "name": {
                    "type": "string",
                    "description": "Descrição adicional"
                },
                "priority": {
                    "type": "integer",
                    "description": "Prioridade (menor = mais prioritário)"
                }
            },
            "required": [
                "modelCode",
                "source",
                "target",
                "movementDate",
                "content"
            ]
        },
    ),
    types.Tool(
        name="totvs_receive_output_package",
        description="⚠️ ESCRITA — Marca pacote de exportação como recebido.",
        inputSchema={
            "type": "object",
            "properties": {
                "packageId": {
                    "type": "string",
                    "description": "ID do pacote"
                }
            },
            "required": [
                "packageId"
            ]
        },
    ),
    types.Tool(
        name="totvs_reactivate_package",
        description="⚠️ ESCRITA — Reativa pacote rejeitado, mudando situação para 'Em andamento'.",
        inputSchema={
            "type": "object",
            "properties": {
                "packageId": {
                    "type": "string",
                    "description": "ID do pacote rejeitado"
                }
            },
            "required": [
                "packageId"
            ]
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_list_input_packages": "list_input_packages",
    "totvs_get_package": "get_package",
    "totvs_get_package_content": "get_package_content",
    "totvs_list_output_packages": "list_output_packages",
    "totvs_create_input_package": "create_input_package",
    "totvs_receive_output_package": "receive_output_package",
    "totvs_reactivate_package": "reactivate_package",
}