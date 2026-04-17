"""
Person Tools
============
API Person v2 — /api/totvsmoda/person/v2/
Clientes PF/PJ, representantes, filiais, bônus, mensagens.
"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.person")
BASE = "/api/totvsmoda/person/v2"


def _search_body(args: dict[str, Any]) -> dict[str, Any]:
    flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order") and v is not None}
    body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
    if args.get("order"):
        body["order"] = args["order"]
    return body


class PersonTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_individuals(self, args: dict[str, Any]) -> Any:
        """POST /individuals/search — Dados de pessoa física."""
        return await self.client.post(f"{BASE}/individuals/search", _search_body(args))

    async def search_legal_entities(self, args: dict[str, Any]) -> Any:
        """POST /legal-entities/search — Dados de pessoa jurídica."""
        return await self.client.post(f"{BASE}/legal-entities/search", _search_body(args))

    async def get_branch(self, args: dict[str, Any]) -> Any:
        """GET /branches/{branchId} — Dados de empresa por código ou CNPJ."""
        branch_id = args["branchId"]
        return await self.client.get(f"{BASE}/branches/{branch_id}")

    async def get_branches_list(self, args: dict[str, Any]) -> Any:
        """GET /branchesList — Lista todas as empresas."""
        return await self.client.get(f"{BASE}/branchesList")

    async def search_representatives(self, args: dict[str, Any]) -> Any:
        """POST /representatives/search — Dados de representante."""
        return await self.client.post(f"{BASE}/representatives/search", _search_body(args))

    async def list_bonus_balance(self, args: dict[str, Any]) -> Any:
        """POST /list-balance-bonus — Saldo de bônus de cliente."""
        return await self.client.post(f"{BASE}/list-balance-bonus", _search_body(args))

    async def get_person_statistics(self, args: dict[str, Any]) -> Any:
        """GET /person-statistics — Estatísticas do cliente."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/person-statistics", params=params or None)

    async def get_classifications(self, args: dict[str, Any]) -> Any:
        """GET /classifications — Classificações de pessoa."""
        return await self.client.get(f"{BASE}/classifications")

    async def get_email_types(self, args: dict[str, Any]) -> Any:
        """GET /email-types — Tipos de e-mail disponíveis."""
        return await self.client.get(f"{BASE}/email-types")

    async def get_phone_types(self, args: dict[str, Any]) -> Any:
        """GET /phone-types — Tipos de telefone disponíveis."""
        return await self.client.get(f"{BASE}/phone-types")

    # ── WRITE ──────────────────────────────────────────────────────────────

    async def create_or_update_individual_customer(self, args: dict[str, Any]) -> Any:
        """POST /individual-customers — ⚠️ Criar ou alterar cliente PF."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/individual-customers", body)

    async def create_or_update_legal_customer(self, args: dict[str, Any]) -> Any:
        """POST /legal-customers — ⚠️ Criar ou alterar cliente PJ."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/legal-customers", body)

    async def consume_bonus(self, args: dict[str, Any]) -> Any:
        """POST /bonus-consume — ⚠️ Consumir bônus desconto de cliente."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/bonus-consume", body)

    async def create_message(self, args: dict[str, Any]) -> Any:
        """POST /messages — ⚠️ Incluir mensagem para pessoa."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/messages", body)
