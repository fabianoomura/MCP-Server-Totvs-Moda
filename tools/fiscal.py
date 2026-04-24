"""
Fiscal Tools
============
API Fiscal v2 — /api/totvsmoda/fiscal/v2/
Notas fiscais, XML NF-e, DANFE, certificado digital, centro de custo.
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults

logger = logging.getLogger("totvs-moda-mcp.fiscal")
BASE = "/api/totvsmoda/fiscal/v2"


class FiscalTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices/search — Lista NF-e por filtro geral."""
        args = inject_branch_defaults(args)
        flt: dict[str, Any] = {
            "branchCodeList": args["branchCodeList"],
        }
        for field in (
            "invoiceSequenceList", "invoiceCodeList", "operationType", "origin",
            "invoiceStatusList", "personCodeList", "operationCodeList",
            "documentTypeCodeList", "personCpfCnpjList",
            "startInvoiceCode", "endInvoiceCode",
            "startIssueDate", "endIssueDate",
            "serialCodeList", "eletronicInvoiceStatusList",
            "shippingCompanyCodeList", "shippingCompanyCpfCnpjList",
            "amountLastDays",
            "transactionBranchCode", "transactionCode", "transactionDate",
        ):
            if args.get(field) is not None:
                flt[field] = args[field]

        if args.get("startChangeDate") or args.get("endChangeDate"):
            flt["change"] = {k: v for k, v in {
                "startDate": args.get("startChangeDate"),
                "endDate": args.get("endChangeDate"),
            }.items() if v is not None}

        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        if args.get("expand"):
            body["expand"] = args["expand"]
        if args.get("order"):
            body["order"] = args["order"]

        result = await self.client.post(f"{BASE}/invoices/search", body)
        return apply_fields(result, args)

    async def get_xml_content(self, args: dict[str, Any]) -> Any:
        """GET /xml-contents/{accessKey} — XML da NF-e pela chave de acesso (44 dígitos)."""
        return await self.client.get(f"{BASE}/xml-contents/{args['accessKey']}")

    async def get_invoice_item_detail(self, args: dict[str, Any]) -> Any:
        """GET /invoices/item-detail-search — Detalhe de itens da NF-e."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/invoices/item-detail-search", params=params or None)

    async def get_danfe(self, args: dict[str, Any]) -> Any:
        """POST /danfe-search — Base64 do DANFE via XML da NF-e."""
        body: dict[str, Any] = {"mainInvoiceXml": args["mainInvoiceXml"]}
        if args.get("nfeDocumentType"):
            body["nfeDocumentType"] = args["nfeDocumentType"]
        return await self.client.post(f"{BASE}/danfe-search", body)

    async def search_invoice_products(self, args: dict[str, Any]) -> Any:
        """POST /invoice-products/search — Produtos de NF-e por filtro geral."""
        args = inject_branch_defaults(args)
        flt: dict[str, Any] = {
            "branchCodeList": args["branchCodeList"],
        }
        for field in (
            "ProductCodeList", "BatchBarCodeList", "invoiceCodeList",
            "operationType", "modality", "origin",
            "invoiceStatusList", "personCodeList", "ignorePersonCodeList",
            "operationCodeList", "personCpfCnpjList", "ignorePersonCpfCnpjList",
            "startIssueDate", "endIssueDate", "acessKeyList",
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

        result = await self.client.post(f"{BASE}/invoice-products/search", body)
        return apply_fields(result, args)

    async def get_digital_certificates(self, args: dict[str, Any]) -> Any:
        """GET /digital-certificates — Dados de certificados digitais."""
        args = inject_branch_defaults(args)
        params: dict[str, Any] = {
            "BranchCode": args["branchCode"],
            "EnviromentType": args["environmentType"],
        }
        return await self.client.get(f"{BASE}/digital-certificates", params=params)

    async def get_cost_center(self, args: dict[str, Any]) -> Any:
        """GET /cost-center — Centros de custo (datas obrigatórias)."""
        args = inject_branch_defaults(args)
        params: dict[str, Any] = {
            "StartChangeDate": args["startChangeDate"],
            "EndChangeDate": args["endChangeDate"],
        }
        if args.get("isInactive") is not None:
            params["IsInactive"] = args["isInactive"]
        if args.get("page"):
            params["Page"] = args["page"]
        if args.get("pageSize"):
            params["PageSize"] = args["pageSize"]
        return await self.client.get(f"{BASE}/cost-center", params=params)

    async def get_pending_conditional_products(self, args: dict[str, Any]) -> Any:
        """GET /invoices/pending-conditional-products — Saldo de produto em condicional por pessoa."""
        args = inject_branch_defaults(args)
        params: dict[str, Any] = {
            "BranchCode": args["branchCode"],
            "OnlyPendingItem": args.get("onlyPendingItem", True),
        }
        if args.get("personCode"):
            params["PersonCode"] = args["personCode"]
        if args.get("personCpfCnpj"):
            params["PersonCpfCnpj"] = args["personCpfCnpj"]
        return await self.client.get(f"{BASE}/invoices/pending-conditional-products", params=params)

    async def get_disabled_invoices(self, args: dict[str, Any]) -> Any:
        """GET /invoices/disable — NF-e inutilizadas por período e filial."""
        args = inject_branch_defaults(args)
        params: dict[str, Any] = {
            "StartDate": args["startDate"],
            "EndDate": args["endDate"],
            "BranchCodeList": args["branchCodeList"],
        }
        if args.get("page"):
            params["Page"] = args["page"]
        if args.get("pageSize"):
            params["PageSize"] = args["pageSize"]
        if args.get("order"):
            params["Order"] = args["order"]
        return await self.client.get(f"{BASE}/invoices/disable", params=params)

    async def print_transaction(self, args: dict[str, Any]) -> Any:
        """POST /transaction/print — Base64 da impressão da transação em PDF."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/transaction/print", body)

    async def create_manifestation(self, args: dict[str, Any]) -> Any:
        """POST /invoices/manifestations — ⚠️ Manifestação do destinatário NF-e."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices/manifestations", body)
