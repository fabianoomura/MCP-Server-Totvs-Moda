"""
Account Payable Tools
=====================
API Accounts Payable v2 — /api/totvsmoda/accounts-payable/v2/
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields

logger = logging.getLogger("totvs-moda-mcp.account-payable")
BASE = "/api/totvsmoda/accounts-payable/v2"


class AccountPayableTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_duplicates(self, args: dict[str, Any]) -> Any:
        """POST /duplicates/search — Consulta de duplicatas a pagar."""
        flt: dict[str, Any] = {
            "branchCodeList": args["branchCodeList"],
        }
        for field in (
            "duplicateCodeList", "supplierCodeList", "bearerCodeList",
            "startIssueDate", "endIssueDate",
            "startExpiredDate", "endExpiredDate",
            "startSettlementDate", "endSettlementDate",
            "startArrivalDate", "endArrivalDate",
            "inclusionTypeList", "status", "documentTypeList",
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
        if args.get("order"):
            body["order"] = args["order"]

        result = await self.client.post(f"{BASE}/duplicates/search", body)
        return apply_fields(result, args)

    async def search_commissions_paid(self, args: dict[str, Any]) -> Any:
        """POST /comissions-paid/search — Fechamento de comissão por representante."""
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
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/duplicates", body)
