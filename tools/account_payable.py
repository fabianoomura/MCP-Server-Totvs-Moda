"""
Account Payable Tools
=====================
API Accounts Payable v2 — /api/totvsmoda/accounts-payable/v2/
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults
from tools._dates import normalize_day_ranges
import response_cache as cache

logger = logging.getLogger("totvs-moda-mcp.account-payable")
BASE = "/api/totvsmoda/accounts-payable/v2"


class AccountPayableTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_duplicates(self, args: dict[str, Any]) -> Any:
        """POST /duplicates/search — Consulta de duplicatas a pagar."""
        args = inject_branch_defaults(args)
        args = normalize_day_ranges(args)
        flt: dict[str, Any] = {
            "branchCodeList": args["branchCodeList"],
        }
        for field in (
            "change",
            "duplicateCodeList", "supplierCodeList", "bearerCodeList",
            "startIssueDate", "endIssueDate",
            "startExpiredDate", "endExpiredDate",
            "startSettlementDate", "endSettlementDate",
            "startArrivalDate", "endArrivalDate",
            "inclusionTypeList", "status", "documentTypeList",
        ):
            if args.get(field) is not None:
                flt[field] = args[field]

        if "change" not in flt and (args.get("startChangeDate") or args.get("endChangeDate")):
            flt["change"] = {k: v for k, v in {
                "startDate": args.get("startChangeDate"),
                "endDate": args.get("endChangeDate"),
            }.items() if v is not None}

        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        if args.get("order"):
            body["order"] = args["order"]

        cached = cache.get("payable", body, cache.FINANCIAL)
        if cached is not None:
            return apply_fields(cached, args)

        result = await self.client.post(f"{BASE}/duplicates/search", body)
        cache.put("payable", body, result)
        return apply_fields(result, args)

    async def search_commissions_paid(self, args: dict[str, Any]) -> Any:
        """POST /comissions-paid/search — Fechamento de comissão por representante."""
        args = inject_branch_defaults(args)
        flt: dict[str, Any] = {
            "closingCompanyCode": args["closingCompanyCode"],
        }
        for field in (
            "closingCode", "startClosingDate", "endClosingDate",
            "commissionedCodeList", "commissionedCpfCnpjList",
        ):
            if args.get(field) is not None:
                flt[field] = args[field]

        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        if args.get("order"):
            body["order"] = args["order"]
        if args.get("expand"):
            body["expand"] = args["expand"]

        result = await self.client.post(f"{BASE}/comissions-paid/search", body)
        return apply_fields(result, args)

    async def create_duplicate(self, args: dict[str, Any]) -> Any:
        """POST /duplicates — ⚠️ Inclusão de duplicata a pagar."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/duplicates", body)

    async def group_duplicates(self, args: dict[str, Any]) -> Any:
        """POST /group-duplicates — ⚠️ Agrupa duplicatas a pagar."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/group-duplicates", body)


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_payable_duplicates",
        description=(
            "Consulta duplicatas de contas a pagar com filtros flexíveis de vencimento, emissão, fornecedor e status."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos das filiais (obrigatório)"
                },
                "change": {
                    "type": "object",
                    "description": "Filtro oficial por alteração: {startDate,endDate}. Quando informado, use branchCodeList."
                },
                "duplicateCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos das duplicatas"
                },
                "supplierCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos dos fornecedores"
                },
                "bearerCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos dos portadores"
                },
                "startIssueDate": {
                    "type": "string",
                    "description": "Data emissão inicial (ISO 8601)"
                },
                "endIssueDate": {
                    "type": "string",
                    "description": "Data emissão final"
                },
                "startExpiredDate": {
                    "type": "string",
                    "description": "Data vencimento inicial"
                },
                "endExpiredDate": {
                    "type": "string",
                    "description": "Data vencimento final"
                },
                "startSettlementDate": {
                    "type": "string",
                    "description": "Data liquidação inicial"
                },
                "endSettlementDate": {
                    "type": "string",
                    "description": "Data liquidação final"
                },
                "startArrivalDate": {
                    "type": "string",
                    "description": "Data chegada inicial"
                },
                "endArrivalDate": {
                    "type": "string",
                    "description": "Data chegada final"
                },
                "startChangeDate": {
                    "type": "string",
                    "description": "Data alteração inicial"
                },
                "endChangeDate": {
                    "type": "string",
                    "description": "Data alteração final"
                },
                "inclusionTypeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Tipo de inclusão: 1=Manual, 2=Automática(NF), 3=Via caixa, 4=Folha pgto, 5=Troca cheque próprio, 6=Rateio despesas, 7=Rateio receitas, 9=Conversão, 11-14=Entre empresas"
                },
                "status": {
                    "type": "string",
                    "enum": [
                        "Normal",
                        "Canceled",
                        "Grouped",
                        "Retorned",
                        "CommissionSettled",
                        "Broken"
                    ],
                    "description": "Situação: Normal(N), Canceled(C=Cancelada), Grouped(A=Agrupada), Retorned(D=Devolvida), CommissionSettled(L=Liquidada comissão), Broken(Q=Quebrada)"
                },
                "documentTypeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Tipo documento: 1=Duplicata, 2=Boleto, 3=Comissão, 4=Guia(doc), 5=Financiamento, 6=Vale, 7=NF, 8=Nota desconto, 9=Taxa admin, 10=Juros financiamento, 11=Bonificação, 12=Depósito, 13=Compror, 14=Vendor, 15=Recibo, 16=TED/DOC, 17=Empréstimo, 18=Conhecimento frete, 19=Pró-labore, 20=Adiantamento, 21=DARF Normal, 22=GPS, 25=FGTS, 27=GNRE, 30=Cheque presente, 31=Fatura terceiro, 50=Outro título"
                },
                "order": {
                    "type": "string",
                    "description": "Ordenação suportada: productCode, maxChangeFilterDate. Use - para desc."
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100,
                    "description": "Máximo 100 no Swagger"
                },
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Lista opcional de campos a retornar. Reduz tokens. Ex: ['supplierName','balanceValue','expiredDate']."
                }
            },
            "required": [
                "branchCodeList"
            ]
        },
    ),
    types.Tool(
        name="totvs_search_commissions_paid",
        description="Fechamento de comissão por período e representante/comissionado.",
        inputSchema={
            "type": "object",
            "properties": {
                "closingCompanyCode": {
                    "type": "integer",
                    "description": "Código da empresa de fechamento de comissão (obrigatório)"
                },
                "closingCode": {
                    "type": "integer",
                    "description": "Número do fechamento de comissão"
                },
                "startClosingDate": {
                    "type": "string",
                    "description": "Data inicial do fechamento (ISO 8601)"
                },
                "endClosingDate": {
                    "type": "string",
                    "description": "Data final do fechamento"
                },
                "commissionedCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos dos comissionados"
                },
                "commissionedCpfCnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "CPF/CNPJ dos comissionados"
                },
                "expand": {
                    "type": "string",
                    "description": "Expansão: accountMovements"
                },
                "order": {
                    "type": "string",
                    "description": "Ordenação: closingDate, commissionedCode"
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
            },
            "required": [
                "closingCompanyCode"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_duplicate",
        description=(
            "⚠️ ESCRITA — Inclui duplicata a pagar. Requer CNPJ da empresa, CPF/CNPJ do fornecedor, código da duplicata e lista de parcelas."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCnpj": {
                    "type": "string",
                    "description": "CNPJ da empresa (max 14 chars)"
                },
                "supplierCpfCnpj": {
                    "type": "string",
                    "description": "CPF ou CNPJ do fornecedor (max 14 chars)"
                },
                "duplicateCode": {
                    "type": "integer",
                    "description": "Código da duplicata (max 10 chars)"
                },
                "installments": {
                    "type": "array",
                    "description": "Lista de parcelas",
                    "items": {
                        "type": "object",
                        "properties": {
                            "installmentCode": {
                                "type": "integer",
                                "description": "Número da parcela (max 3)"
                            },
                            "bearerCode": {
                                "type": "integer",
                                "description": "Código do portador (max 4)"
                            },
                            "issueDate": {
                                "type": "string",
                                "description": "Data de emissão (ISO 8601)"
                            },
                            "dueDate": {
                                "type": "string",
                                "description": "Data de vencimento"
                            },
                            "arrivalDate": {
                                "type": "string",
                                "description": "Data de chegada"
                            },
                            "document": {
                                "type": "integer",
                                "description": "Tipo documento: 1=Duplicata, 2=Boleto, 3=Comissão, 4=Guia, 5=Financiamento, 6=Vale, 7=NF, 15=Recibo, 16=TED/DOC, 17=Empréstimo, 18=Conhecimento frete, 20=Adiantamento, 50=Outro título"
                            },
                            "prevision": {
                                "type": "integer",
                                "description": "Tipo previsão: 1=Previsto, 2=Real, 3=Consignação"
                            },
                            "stage": {
                                "type": "integer",
                                "description": "Estágio: 1=Título não conferido, 2=Liberado para pagamento, 3=Cheque autorizado, 4=Cheque emitido, 5=Título aceito, 10=Endossado, 20=Pagamento em banco, 30=Reservado, 40=Pagamento automático, 70=Com restrição, 90=Liquidado"
                            },
                            "duplicateValue": {
                                "type": "number",
                                "description": "Valor da parcela"
                            },
                            "expenses": {
                                "type": "array",
                                "description": "Lista de despesas",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "expenseCode": {
                                            "type": "integer"
                                        },
                                        "costCenterCode": {
                                            "type": "integer"
                                        },
                                        "proratedPercentage": {
                                            "type": "number"
                                        }
                                    },
                                    "required": [
                                        "expenseCode",
                                        "costCenterCode",
                                        "proratedPercentage"
                                    ]
                                }
                            }
                        },
                        "required": [
                            "installmentCode",
                            "bearerCode",
                            "issueDate",
                            "dueDate",
                            "arrivalDate",
                            "document",
                            "prevision",
                            "stage",
                            "duplicateValue",
                            "expenses"
                        ]
                    }
                }
            },
            "required": [
                "branchCnpj",
                "supplierCpfCnpj",
                "duplicateCode",
                "installments"
            ]
        },
    ),
    types.Tool(
        name="totvs_group_duplicates",
        description=(
            "⚠️ ESCRITA — Agrupa duplicatas a pagar. Útil para logística/frete quando há uso recorrente de agrupamento."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCnpj": {
                    "type": "string",
                    "description": "CNPJ da empresa que gravará a duplicata agrupada, somente dígitos"
                },
                "supplierCpfCnpj": {
                    "type": "string",
                    "description": "CPF/CNPJ do fornecedor, somente dígitos"
                },
                "duplicateCode": {
                    "type": "integer",
                    "description": "Código da duplicata agrupadora"
                },
                "document": {
                    "type": "integer",
                    "enum": [
                        1,
                        18
                    ],
                    "description": "Tipo documento: 1=Duplicata, 18=Conhecimento de frete"
                },
                "dueDate": {
                    "type": "string",
                    "description": "Data de vencimento ISO 8601"
                },
                "groupInstallments": {
                    "type": "array",
                    "description": "Duplicatas que serão agrupadas",
                    "items": {
                        "type": "object",
                        "properties": {
                            "branchCnpj": {
                                "type": "string"
                            },
                            "supplierCpfCnpj": {
                                "type": "string"
                            },
                            "duplicateCode": {
                                "type": "integer"
                            },
                            "installmentCode": {
                                "type": "integer"
                            }
                        },
                        "required": [
                            "branchCnpj",
                            "supplierCpfCnpj",
                            "duplicateCode",
                            "installmentCode"
                        ]
                    }
                }
            },
            "required": [
                "branchCnpj",
                "supplierCpfCnpj",
                "duplicateCode",
                "dueDate",
                "groupInstallments"
            ]
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_payable_duplicates": "search_duplicates",
    "totvs_search_commissions_paid": "search_commissions_paid",
    "totvs_create_duplicate": "create_duplicate",
    "totvs_group_duplicates": "group_duplicates",
}