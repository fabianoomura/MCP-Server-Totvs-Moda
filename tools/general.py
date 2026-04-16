"""
General Tools
=============
API General v2 — /api/totvsmoda/general/v2/
Condições de pagamento, operações, devoluções, transações, contagens.
"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.general")
BASE = "/api/totvsmoda/general/v2"


class GeneralTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def get_payment_conditions(self, args: dict[str, Any]) -> Any:
        """GET /payment-conditions — Condições de pagamento disponíveis."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/payment-conditions", params=params or None)

    async def get_operations(self, args: dict[str, Any]) -> Any:
        """GET /operations — Operações disponíveis."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/operations", params=params or None)

    async def get_payment_plans(self, args: dict[str, Any]) -> Any:
        """GET /payment-plans — Planos de pagamento ativos."""
        return await self.client.get(f"{BASE}/payment-plans")

    async def simulate_payment_plan(self, args: dict[str, Any]) -> Any:
        """POST /payment-plan-simulate — Simula cálculo de plano de pagamento."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/payment-plan-simulate", body)

    async def search_devolutions(self, args: dict[str, Any]) -> Any:
        """GET /devolutions/search — Dados de devolução por estágio."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/devolutions/search", params=params or None)

    async def get_transactions(self, args: dict[str, Any]) -> Any:
        """GET /transactions — Dados de uma transação."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/transactions", params=params or None)

    async def get_classifications(self, args: dict[str, Any]) -> Any:
        """GET /classifications — Classificações disponíveis."""
        return await self.client.get(f"{BASE}/classifications")

    async def create_devolution(self, args: dict[str, Any]) -> Any:
        """POST /devolutions/create — ⚠️ Grava dados de devolução."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/devolutions/create", body)

    async def create_transaction(self, args: dict[str, Any]) -> Any:
        """POST /transactions — ⚠️ Inclui transação."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/transactions", body)

    async def create_product_count(self, args: dict[str, Any]) -> Any:
        """POST /product-counts — ⚠️ Criação de contagem com produtos."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product-counts", body)
