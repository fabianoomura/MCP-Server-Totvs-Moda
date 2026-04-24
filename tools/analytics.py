"""
Analytics Tools
===============
API Analytics v2 — múltiplos base paths
Movimentação fiscal, ranking e-commerce, painel financeiro, painel de vendedor.
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults

logger = logging.getLogger("totvs-moda-mcp.analytics")
BASE_ANALYTICS = "/api/totvsmoda/analytics/v2"
BASE_ECOMMERCE = "/api/totvsmoda/ecommerce-sales-order/v2"
BASE_FINANCIAL = "/api/totvsmoda/financial-panel/v2"
BASE_SELLER    = "/api/totvsmoda/analytics/v2/seller-panel"


def _financial_body(args: dict[str, Any]) -> dict[str, Any]:
    """Mapeia campos amigáveis para o body do financial-panel (branchs/datemin/datemax)."""
    body: dict[str, Any] = {}
    if args.get("branchCodeList"):
        body["branchs"] = args["branchCodeList"]
    elif args.get("branchCode"):
        body["branchs"] = [args["branchCode"]]
    if args.get("startDate") or args.get("datemin"):
        body["datemin"] = args.get("datemin") or args.get("startDate")
    if args.get("endDate") or args.get("datemax"):
        body["datemax"] = args.get("datemax") or args.get("endDate")
    return body


def _fiscal_movement_body(args: dict[str, Any]) -> dict[str, Any]:
    """Monta body para endpoints de movimentação fiscal analytics.
    Aceita branchCode (int) ou branchCodeList (array) → filter.branchCodeList.
    startDate/endDate → filter.startIssueDate/endIssueDate.
    """
    flt: dict[str, Any] = {}
    if args.get("branchCodeList"):
        flt["branchCodeList"] = args["branchCodeList"]
    elif args.get("branchCode"):
        flt["branchCodeList"] = [args["branchCode"]]

    if args.get("startDate") or args.get("startIssueDate"):
        flt["startIssueDate"] = args.get("startIssueDate") or args.get("startDate")
    if args.get("endDate") or args.get("endIssueDate"):
        flt["endIssueDate"] = args.get("endIssueDate") or args.get("endDate")

    for field in ("operationType", "operationCodeList", "personCodeList",
                  "personCpfCnpjList", "invoiceStatusList"):
        if args.get(field) is not None:
            flt[field] = args[field]

    body: dict[str, Any] = {"filter": flt}
    body["page"] = args.get("page", 1)
    body["pageSize"] = args.get("pageSize", 100)
    if args.get("order"):
        body["order"] = args["order"]
    return body


class AnalyticsTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    # ── Movimentação Fiscal ────────────────────────────────────────────────

    async def search_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/fiscal-movement/search — Movimentação fiscal geral."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_ANALYTICS}/fiscal-movement/search", _fiscal_movement_body(args))
        return apply_fields(result, args)

    async def search_branch_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/branch-fiscal-movement/search — Empresas da movimentação fiscal."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_ANALYTICS}/branch-fiscal-movement/search", _fiscal_movement_body(args))
        return apply_fields(result, args)

    async def search_stock_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/stock-fiscal-movement/search — Tipo de saldo da movimentação fiscal."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_ANALYTICS}/stock-fiscal-movement/search", _fiscal_movement_body(args))
        return apply_fields(result, args)

    async def search_product_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/product-fiscal-movement/search — Produtos da movimentação fiscal."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_ANALYTICS}/product-fiscal-movement/search", _fiscal_movement_body(args))
        return apply_fields(result, args)

    async def search_person_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/person-fiscal-movement/search — Pessoa da movimentação fiscal."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_ANALYTICS}/person-fiscal-movement/search", _fiscal_movement_body(args))
        return apply_fields(result, args)

    async def search_seller_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/seller-fiscal-movement/search — Vendedor da movimentação fiscal."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_ANALYTICS}/seller-fiscal-movement/search", _fiscal_movement_body(args))
        return apply_fields(result, args)

    async def search_payment_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/payment-fiscal-movement/search — Condição de pagamento da movimentação fiscal."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_ANALYTICS}/payment-fiscal-movement/search", _fiscal_movement_body(args))
        return apply_fields(result, args)

    async def search_representative_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/representative-fiscal-movement/search — Representante da movimentação fiscal."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_ANALYTICS}/representative-fiscal-movement/search", _fiscal_movement_body(args))
        return apply_fields(result, args)

    async def search_buyer_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/buyer-fiscal-movement/search — Comprador da movimentação fiscal."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_ANALYTICS}/buyer-fiscal-movement/search", _fiscal_movement_body(args))
        return apply_fields(result, args)

    async def search_operation_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/operation-fiscal-movement/search — Operação da movimentação fiscal."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_ANALYTICS}/operation-fiscal-movement/search", _fiscal_movement_body(args))
        return apply_fields(result, args)

    async def get_branch_sale(self, args: dict[str, Any]) -> Any:
        """GET analytics/branch-sale — Vendas e devoluções por empresa (CNPJ obrigatório)."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE_ANALYTICS}/branch-sale", params=params or None)

    # ── E-commerce Stats ───────────────────────────────────────────────────

    async def search_best_selling_products(self, args: dict[str, Any]) -> Any:
        """POST ecommerce/best-selling-products/search — Ranking dos mais vendidos."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE_ECOMMERCE}/best-selling-products/search", body)
        return apply_fields(result, args)

    async def search_sales_quantity_hour(self, args: dict[str, Any]) -> Any:
        """POST ecommerce/sales-quantity-hour/search — Vendas por hora no período."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE_ECOMMERCE}/sales-quantity-hour/search", body)
        return apply_fields(result, args)

    async def search_sales_quantity_weekday(self, args: dict[str, Any]) -> Any:
        """POST ecommerce/sales-quantity-weekday/search — Vendas por dia da semana."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE_ECOMMERCE}/sales-quantity-weekday/search", body)
        return apply_fields(result, args)

    async def search_orders_customer_quantity(self, args: dict[str, Any]) -> Any:
        """POST ecommerce/orders-customer-quantity/search — Vendas por quantidade de clientes."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE_ECOMMERCE}/orders-customer-quantity/search", body)
        return apply_fields(result, args)

    # ── Painel Financeiro ──────────────────────────────────────────────────

    async def search_total_receivable(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/total-receivable/search — Totais de contas a receber."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_FINANCIAL}/total-receivable/search", _financial_body(args))
        return apply_fields(result, args)

    async def search_total_payable(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/total-payable/search — Totais de contas a pagar."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_FINANCIAL}/total-payable/search", _financial_body(args))
        return apply_fields(result, args)

    async def search_ranking_customer_biggers(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/ranking-customer-biggers/search — Top 5 clientes que mais compraram."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_FINANCIAL}/ranking-customer-biggers/search", _financial_body(args))
        return apply_fields(result, args)

    async def search_ranking_customer_debtors(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/ranking-customer-debtors/search — Top 5 clientes em atraso."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_FINANCIAL}/ranking-customer-debtors/search", _financial_body(args))
        return apply_fields(result, args)

    async def search_financial_income_statement(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/financial-income-statement/search — DRF."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_FINANCIAL}/financial-income-statement/search", _financial_body(args))
        return apply_fields(result, args)

    async def search_biweekly(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/biweekly/search — Total a pagar e receber quinzenal."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_FINANCIAL}/biweekly/search", _financial_body(args))
        return apply_fields(result, args)

    async def search_ranking_supplier_biggers(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/ranking-supplier-biggers/search — Maiores fornecedores."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_FINANCIAL}/ranking-supplier-biggers/search", _financial_body(args))
        return apply_fields(result, args)

    async def search_ranking_supplier_debtors(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/ranking-supplier-debtors/search — Fornecedores com maiores débitos."""
        args = inject_branch_defaults(args)
        result = await self.client.post(f"{BASE_FINANCIAL}/ranking-supplier-debtors/search", _financial_body(args))
        return apply_fields(result, args)

    # ── Painel de Vendedor ─────────────────────────────────────────────────

    async def search_seller_panel_totals(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/totals/search — Totais do painel de vendedor."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE_SELLER}/totals/search", body)
        return apply_fields(result, args)

    async def search_seller_top_customers(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/seller/top-customers — Melhores clientes do vendedor."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE_SELLER}/seller/top-customers", body)
        return apply_fields(result, args)

    async def search_seller_period_birthday(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/seller/period-birthday — Aniversariantes do período."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE_SELLER}/seller/period-birthday", body)
        return apply_fields(result, args)

    async def search_seller_sales_target(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/sales-target/search — Meta do vendedor."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE_SELLER}/sales-target/search", body)
        return apply_fields(result, args)

    async def search_customer_purchased_products(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/seller/customer-purchased-products — Produtos comprados pelo cliente."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE_SELLER}/seller/customer-purchased-products", body)
        return apply_fields(result, args)

    async def search_seller_pending_conditionals(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/seller/pending-conditionals — Condicionais pendentes do vendedor."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE_SELLER}/seller/pending-conditionals", body)
        return apply_fields(result, args)
