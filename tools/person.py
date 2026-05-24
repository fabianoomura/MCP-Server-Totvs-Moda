"""
Person Tools
============
API Person v2 — /api/totvsmoda/person/v2/
Clientes PF/PJ, representantes, filiais, bônus, mensagens.
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults

logger = logging.getLogger("totvs-moda-mcp.person")
BASE = "/api/totvsmoda/person/v2"


def _pascal_params(args: dict[str, Any]) -> dict[str, Any]:
    return {k[:1].upper() + k[1:]: v for k, v in args.items() if v is not None}


def _search_body(args: dict[str, Any]) -> dict[str, Any]:
    if isinstance(args.get("filter"), dict):
        flt = {k: v for k, v in args["filter"].items() if v is not None}
    else:
        flt = {
            k: v
            for k, v in args.items()
            if k not in ("filter", "option", "expand", "page", "pageSize", "order", "fields") and v is not None
        }
    body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
    if args.get("option") is not None:
        body["option"] = args["option"]
    if args.get("expand"):
        body["expand"] = args["expand"]
    if args.get("order"):
        body["order"] = args["order"]
    return body


class PersonTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_individuals(self, args: dict[str, Any]) -> Any:
        """POST /individuals/search — Dados de pessoa física."""
        result = await self.client.post(f"{BASE}/individuals/search", _search_body(args))
        return apply_fields(result, args)

    async def search_legal_entities(self, args: dict[str, Any]) -> Any:
        """POST /legal-entities/search — Dados de pessoa jurídica."""
        result = await self.client.post(f"{BASE}/legal-entities/search", _search_body(args))
        return apply_fields(result, args)

    async def get_branch(self, args: dict[str, Any]) -> Any:
        """GET /branches/{branchId} — Dados de empresa por código ou CNPJ."""
        branch_id = args["branchId"]
        return await self.client.get(f"{BASE}/branches/{branch_id}")

    async def get_branches_list(self, args: dict[str, Any]) -> Any:
        """GET /branchesList — Lista todas as empresas."""
        return await self.client.get(f"{BASE}/branchesList")

    async def search_representatives(self, args: dict[str, Any]) -> Any:
        """POST /representatives/search — Dados de representante."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE}/representatives/search", _search_body(args))
        return apply_fields(result, args)

    async def list_bonus_balance(self, args: dict[str, Any]) -> Any:
        """POST /list-balance-bonus — Saldo de bônus de cliente."""
        return await self.client.post(f"{BASE}/list-balance-bonus", _search_body(args))

    async def get_person_statistics(self, args: dict[str, Any]) -> Any:
        """GET /person-statistics — Estatísticas do cliente."""
        args = inject_branch_defaults(args)
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/person-statistics", params=params or None)

    async def get_classifications(self, args: dict[str, Any]) -> Any:
        """GET /classifications — Classificações de pessoa."""
        return await self.client.get(f"{BASE}/classifications")

    async def remove_classification_relationship(self, args: dict[str, Any]) -> Any:
        """POST /classification-relationship/remove - remove vinculo de classificacao de pessoa."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/classification-relationship/remove", body)

    async def get_email_types(self, args: dict[str, Any]) -> Any:
        """GET /email-types — Tipos de e-mail disponíveis."""
        return await self.client.get(f"{BASE}/email-types", params=_pascal_params(args) or None)

    async def get_phone_types(self, args: dict[str, Any]) -> Any:
        """GET /phone-types — Tipos de telefone disponíveis."""
        return await self.client.get(f"{BASE}/phone-types", params=_pascal_params(args) or None)

    async def get_contact_types(self, args: dict[str, Any]) -> Any:
        """GET /contact-types - Tipos de contato disponiveis."""
        return await self.client.get(f"{BASE}/contact-types", params=_pascal_params(args) or None)

    async def search_reception_sale(self, args: dict[str, Any]) -> Any:
        """GET /reception-sale/search - Recepcao de venda por data/tipo."""
        result = await self.client.get(f"{BASE}/reception-sale/search", params=_pascal_params(args) or None)
        return apply_fields(result, args)

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

    async def relate_customer_representatives(self, args: dict[str, Any]) -> Any:
        """POST /customer-representatives - Relaciona clientes a representante."""
        if not (args.get("representativeCode") or args.get("representativeCpfCnpj")):
            raise ValueError("Informe representativeCode OU representativeCpfCnpj")
        if not (args.get("customerCodeList") or args.get("customerCpfCnpjList")):
            raise ValueError("Informe customerCodeList OU customerCpfCnpjList")
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/customer-representatives", body)

    async def change_message(self, args: dict[str, Any]) -> Any:
        """PUT /messages/change - Altera mensagem de pessoa."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.put(f"{BASE}/messages/change", body)
