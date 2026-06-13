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
import response_cache as cache

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

    def _invalidate_after_write(self) -> None:
        for prefix in (
            "person_pf",
            "person_pj",
            "customer360",
            "dashboard",
            "new_customers_today",
        ):
            cache.invalidate(prefix)

    async def search_individuals(self, args: dict[str, Any]) -> Any:
        """POST /individuals/search — Dados de pessoa física."""
        body = _search_body(args)
        cached = cache.get("person_pf", body, cache.CATALOG)
        if cached is not None:
            return apply_fields(cached, args)
        result = await self.client.post(f"{BASE}/individuals/search", body)
        cache.put("person_pf", body, result)
        return apply_fields(result, args)

    async def search_legal_entities(self, args: dict[str, Any]) -> Any:
        """POST /legal-entities/search — Dados de pessoa jurídica."""
        body = _search_body(args)
        cached = cache.get("person_pj", body, cache.CATALOG)
        if cached is not None:
            return apply_fields(cached, args)
        result = await self.client.post(f"{BASE}/legal-entities/search", body)
        cache.put("person_pj", body, result)
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
        result = await self.client.post(f"{BASE}/classification-relationship/remove", body)
        self._invalidate_after_write()
        return result

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
        result = await self.client.post(f"{BASE}/individual-customers", body)
        self._invalidate_after_write()
        return result

    async def create_or_update_legal_customer(self, args: dict[str, Any]) -> Any:
        """POST /legal-customers — ⚠️ Criar ou alterar cliente PJ."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/legal-customers", body)
        self._invalidate_after_write()
        return result

    async def consume_bonus(self, args: dict[str, Any]) -> Any:
        """POST /bonus-consume — ⚠️ Consumir bônus desconto de cliente."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/bonus-consume", body)
        self._invalidate_after_write()
        return result

    async def create_message(self, args: dict[str, Any]) -> Any:
        """POST /messages — ⚠️ Incluir mensagem para pessoa."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/messages", body)
        self._invalidate_after_write()
        return result

    async def relate_customer_representatives(self, args: dict[str, Any]) -> Any:
        """POST /customer-representatives - Relaciona clientes a representante."""
        if not (args.get("representativeCode") or args.get("representativeCpfCnpj")):
            raise ValueError("Informe representativeCode OU representativeCpfCnpj")
        if not (args.get("customerCodeList") or args.get("customerCpfCnpjList")):
            raise ValueError("Informe customerCodeList OU customerCpfCnpjList")
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/customer-representatives", body)
        self._invalidate_after_write()
        return result

    async def change_message(self, args: dict[str, Any]) -> Any:
        """PUT /messages/change - Altera mensagem de pessoa."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.put(f"{BASE}/messages/change", body)
        self._invalidate_after_write()
        return result


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

