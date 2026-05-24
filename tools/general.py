"""
General Tools
=============
API General v2 — /api/totvsmoda/general/v2/
Condições de pagamento, operações, devoluções, transações, contagens.
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._defaults import inject_branch_defaults
from tools._fields import apply_fields

logger = logging.getLogger("totvs-moda-mcp.general")
BASE = "/api/totvsmoda/general/v2"


def _pascal_params(args: dict[str, Any]) -> dict[str, Any]:
    special = {"customerCpfCnpjList": "CustomerCPFCNPJList"}
    params: dict[str, Any] = {}
    for key, value in args.items():
        if value is None or key in {"branchCode", "fields"}:
            continue
        params[special.get(key, key[:1].upper() + key[1:])] = value
    return params


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
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/payment-plan-simulate", body)

    async def search_devolutions(self, args: dict[str, Any]) -> Any:
        """GET /devolutions/search — Dados de devolução por estágio."""
        args = inject_branch_defaults(args)
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/devolutions/search", params=params or None)

    async def get_transactions(self, args: dict[str, Any]) -> Any:
        """GET /transactions — Dados de uma transação."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/transactions", params=params or None)

    async def get_classifications(self, args: dict[str, Any]) -> Any:
        """GET /classifications — Classificações disponíveis."""
        return await self.client.get(f"{BASE}/classifications")

    async def search_transactions(self, args: dict[str, Any]) -> Any:
        """GET /transactions/search - lista transacoes por filial, cliente, data e alteracao."""
        args = inject_branch_defaults(args)
        args = dict(args)
        if not args.get("branchCodeList") and args.get("branchCode") is not None:
            args["branchCodeList"] = [args["branchCode"]]
        if not args.get("branchCodeList"):
            raise ValueError("branchCode ou branchCodeList e obrigatorio.")
        result = await self.client.get(f"{BASE}/transactions/search", params=_pascal_params(args))
        return apply_fields(result, args)

    async def create_devolution(self, args: dict[str, Any]) -> Any:
        """POST /devolutions/create — ⚠️ Grava dados de devolução."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/devolutions/create", body)

    async def create_transaction(self, args: dict[str, Any]) -> Any:
        """POST /transactions — ⚠️ Inclui transação."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/transactions", body)

    async def create_product_count(self, args: dict[str, Any]) -> Any:
        """POST /product-counts — ⚠️ Criação de contagem com produtos."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product-counts", body)

    async def create_financial_compensation(self, args: dict[str, Any]) -> Any:
        """POST /financial-compensations - write financeiro."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/financial-compensations", body)

    async def add_product_count_additional_count(self, args: dict[str, Any]) -> Any:
        """POST /product-counts/additional-count - adiciona contagem complementar."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product-counts/additional-count", body)

    async def create_relationship_counts(self, args: dict[str, Any]) -> Any:
        """POST /relationship-counts - relaciona contagens a transacao."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/relationship-counts", body)

    async def create_transaction_classification_relationship(self, args: dict[str, Any]) -> Any:
        """POST /transaction-classification-relationship/create - vincula classificacoes a transacao."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/transaction-classification-relationship/create", body)
