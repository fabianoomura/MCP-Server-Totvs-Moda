"""
Accounts Receivable Tools
=========================
API Accounts Receivable v2 — /api/totvsmoda/accounts-receivable/v2/
"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.accounts-receivable")
BASE = "/api/totvsmoda/accounts-receivable/v2"


class AccountsReceivableTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_customer_financial_balance(self, args: dict[str, Any]) -> Any:
        """POST /customer-financial-balance/search — Limite financeiro e saldo do cliente."""
        # filter: quem buscar
        flt: dict[str, Any] = {}
        if args.get("customerCodeList"):
            flt["customerCodeList"] = args["customerCodeList"]
        if args.get("customerCpfCnpjList"):
            flt["customerCpfCnpjList"] = args["customerCpfCnpjList"]
        if args.get("startChangeDate") or args.get("endChangeDate"):
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
        return await self.client.post(f"{BASE}/customer-financial-balance/search", body)

    async def search_documents(self, args: dict[str, Any]) -> Any:
        """POST /documents/search — Documentos de contas a receber."""
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
        ):
            if args.get(field) is not None:
                flt[field] = args[field]

        if args.get("startChangeDate") or args.get("endChangeDate"):
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

        return await self.client.post(f"{BASE}/documents/search", body)

    async def search_printed_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-print/search — Boletos já impressos."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices-print/search", body)

    async def get_gift_check_balances(self, args: dict[str, Any]) -> Any:
        """GET /gift-check-balances — Saldo de cheque presente."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/gift-check-balances", params=params or None)

    async def get_bank_slip(self, args: dict[str, Any]) -> Any:
        """POST /bank-slip — Retorna base64 do boleto bancário."""
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
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/payment-link", body)

    # ── WRITE ──────────────────────────────────────────────────────────────

    async def settle_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-settle/create — ⚠️ Liquidar faturas."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices-settle/create", body)

    async def create_invoice(self, args: dict[str, Any]) -> Any:
        """POST /invoices — ⚠️ Incluir fatura em aberto."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices", body)

    async def renegotiate_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-renegotiate — ⚠️ Renegociar faturas."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices-renegotiate", body)

    async def pay_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices-payment — ⚠️ Baixa de faturas."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices-payment", body)

    async def create_gift_check(self, args: dict[str, Any]) -> Any:
        """POST /gift-checks — ⚠️ Incluir cheque presente."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/gift-checks", body)

    async def change_charge_type(self, args: dict[str, Any]) -> Any:
        """POST /documents/change-charge-type — ⚠️ Altera tipo de cobrança de fatura."""
        body: dict[str, Any] = {
            "branchCode": args["branchCode"],
            "customerCode": args["customerCode"],
            "receivableCode": args["receivableCode"],
            "installmentCode": args["installmentCode"],
            "chargeType": args["chargeType"],
        }
        if args.get("customerCpfCnpj"):
            body["customerCpfCnpj"] = args["customerCpfCnpj"]
        if args.get("observation"):
            body["observation"] = args["observation"]
        return await self.client.post(f"{BASE}/documents/change-charge-type", body)
