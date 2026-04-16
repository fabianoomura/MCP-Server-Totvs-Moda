"""Voucher Tools — /api/totvsmoda/voucher/v2/"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.voucher")
BASE = "/api/totvsmoda/voucher/v2"


class VoucherTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_voucher(self, args: dict[str, Any]) -> Any:
        """GET /search — Consulta voucher."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/search", params=params or None)

    async def create_voucher(self, args: dict[str, Any]) -> Any:
        """POST /create — ⚠️ Inclui voucher."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/create", body)

    async def update_voucher(self, args: dict[str, Any]) -> Any:
        """POST /update — ⚠️ Altera voucher."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/update", body)

    async def create_customer_vouchers(self, args: dict[str, Any]) -> Any:
        """POST /customer/create — ⚠️ Cria vouchers para lista de clientes."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/customer/create", body)


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
        """GET /global-parameter — Parâmetros corporativos."""
        return await self.client.get(f"{self.BASE}/global-parameter")

    async def get_branch_parameters(self, args: dict[str, Any]) -> Any:
        """GET /branch-parameter — Parâmetros por empresa."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{self.BASE}/branch-parameter", params=params or None)


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
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{self.BASE}/orders/search", body)

    async def get_pending_material_consumption(self, args: dict[str, Any]) -> Any:
        """POST /pending-material-consumption — Fichas de consumo pendentes."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{self.BASE}/pending-material-consumption", body)

    async def create_material_movement(self, args: dict[str, Any]) -> Any:
        """POST /materials/movement — ⚠️ Movimentação de matéria prima."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{self.BASE}/materials/movement", body)