WRITE_TOOL_ANNOTATIONS: dict[str, bool] = {
    "destructiveHint": True,
    "idempotentHint": False,
    "readOnlyHint": False,
    "openWorldHint": True,
}

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_individual_customers",
        description=(
            "Busca pessoas físicas/clientes PF por CPF, código, telefone, aniversário, classificações e flags funcionais. Use expand apenas quando precisar dados ricos."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "object",
                    "description": "IndividualFilterModel oficial; se informado, substitui os filtros soltos."
                },
                "change": {
                    "type": "object",
                    "description": "PersonChangeFilterModel: startDate,endDate,inClassification,inAddress,inPhone,inObservation,inPerson,inCustomer,inSupplier,inRepresentative,inPurchasingGuide,inShippingCompany,inReference,inContact,inStatistic,inCustomerObservation,inEmployee,inPreference,classificationTypeCodeList"
                },
                "startPersonCode": {
                    "type": "integer"
                },
                "endPersonCode": {
                    "type": "integer"
                },
                "personCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "customerCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Alias legado para personCodeList em alguns fluxos."
                },
                "cpfList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "name": {
                    "type": "string"
                },
                "phoneNumber": {
                    "type": "string"
                },
                "birthdayDayList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "birthdayMonth": {
                    "type": "string"
                },
                "personIsInactive": {
                    "type": "boolean"
                },
                "isCustomer": {
                    "type": "boolean"
                },
                "isSupplier": {
                    "type": "boolean"
                },
                "isRepresentative": {
                    "type": "boolean"
                },
                "isPurchasingGuide": {
                    "type": "boolean"
                },
                "isShippingCompany": {
                    "type": "boolean"
                },
                "isEmployee": {
                    "type": "boolean"
                },
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "integer"
                            },
                            "codeList": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            }
                        }
                    }
                },
                "option": {
                    "type": "object",
                    "description": "PersonOptionModel: classificationTypeCodeList, additionalFieldCodeList, branchStaticDataList, branchRepresentativeParameterList, QuantityOcurrenceCustomerObservation"
                },
                "expand": {
                    "type": "string",
                    "description": "phones,addresses,emails,classifications,additionalFields,references,observations,relateds,shippingCompany,statistics,representatives,customerObservations,familiars"
                },
                "order": {
                    "type": "string",
                    "description": "personCode,maxChangeFilterDate. Use - para desc."
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 500,
                    "description": "Máximo 500 no Swagger"
                },
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."
                }
            }
        },
    ),
    types.Tool(
        name="totvs_search_legal_customers",
        description=(
            "Busca pessoas jurídicas/clientes PJ por CNPJ, código, classificações e flags funcionais. Use expand apenas quando precisar dados ricos."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "object",
                    "description": "LegalEntityFilterModel oficial; se informado, substitui os filtros soltos."
                },
                "change": {
                    "type": "object",
                    "description": "PersonChangeFilterModel: startDate,endDate,inClassification,inAddress,inPhone,inObservation,inPerson,inCustomer,inSupplier,inRepresentative,inPurchasingGuide,inShippingCompany,inReference,inContact,inStatistic,inCustomerObservation,inEmployee,inPreference,classificationTypeCodeList"
                },
                "startPersonCode": {
                    "type": "integer"
                },
                "endPersonCode": {
                    "type": "integer"
                },
                "personCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "customerCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Alias legado para personCodeList em alguns fluxos."
                },
                "cnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "corporateName": {
                    "type": "string"
                },
                "isCustomer": {
                    "type": "boolean"
                },
                "isSupplier": {
                    "type": "boolean"
                },
                "isRepresentative": {
                    "type": "boolean"
                },
                "isPurchasingGuide": {
                    "type": "boolean"
                },
                "isShippingCompany": {
                    "type": "boolean"
                },
                "isEmployee": {
                    "type": "boolean"
                },
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "integer"
                            },
                            "codeList": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            }
                        }
                    }
                },
                "option": {
                    "type": "object",
                    "description": "PersonOptionModel: classificationTypeCodeList, additionalFieldCodeList, branchStaticDataList, branchRepresentativeParameterList, QuantityOcurrenceCustomerObservation"
                },
                "expand": {
                    "type": "string",
                    "description": "phones,addresses,emails,classifications,additionalFields,references,observations,relateds,partners,shippingCompany,contacts,statistics,paymentMethods,preferences,socialNetworks,representatives,customerObservations"
                },
                "order": {
                    "type": "string",
                    "description": "personCode,maxChangeFilterDate. Use - para desc."
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 500,
                    "description": "Máximo 500 no Swagger"
                },
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_customer_bonus_balance",
        description="Saldo de bônus/desconto de um cliente.",
        inputSchema={
            "type": "object",
            "properties": {
                "customerCode": {
                    "type": "integer"
                },
                "cpfCnpj": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_person_statistics",
        description=(
            "Estatísticas de UM cliente específico: total comprado, ticket médio, frequência. NÃO use para 'vendas de hoje', 'o que vendi', ranking, resumo geral ou clientes novos; nesses casos use totvs_sales_today_summary, totvs_daily_dashboard ou totvs_new_customers_today."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customerCode": {
                    "type": "integer"
                },
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                }
            },
            "required": [
                "customerCode"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_or_update_individual_customer",
        description="⚠️ ESCRITA — Cria ou atualiza cliente PF no TOTVS.",
        inputSchema={
            "type": "object",
            "properties": {
                "cpf": {
                    "type": "string"
                },
                "name": {
                    "type": "string"
                },
                "email": {
                    "type": "string"
                },
                "phone": {
                    "type": "string"
                },
                "birthDate": {
                    "type": "string"
                },
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                }
            },
            "required": [
                "cpf",
                "name"
            ]
        },
        annotations=WRITE_TOOL_ANNOTATIONS,
    ),
    types.Tool(
        name="totvs_create_or_update_legal_customer",
        description="⚠️ Cria ou atualiza cliente PJ no TOTVS.",
        inputSchema={
            "type": "object",
            "properties": {
                "cnpj": {
                    "type": "string"
                },
                "corporateName": {
                    "type": "string"
                },
                "fantasyName": {
                    "type": "string"
                },
                "email": {
                    "type": "string"
                },
                "branchCode": {
                    "type": "integer"
                }
            },
            "required": [
                "cnpj",
                "corporateName"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_branches_list",
        description="Lista todas as filiais/empresas cadastradas.",
        inputSchema={
            "type": "object",
            "properties": {}
        },
    ),
    types.Tool(
        name="totvs_search_representatives",
        description="Busca representantes comerciais. Use fields para reduzir tokens.",
        inputSchema={
            "type": "object",
            "properties": {
                "representativeCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "cpfCnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "name": {
                    "type": "string"
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100
                },
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_person_classifications",
        description="Classificações de pessoa disponíveis.",
        inputSchema={
            "type": "object",
            "properties": {}
        },
    ),
    types.Tool(
        name="totvs_remove_person_classification_relationship",
        description=(
            "⚠️ DESTRUTIVO — Remove relacionamento de classificação com pessoa. Use somente após confirmação explícita."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "personCode": {
                    "type": "integer"
                },
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "personCode"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_email_types",
        description="Tipos de e-mail disponíveis para cadastro de pessoa.",
        inputSchema={
            "type": "object",
            "properties": {}
        },
    ),
    types.Tool(
        name="totvs_get_phone_types",
        description="Tipos de telefone disponíveis para cadastro de pessoa.",
        inputSchema={
            "type": "object",
            "properties": {}
        },
    ),
    types.Tool(
        name="totvs_get_contact_types",
        description="Tipos de contato disponiveis para cadastro de pessoa.",
        inputSchema={
            "type": "object",
            "properties": {
                "startChangeDate": {
                    "type": "string"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "typeCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "order": {
                    "type": "string",
                    "description": "code,maxChangeFilterDate. Use - para desc."
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 1000
                }
            }
        },
    ),
    types.Tool(
        name="totvs_search_reception_sale",
        description="Consulta recepcao de venda por data de movimento/cadastro e tipo L=Loja, P=Pedido.",
        inputSchema={
            "type": "object",
            "properties": {
                "startMovementDate": {
                    "type": "string"
                },
                "endMovementDate": {
                    "type": "string"
                },
                "startRegistrationDate": {
                    "type": "string"
                },
                "endRegistrationDate": {
                    "type": "string"
                },
                "receptionTypeList": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "L",
                            "P"
                        ]
                    }
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 1000
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
        name="totvs_consume_bonus",
        description="⚠️ Consome bônus/desconto de cliente.",
        inputSchema={
            "type": "object",
            "properties": {
                "customerCode": {
                    "type": "integer"
                },
                "branchCode": {
                    "type": "integer"
                },
                "value": {
                    "type": "number"
                }
            },
            "required": [
                "customerCode",
                "branchCode",
                "value"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_person_message",
        description="⚠️ Inclui mensagem/observação para uma pessoa.",
        inputSchema={
            "type": "object",
            "properties": {
                "personCode": {
                    "type": "integer"
                },
                "message": {
                    "type": "string"
                }
            },
            "required": [
                "personCode",
                "message"
            ]
        },
    ),
    types.Tool(
        name="totvs_relate_customer_representatives",
        description="⚠️ ESCRITA — Relaciona clientes a representante.",
        inputSchema={
            "type": "object",
            "properties": {
                "representativeCode": {
                    "type": "integer"
                },
                "representativeCpfCnpj": {
                    "type": "string"
                },
                "customerCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "customerCpfCnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            }
        },
    ),
    types.Tool(
        name="totvs_change_person_message",
        description=(
            "⚠️ ESCRITA — Altera descricao/status/prioridade de mensagem da pessoa. Status: Unread, Read, Canceled."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "object",
                    "properties": {
                        "personCode": {
                            "type": "integer"
                        },
                        "personCpfCnpj": {
                            "type": "string"
                        },
                        "sequence": {
                            "type": "integer"
                        }
                    },
                    "required": [
                        "sequence"
                    ]
                },
                "description": {
                    "type": "string"
                },
                "status": {
                    "type": "string",
                    "enum": [
                        "Unread",
                        "Read",
                        "Canceled"
                    ]
                },
                "priority": {
                    "type": "integer"
                }
            },
            "required": [
                "filter"
            ]
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_individual_customers": "search_individuals",
    "totvs_search_legal_customers": "search_legal_entities",
    "totvs_get_customer_bonus_balance": "list_bonus_balance",
    "totvs_get_person_statistics": "get_person_statistics",
    "totvs_create_or_update_individual_customer": "create_or_update_individual_customer",
    "totvs_create_or_update_legal_customer": "create_or_update_legal_customer",
    "totvs_get_branches_list": "get_branches_list",
    "totvs_search_representatives": "search_representatives",
    "totvs_get_person_classifications": "get_classifications",
    "totvs_remove_person_classification_relationship": "remove_classification_relationship",
    "totvs_get_email_types": "get_email_types",
    "totvs_get_phone_types": "get_phone_types",
    "totvs_get_contact_types": "get_contact_types",
    "totvs_search_reception_sale": "search_reception_sale",
    "totvs_consume_bonus": "consume_bonus",
    "totvs_create_person_message": "create_message",
    "totvs_relate_customer_representatives": "relate_customer_representatives",
    "totvs_change_person_message": "change_message",
}