"""
Data Package Tools
==================
API Data Package v2 — /api/totvsmoda/data-package/v2/
Gerenciamento de pacotes de dados (importação/exportação).
"""
import logging
from typing import Any
from totvs_client import TotvsClient

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
        return await self.client.get(f"{BASE}/input-packages", params=params or None)

    async def get_package(self, args: dict[str, Any]) -> Any:
        """GET /packages/{packageId} — Dados de um pacote de dados."""
        return await self.client.get(f"{BASE}/packages/{args['packageId']}")

    async def get_package_content(self, args: dict[str, Any]) -> Any:
        """GET /content-packages/{packageId} — Conteúdo de um pacote de dados."""
        return await self.client.get(f"{BASE}/content-packages/{args['packageId']}")

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
        return await self.client.get(f"{BASE}/output-packages", params=params)

    async def receive_output_package(self, args: dict[str, Any]) -> Any:
        """POST /output-packages/receive — ⚠️ Marca pacote de exportação como recebido."""
        return await self.client.post(f"{BASE}/output-packages/receive", {"packageId": args["packageId"]})

    async def reactivate_package(self, args: dict[str, Any]) -> Any:
        """POST /packages/reactivate — ⚠️ Reativa pacote rejeitado para 'Em andamento'."""
        return await self.client.post(f"{BASE}/packages/reactivate", {"packageId": args["packageId"]})
