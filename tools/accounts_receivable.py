"""
Accounts Receivable Tools
=========================
API Accounts Receivable v2 — /api/totvsmoda/accounts-receivable/v2/
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults
from tools._dates import normalize_day_ranges
import response_cache as cache

logger = logging.getLogger("totvs-moda-mcp.accounts-receivable")
BASE = "/api/totvsmoda/accounts-receivable/v2"
ZERO_OPTIONAL_INVOICE_VALUES = {
    "interestValue",
    "discountValue",
    "grossUpValue",
    "expensesValue",
}


def _drop_zero_optional_invoice_values(body: dict[str, Any]) -> None:
    for invoice in body.get("invoices", []):
        if not isinstance(invoice, dict):
            continue
        for field in ZERO_OPTIONAL_INVOICE_VALUES:
            if invoice.get(field) == 0:
                invoice.pop(field)


class AccountsReceivableTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_customer_financial_balance(self, args: dict[str, Any]) -> Any:
        """POST /customer-financial-balance/search — Limite financeiro e saldo do cliente."""
        args = inject_branch_defaults(args)
        # filter: quem buscar
        flt: dict[str, Any] = {}
        if args.get("customerCodeList"):
            flt["customerCodeList"] = args["customerCodeList"]
        if args.get("customerCpfCnpjList"):
            flt["customerCpfCnpjList"] = args["customerCpfCnpjList"]
        if args.get("change") is not None:
            flt["change"] = args["change"]
        elif args.get("startChangeDate") or args.get("endChangeDate"):
            flt["change"] = {k: v for k, v in {
                "startDate": args.get("startChangeDate"),
                "endDate": args.get("endChangeDate"),
                "branchCodeList": args.get("changeBranchCodeList"),
            }.items() if v is not None}

        # option: o que retornar por filial
        option: dict[str, Any] = {}
        if args.get("branchCodeList"):
            option["branchCodeList"] = args["branchCodeList"]
        for flag in (
            "isLimit", "isOpenInvoice", "isRefundCredit", "isAdvanceAmount",
            "isDofni", "isDofniCheck", "isTransactionOut", "isConsigned",
            "isInvoiceBehindSchedule", "isSalesOrderAdvance",
        ):
            if args.get(flag) is not None:
                option[flag] = args[flag]
        if args.get("dateInvoiceBehindSchedule"):
            option["dateInvoiceBehindSchedule"] = args["dateInvoiceBehindSchedule"]

        body: dict[str, Any] = {
            "filter": flt,
            "option": option,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 500),
        }
        result = await self.client.post(f"{BASE}/customer-financial-balance/search", body)
        return apply_fields(result, args)

    async def search_documents(self, args: dict[str, Any]) -> Any:
        """POST /documents/search — Documentos de contas a receber."""
        args = inject_branch_defaults(args)
        args = normalize_day_ranges(args)
        flt: dict[str, Any] = {}
        for field in (
            "branchCodeList", "customerCodeList", "customerCpfCnpjList",
            "startExpiredDate", "endExpiredDate",
            "startPaymentDate", "endPaymentDate",
            "startIssueDate", "endIssueDate",
            "startCreditDate", "endCreditDate",
            "statusList", "documentTypeList", "billingTypeList",
            "dischargeTypeList", "chargeTypeList",
            "hasOpenInvoices", "receivableCodeList", "ourNumberList",
            "commissionedCode", "commissionedCpfCnpj",
            "closingCodeCommission", "closingCompanyCommission", "closingDateCommission",
            "closingCommissionedCode", "closingCommissionedCpfCnpj", "change",
        ):
            if args.get(field) is not None:
                flt[field] = args[field]

        if "change" not in flt and (args.get("startChangeDate") or args.get("endChangeDate")):
            flt["change"] = {k: v for k, v in {
                "startDate": args.get("startChangeDate"),
                "endDate": args.get("endChangeDate"),
                "inCheck": args.get("inCheck"),
            }.items() if v is not None}

        body: dict[str, Any] = {
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        if flt:
            body["filter"] = flt
        if args.get("expand"):
            body["expand"] = args["expand"]
        if args.get("order"):
            body["order"] = args["order"]

        cached = cache.get("receivable", body, cache.FINANCIAL)
        if cached is not None:
            return self._finalize_receivable(cached, args)

        result = await self.client.post(f"{BASE}/documents/search", body)
        cache.put("receivable", body, result)
        return self._finalize_receivable(result, args)

    @staticmethod
    def _classify_receivable_items(result: Any) -> tuple[Any, dict | None]:
        """Tag each document with isOpen/isSettled/openValue and total them.

        A document is "settled" when it has a settlementDate or a paidValue > 0;
        otherwise it is "open". Returns a NEW result (no mutation of the cached
        object) plus an open-vs-settled summary.

        Note: this intentionally does NOT deduplicate the invoice/receipt pairs
        the API returns — that rule is company-specific and not safe to assume.
        It only classifies and totals, which already prevents the "soma dobrada"
        mistake by keeping open and settled apart.
        """
        if not isinstance(result, dict) or not isinstance(result.get("items"), list):
            return result, None
        new_items = []
        open_count = settled_count = 0
        open_value = settled_value = 0.0
        for it in result["items"]:
            if not isinstance(it, dict):
                new_items.append(it)
                continue
            inst = it.get("installmentValue") or 0
            paid = it.get("paidValue") or 0
            settled = bool(it.get("settlementDate")) or (paid is not None and paid > 0)
            nit = dict(it)
            nit["isSettled"] = bool(settled)
            nit["isOpen"] = not settled
            nit["openValue"] = 0.0 if settled else round(max(inst - paid, 0), 2)
            new_items.append(nit)
            if settled:
                settled_count += 1
                settled_value += paid or inst
            else:
                open_count += 1
                open_value += inst
        summary = {
            "open": {"count": open_count, "value": round(open_value, 2)},
            "settled": {"count": settled_count, "value": round(settled_value, 2)},
        }
        return {**result, "items": new_items}, summary

    def _finalize_receivable(self, result: Any, args: dict[str, Any]) -> Any:
        summary = None
        if args.get("withStatusFlags"):
            result, summary = self._classify_receivable_items(result)
        out = apply_fields(result, args)
        if summary is not None and isinstance(out, dict):
            out["receivableSummary"] = summary
        return out

    async def search_printed_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-print/search — Boletos já impressos."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if k != "fields" and v is not None}
        result = await self.client.post(f"{BASE}/invoices-print/search", body)
        return apply_fields(result, args)

    async def get_gift_check_balances(self, args: dict[str, Any]) -> Any:
        """GET /gift-check-balances — Saldo de cheque presente."""
        args = inject_branch_defaults(args)
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/gift-check-balances", params=params or None)

    async def get_bank_slip(self, args: dict[str, Any]) -> Any:
        """POST /bank-slip — Retorna base64 do boleto bancário."""
        args = inject_branch_defaults(args)
        body: dict[str, Any] = {
            "branchCode": args["branchCode"],
            "customerCode": args["customerCode"],
            "receivableCode": args["receivableCode"],
            "installmentNumber": args["installmentNumber"],
        }
        if args.get("customerCpfCnpj"):
            body["customerCpfCnpj"] = args["customerCpfCnpj"]
        return await self.client.post(f"{BASE}/bank-slip", body)

    async def get_payment_link(self, args: dict[str, Any]) -> Any:
        """POST /payment-link — Retorna link de pagamento PIX da fatura."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/payment-link", body)

    # ── WRITE ──────────────────────────────────────────────────────────────

    async def settle_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-settle/create — ⚠️ Liquidar faturas."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices-settle/create", body)

    async def create_invoice(self, args: dict[str, Any]) -> Any:
        """POST /invoices — ⚠️ Incluir fatura em aberto."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices", body)

    async def renegotiate_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-renegotiate — ⚠️ Renegociar faturas."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices-renegotiate", body)

    async def pay_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-payment — ⚠️ Baixa de faturas."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        body.pop("branchCodeList", None)
        _drop_zero_optional_invoice_values(body)
        return await self.client.post(f"{BASE}/invoices-payment", body)

    async def create_gift_check(self, args: dict[str, Any]) -> Any:
        """POST /gift-checks — ⚠️ Incluir cheque presente."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/gift-checks", body)

    async def change_charge_type(self, args: dict[str, Any]) -> Any:
        """POST /documents/change-charge-type — ⚠️ Altera tipo de cobrança de fatura."""
        args = inject_branch_defaults(args)
        if not args.get("customerCode") and not args.get("customerCpfCnpj"):
            raise ValueError("customerCode OU customerCpfCnpj é obrigatório")
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/documents/change-charge-type", body)

    async def move_gift_check(self, args: dict[str, Any]) -> Any:
        """POST /gift-check-movements — ⚠️ Movimenta cheque presente."""
        args = inject_branch_defaults(args)
        if args.get("value") is None:
            raise ValueError("'value' é obrigatório")
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/gift-check-movements", body)

    async def upsert_invoice_commission(self, args: dict[str, Any]) -> Any:
        """POST /comission — ⚠️ Cria ou atualiza comissão de fatura."""
        args = inject_branch_defaults(args)
        if not args.get("receivableCode"):
            raise ValueError("'receivableCode' é obrigatório")
        if not args.get("installments"):
            raise ValueError("'installments' é obrigatório")
        if not args.get("customerCode") and not args.get("customerCpfCnpj"):
            raise ValueError("customerCode OU customerCpfCnpj é obrigatório")
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/comission", body)


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_customer_financial_balance",
        description=(
            "Limite financeiro e saldo do cliente por filial. Retorna limite, faturas em aberto, crédito de devolução, adiantamento e outros."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customerCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos dos clientes"
                },
                "customerCpfCnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "CPF/CNPJ dos clientes"
                },
                "branchCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Filiais para retorno dos saldos"
                },
                "isLimit": {
                    "type": "boolean",
                    "description": "Retornar limite de crédito"
                },
                "isOpenInvoice": {
                    "type": "boolean",
                    "description": "Retornar faturas em aberto"
                },
                "isRefundCredit": {
                    "type": "boolean",
                    "description": "Retornar crédito de devolução"
                },
                "isAdvanceAmount": {
                    "type": "boolean",
                    "description": "Retornar adiantamento"
                },
                "isDofni": {
                    "type": "boolean",
                    "description": "Retornar DOFNI"
                },
                "isConsigned": {
                    "type": "boolean",
                    "description": "Retornar consignado"
                },
                "isInvoiceBehindSchedule": {
                    "type": "boolean",
                    "description": "Retornar faturas em atraso"
                },
                "isSalesOrderAdvance": {
                    "type": "boolean",
                    "description": "Retornar adiantamento de pedido de venda"
                },
                "change": {
                    "type": "object",
                    "description": "Filtro oficial por alteração: {startDate,endDate,branchCodeList,inLimit/inOpenInvoice/inRefundCredit/inAdvanceAmount/inDofni/inDofniCheck/inTransactionOut/inConsigned/inSalesOrderAdvance}. Se usar datas, informe branchCodeList e ao menos um in..."
                },
                "startChangeDate": {
                    "type": "string",
                    "description": "Data de alteração inicial (ISO 8601)"
                },
                "endChangeDate": {
                    "type": "string",
                    "description": "Data de alteração final"
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
                    "description": "Lista opcional de campos a retornar. Reduz tokens."
                }
            }
        },
    ),
    types.Tool(
        name="totvs_search_receivable_documents",
        description=(
            "Busca documentos a receber (faturas, duplicatas). Retorna items[] com: branchCode, customerCode, customerCpfCnpj, receivableCode, installmentCode, issueDate, expiredDate, paymentDate, installmentValue, paidValue, discountValue, interestValue, status (1=Normal, 2=Devolvido, 3=Cancelado, 4=Quebrado), chargeType, billingType, bearerCode, bearerName. Filtros úteis: startExpiredDate + endExpiredDate, statusList=[1], hasOpenInvoices=true. Para inadimplentes: statusList=[1] + endExpiredDate < hoje. Suporta expand: check, invoice, commissioneds, calculateValue."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos das filiais"
                },
                "customerCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos dos clientes"
                },
                "customerCpfCnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "CPF/CNPJ dos clientes"
                },
                "startExpiredDate": {
                    "type": "string",
                    "description": "Vencimento inicial (ISO 8601)"
                },
                "endExpiredDate": {
                    "type": "string",
                    "description": "Vencimento final"
                },
                "startPaymentDate": {
                    "type": "string",
                    "description": "Data pagamento inicial"
                },
                "endPaymentDate": {
                    "type": "string",
                    "description": "Data pagamento final"
                },
                "startIssueDate": {
                    "type": "string",
                    "description": "Data emissão inicial"
                },
                "endIssueDate": {
                    "type": "string",
                    "description": "Data emissão final"
                },
                "change": {
                    "type": "object",
                    "description": "Filtro oficial por alteração: {startDate,endDate,inCheck}"
                },
                "startChangeDate": {
                    "type": "string",
                    "description": "Data alteração inicial"
                },
                "endChangeDate": {
                    "type": "string",
                    "description": "Data alteração final"
                },
                "statusList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Status: 1=Normal, 2=Devolvido, 3=Cancelado, 4=Quebrado"
                },
                "documentTypeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Tipo documento: 1=fatura, 2=cheque, 3=dinheiro, 4=cartão crédito, 5=cartão débito, 16=TED/DOC, 18=cheque presente"
                },
                "billingTypeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Tipo faturamento: 1=Venda à vista, 2=Venda a prazo, 3=Recebimento à vista, 4=Recebimento a prazo, 12=Renegociação, 13=Cobrança cartão"
                },
                "dischargeTypeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Tipo baixa: 0=Título não baixado, 1=Via recebimento, 7=Via banco, 9=Renegociação, 12=Conta bancária"
                },
                "chargeTypeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Tipo cobrança: 0=Não está em cobrança, 1=Simples, 2=Descontada, 3=Caucionada, 5=Sem registro, 8=Protestado"
                },
                "hasOpenInvoices": {
                    "type": "boolean",
                    "description": "Apenas faturas em aberto"
                },
                "withStatusFlags": {
                    "type": "boolean",
                    "description": "Se true, marca cada documento com isOpen/isSettled/openValue e adiciona receivableSummary com totais em aberto x recebido (evita somar valores duplicados)."
                },
                "receivableCodeList": {
                    "type": "array",
                    "items": {
                        "type": "number"
                    },
                    "description": "Códigos das faturas"
                },
                "ourNumberList": {
                    "type": "array",
                    "items": {
                        "type": "number"
                    },
                    "description": "Nosso número da parcela"
                },
                "commissionedCode": {
                    "type": "integer",
                    "description": "Código do comissionado"
                },
                "commissionedCpfCnpj": {
                    "type": "string",
                    "description": "CPF/CNPJ do comissionado"
                },
                "closingCodeCommission": {
                    "type": "integer",
                    "description": "Código de fechamento da comissão. Use junto com os demais filtros de fechamento quando aplicável."
                },
                "closingCompanyCommission": {
                    "type": "integer",
                    "description": "Empresa de fechamento da comissão. Não use isolado."
                },
                "closingDateCommission": {
                    "type": "string",
                    "description": "Data de fechamento da comissão"
                },
                "closingCommissionedCode": {
                    "type": "integer",
                    "description": "Código do comissionado no fechamento"
                },
                "closingCommissionedCpfCnpj": {
                    "type": "string",
                    "description": "CPF/CNPJ do comissionado no fechamento"
                },
                "expand": {
                    "type": "string",
                    "description": "Expansão: check, invoice, commissioneds, calculateValue"
                },
                "order": {
                    "type": "string",
                    "description": "Ordenação: branchCode, customerCode, customerCpfCnpj, receivableCode, installmentCode, maxChangeFilterDate. Use - para desc."
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
                    "description": "Lista opcional de campos a retornar. Reduz tokens. Ex: ['customerCode','installmentValue','expiredDate']."
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_bank_slip",
        description="Base64 do boleto bancário de uma fatura. Requer código da fatura, parcela e cliente.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "customerCode": {
                    "type": "integer",
                    "description": "Código do cliente"
                },
                "customerCpfCnpj": {
                    "type": "string",
                    "description": "CPF/CNPJ do cliente (alternativa ao customerCode)"
                },
                "receivableCode": {
                    "type": "integer",
                    "description": "Código da fatura (receivableCode)"
                },
                "installmentNumber": {
                    "type": "integer",
                    "description": "Número da parcela da fatura"
                }
            },
            "required": [
                "branchCode",
                "customerCode",
                "receivableCode",
                "installmentNumber"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_payment_link",
        description="Link de pagamento PIX de uma fatura.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "customerCode": {
                    "type": "integer",
                    "description": "Código do cliente"
                },
                "customerCpfCnpj": {
                    "type": "string",
                    "description": "CPF/CNPJ do cliente"
                },
                "receivableCode": {
                    "type": "integer",
                    "description": "Código da fatura"
                },
                "installmentNumber": {
                    "type": "integer",
                    "description": "Número da parcela"
                }
            },
            "required": [
                "branchCode",
                "receivableCode",
                "installmentNumber"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_gift_check_balances",
        description="Consulta saldo de cheque presente por cliente, número do cheque ou código de barras.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial (obrigatório se não informar barCode)"
                },
                "customerCode": {
                    "type": "integer",
                    "description": "Código do cliente"
                },
                "customerCpfCnpj": {
                    "type": "string",
                    "description": "CPF/CNPJ do cliente"
                },
                "checkNumber": {
                    "type": "integer",
                    "description": "Número do cheque (obrigatório se não informar barCode)"
                },
                "barCode": {
                    "type": "string",
                    "description": "Código de barras do cheque (quando informado, não passar branchCode/checkNumber)"
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100
                }
            }
        },
    ),
    types.Tool(
        name="totvs_change_charge_type",
        description="⚠️ ESCRITA — Altera tipo de cobrança de uma fatura a receber.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial da fatura"
                },
                "customerCode": {
                    "type": "integer",
                    "description": "Código do cliente"
                },
                "customerCpfCnpj": {
                    "type": "string",
                    "description": "CPF/CNPJ do cliente"
                },
                "receivableCode": {
                    "type": "integer",
                    "description": "Código da fatura"
                },
                "installmentCode": {
                    "type": "integer",
                    "description": "Código da parcela"
                },
                "chargeType": {
                    "type": "integer",
                    "description": "Tipo de cobrança"
                },
                "observation": {
                    "type": "string",
                    "description": "Observação a ser gravada no log"
                }
            },
            "required": [
                "branchCode",
                "customerCode",
                "receivableCode",
                "installmentCode",
                "chargeType"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_receivable_invoice",
        description="⚠️ ESCRITA — Inclui fatura a receber. Use somente com dados validados pelo financeiro.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCnpj": {
                    "type": "string",
                    "description": "CNPJ da empresa que gravará a fatura, somente dígitos"
                },
                "customerCpfCnpj": {
                    "type": "string",
                    "description": "CPF/CNPJ do cliente, somente dígitos"
                },
                "receivableCode": {
                    "type": "integer",
                    "description": "Número da fatura"
                },
                "installments": {
                    "type": "array",
                    "description": "Parcelas da fatura",
                    "items": {
                        "type": "object",
                        "properties": {
                            "installmentCode": {
                                "type": "integer"
                            },
                            "documentType": {
                                "type": "integer",
                                "description": "1=Fatura, 2=Cheque, 3=Dinheiro, 4=Cartão crédito, 5=Cartão débito, 16=TED/DOC, 18=Cheque presente, 20=CREDEV, 25=Voucher, 26=PIX, 50=Outro"
                            },
                            "billingType": {
                                "type": "integer",
                                "description": "1=Venda à vista, 2=Venda a prazo, 3=Recebimento à vista, 4=Recebimento a prazo, 12=Renegociação, 18=Agrupamento de fatura"
                            },
                            "chargeType": {
                                "type": "integer",
                                "description": "0=Não está em cobrança, 1=Simples, 2=Descontada, 3=Caucionada, 5=Sem registro, 18=Direto para boleto, 37=Carteira digital, 38=Bolepix"
                            },
                            "bearerCode": {
                                "type": "integer"
                            },
                            "issueDate": {
                                "type": "string"
                            },
                            "expiredDate": {
                                "type": "string"
                            },
                            "originalExpirationDate": {
                                "type": "string"
                            },
                            "installmentValue": {
                                "type": "number"
                            },
                            "originalValue": {
                                "type": "number"
                            },
                            "taxValue": {
                                "type": "number"
                            },
                            "ourNumber": {
                                "type": "integer"
                            },
                            "dacOurNumber": {
                                "type": "string"
                            },
                            "observations": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                }
                            },
                            "checkInstallment": {
                                "type": "object"
                            },
                            "cardInstallment": {
                                "type": "object"
                            },
                            "classifications": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                }
                            },
                            "commissions": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                }
                            },
                            "revenues": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                }
                            },
                            "additionalFields": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                }
                            },
                            "taxes": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                }
                            }
                        },
                        "required": [
                            "installmentCode",
                            "documentType",
                            "billingType",
                            "chargeType",
                            "bearerCode",
                            "issueDate",
                            "expiredDate",
                            "installmentValue"
                        ]
                    }
                }
            },
            "required": [
                "branchCnpj",
                "customerCpfCnpj",
                "receivableCode",
                "installments"
            ]
        },
    ),
    types.Tool(
        name="totvs_settle_invoices",
        description=(
            "⚠️ ESCRITA — Baixa bancária de fatura a receber (somente para contas do tipo banco). Para pagamentos em dinheiro, cartão ou adiantamento use totvs_pay_invoices."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "customerCode": {
                    "type": "integer",
                    "description": "Código do cliente"
                },
                "receivableCode": {
                    "type": "integer",
                    "description": "Código da fatura"
                },
                "installmentCode": {
                    "type": "integer",
                    "description": "Código da parcela"
                },
                "bankNumber": {
                    "type": "integer",
                    "description": "Número do banco"
                },
                "agencyNumber": {
                    "type": "integer",
                    "description": "Número da agência"
                },
                "account": {
                    "type": "string",
                    "description": "Número da conta bancária"
                }
            },
            "required": [
                "branchCode",
                "customerCode",
                "receivableCode",
                "installmentCode",
                "bankNumber",
                "agencyNumber",
                "account"
            ]
        },
    ),
    types.Tool(
        name="totvs_pay_invoices",
        description=(
            "⚠️ ESCRITA — Baixa/liquidação de faturas a receber com múltiplas formas de pagamento: cartão de crédito, débito, adiantamento (dinheiro/caixa), conta corrente ou CREDEV. A API rejeita interestValue/discountValue/grossUpValue/expensesValue quando enviados como 0; omita esses campos quando não houver valor."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Filial da liquidação"
                },
                "settlementDate": {
                    "type": "string",
                    "description": "Data da liquidação (ISO 8601, ex: 2026-04-27T00:00:00)"
                },
                "invoices": {
                    "type": "array",
                    "description": "Lista de faturas a baixar",
                    "items": {
                        "type": "object",
                        "properties": {
                            "branchCode": {
                                "type": "integer",
                                "description": "Filial da fatura"
                            },
                            "customerCode": {
                                "type": "integer",
                                "description": "Código do cliente"
                            },
                            "customerCpfCnpj": {
                                "type": "string",
                                "description": "CPF/CNPJ do cliente (alternativa ao customerCode)"
                            },
                            "receivableCode": {
                                "type": "integer",
                                "description": "Código da fatura"
                            },
                            "installmentCode": {
                                "type": "integer",
                                "description": "Código da parcela"
                            },
                            "paidValue": {
                                "type": "number",
                                "description": "Valor pago"
                            },
                            "interestValue": {
                                "type": "number",
                                "description": "Valor de juros. Opcional: omita quando for 0."
                            },
                            "discountValue": {
                                "type": "number",
                                "description": "Valor de desconto. Opcional: omita quando for 0."
                            },
                            "grossUpValue": {
                                "type": "number",
                                "description": "Valor de acréscimo. Opcional: omita quando for 0."
                            },
                            "expensesValue": {
                                "type": "number",
                                "description": "Valor de despesas financeiras. Opcional: omita quando for 0."
                            }
                        },
                        "required": [
                            "branchCode",
                            "customerCode",
                            "receivableCode",
                            "installmentCode",
                            "paidValue"
                        ]
                    }
                },
                "payments": {
                    "type": "array",
                    "description": "Lista de pagamentos",
                    "items": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "number",
                                "description": "Valor do pagamento"
                            },
                            "paidType": {
                                "type": "integer",
                                "description": "Tipo de pagamento: 1=CreditCard, 2=DebitCard, 3=Advance, 4=CurrentAccount, 5=CREDEV"
                            },
                            "card": {
                                "type": "object",
                                "description": "Dados do cartão, obrigatório para paidType 1 ou 2",
                                "properties": {
                                    "nsu": {
                                        "type": "integer"
                                    },
                                    "autorization": {
                                        "type": "string"
                                    },
                                    "cardBrand": {
                                        "type": "string"
                                    },
                                    "cardOperator": {
                                        "type": "string"
                                    },
                                    "installmentQuantity": {
                                        "type": "integer"
                                    }
                                }
                            },
                            "bank": {
                                "type": "object",
                                "description": "Dados bancários, obrigatório para paidType 4. Use accountCode OU bankNumber+agencyNumber+account.",
                                "properties": {
                                    "bankNumber": {
                                        "type": "integer"
                                    },
                                    "agencyNumber": {
                                        "type": "integer"
                                    },
                                    "account": {
                                        "type": "string"
                                    },
                                    "accountCode": {
                                        "type": "integer"
                                    }
                                }
                            },
                            "credev": {
                                "type": "object",
                                "description": "Dados de CREDEV para paidType 5",
                                "properties": {
                                    "branchCode": {
                                        "type": "integer"
                                    }
                                }
                            },
                            "movementDate": {
                                "type": "string",
                                "description": "Data de movimento para conciliação (ISO 8601)"
                            }
                        },
                        "required": [
                            "value",
                            "paidType"
                        ]
                    }
                }
            },
            "required": [
                "branchCode",
                "settlementDate",
                "invoices",
                "payments"
            ]
        },
    ),
    types.Tool(
        name="totvs_move_gift_check",
        description="⚠️ ESCRITA — Movimenta cheque presente.",
        inputSchema={
            "type": "object",
            "properties": {
                "value": {
                    "type": "number",
                    "description": "Valor da movimentação"
                },
                "branchCode": {
                    "type": "integer"
                },
                "customerCode": {
                    "type": "integer"
                },
                "sequence": {
                    "type": "integer"
                },
                "barCode": {
                    "type": "string"
                }
            },
            "required": [
                "value"
            ]
        },
    ),
    types.Tool(
        name="totvs_upsert_invoice_commission",
        description="⚠️ ESCRITA — Inclui ou altera comissão de fatura.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "customerCode": {
                    "type": "integer"
                },
                "customerCpfCnpj": {
                    "type": "string"
                },
                "receivableCode": {
                    "type": "integer"
                },
                "installments": {
                    "type": "array",
                    "description": "Lista UpsertCommissionInstallmentRequestModel (installmentCode, commissionedCode, commissionedPercentage)",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "receivableCode",
                "installments"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_gift_check",
        description="⚠️ ESCRITA — Inclui cheque presente para cliente.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "customerCode": {
                    "type": "integer",
                    "description": "Código do cliente"
                },
                "customerCpfCnpj": {
                    "type": "string",
                    "description": "CPF/CNPJ do cliente"
                },
                "value": {
                    "type": "number",
                    "description": "Valor do cheque"
                },
                "nominated": {
                    "type": "string",
                    "description": "Nominal (max 80 chars)"
                },
                "barCode": {
                    "type": "string",
                    "description": "Código de barras (max 40, somente números)"
                },
                "issueDate": {
                    "type": "string",
                    "description": "Data de emissão (ISO 8601)"
                },
                "expiredDate": {
                    "type": "string",
                    "description": "Data de validade"
                }
            },
            "required": [
                "branchCode",
                "customerCode",
                "value",
                "nominated",
                "barCode"
            ]
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_customer_financial_balance": "search_customer_financial_balance",
    "totvs_search_receivable_documents": "search_documents",
    "totvs_get_bank_slip": "get_bank_slip",
    "totvs_get_payment_link": "get_payment_link",
    "totvs_get_gift_check_balances": "get_gift_check_balances",
    "totvs_change_charge_type": "change_charge_type",
    "totvs_create_receivable_invoice": "create_invoice",
    "totvs_settle_invoices": "settle_invoices",
    "totvs_pay_invoices": "pay_invoices",
    "totvs_move_gift_check": "move_gift_check",
    "totvs_upsert_invoice_commission": "upsert_invoice_commission",
    "totvs_create_gift_check": "create_gift_check",
}