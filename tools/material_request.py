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
