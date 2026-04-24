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
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{self.BASE}/orders/search", body)
        return apply_fields(result, args)

    async def get_pending_material_consumption(self, args: dict[str, Any]) -> Any:
        """POST /pending-material-consumption — Fichas de consumo pendentes."""
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        return await self.client.post(f"{self.BASE}/pending-material-consumption", body)

    async def create_material_movement(self, args: dict[str, Any]) -> Any:
        """POST /materials/movement — ⚠️ Movimentação de matéria prima."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{self.BASE}/materials/movement", body)
