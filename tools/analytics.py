"""
Analytics Tools
===============
API Analytics v2 — múltiplos base paths
Movimentação fiscal, ranking e-commerce, painel financeiro, painel de vendedor.
"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.analytics")
BASE_ANALYTICS = "/api/totvsmoda/analytics/v2"
BASE_ECOMMERCE = "/api/totvsmoda/ecommerce-sales-order/v2"
BASE_FINANCIAL = "/api/totvsmoda/financial-panel/v2"
BASE_SELLER    = "/api/totvsmoda/analytics/v2/seller-panel"


def _financial_body(args: dict[str, Any]) -> dict[str, Any]:
    """Mapeia campos amigáveis para o body do financial-panel (branchs/datemin/datemax)."""
    body: dict[str, Any] = {}
    # branchCodeList ou branchCode → branchs (array obrigatório)
    if args.get("branchCodeList"):
        body["branchs"] = args["branchCodeList"]
    elif args.get("branchCode"):
        body["branchs"] = [args["branchCode"]]
    if args.get("startDate") or args.get("datemin"):
        body["datemin"] = args.get("datemin") or args.get("startDate")
    if args.get("endDate") or args.get("datemax"):
        body["datemax"] = args.get("datemax") or args.get("endDate")
    return body


class AnalyticsTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    # ── Movimentação Fiscal ────────────────────────────────────────────────

    async def search_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/fiscal-movement/search — Movimentação fiscal geral."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ANALYTICS}/fiscal-movement/search", body)

    async def search_branch_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/branch-fiscal-movement/search — Empresas da movimentação fiscal."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ANALYTICS}/branch-fiscal-movement/search", body)

    async def search_stock_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/stock-fiscal-movement/search — Tipo de saldo da movimentação fiscal."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ANALYTICS}/stock-fiscal-movement/search", body)

    async def search_product_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/product-fiscal-movement/search — Produtos da movimentação fiscal."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ANALYTICS}/product-fiscal-movement/search", body)

    async def search_person_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/person-fiscal-movement/search — Pessoa da movimentação fiscal."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ANALYTICS}/person-fiscal-movement/search", body)

    async def search_seller_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/seller-fiscal-movement/search — Vendedor da movimentação fiscal."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ANALYTICS}/seller-fiscal-movement/search", body)

    async def search_payment_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/payment-fiscal-movement/search — Condição de pagamento da movimentação fiscal."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ANALYTICS}/payment-fiscal-movement/search", body)

    async def search_representative_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/representative-fiscal-movement/search — Representante da movimentação fiscal."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ANALYTICS}/representative-fiscal-movement/search", body)

    async def search_buyer_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/buyer-fiscal-movement/search — Comprador da movimentação fiscal."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ANALYTICS}/buyer-fiscal-movement/search", body)

    async def search_operation_fiscal_movement(self, args: dict[str, Any]) -> Any:
        """POST analytics/operation-fiscal-movement/search — Operação da movimentação fiscal."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ANALYTICS}/operation-fiscal-movement/search", body)

    async def get_branch_sale(self, args: dict[str, Any]) -> Any:
        """GET analytics/branch-sale — Vendas e devoluções por empresa (CNPJ obrigatório)."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE_ANALYTICS}/branch-sale", params=params or None)

    # ── E-commerce Stats ───────────────────────────────────────────────────

    async def search_best_selling_products(self, args: dict[str, Any]) -> Any:
        """POST ecommerce/best-selling-products/search — Ranking dos mais vendidos."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ECOMMERCE}/best-selling-products/search", body)

    async def search_sales_quantity_hour(self, args: dict[str, Any]) -> Any:
        """POST ecommerce/sales-quantity-hour/search — Vendas por hora no período."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ECOMMERCE}/sales-quantity-hour/search", body)

    async def search_sales_quantity_weekday(self, args: dict[str, Any]) -> Any:
        """POST ecommerce/sales-quantity-weekday/search — Vendas por dia da semana."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ECOMMERCE}/sales-quantity-weekday/search", body)

    async def search_orders_customer_quantity(self, args: dict[str, Any]) -> Any:
        """POST ecommerce/orders-customer-quantity/search — Vendas por quantidade de clientes."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_ECOMMERCE}/orders-customer-quantity/search", body)

    # ── Painel Financeiro ──────────────────────────────────────────────────

    async def search_total_receivable(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/total-receivable/search — Totais de contas a receber."""
        return await self.client.post(f"{BASE_FINANCIAL}/total-receivable/search", _financial_body(args))

    async def search_total_payable(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/total-payable/search — Totais de contas a pagar."""
        return await self.client.post(f"{BASE_FINANCIAL}/total-payable/search", _financial_body(args))

    async def search_ranking_customer_biggers(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/ranking-customer-biggers/search — Top 5 clientes que mais compraram."""
        return await self.client.post(f"{BASE_FINANCIAL}/ranking-customer-biggers/search", _financial_body(args))

    async def search_ranking_customer_debtors(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/ranking-customer-debtors/search — Top 5 clientes em atraso."""
        body = _financial_body(args)
        return await self.client.post(f"{BASE_FINANCIAL}/ranking-customer-debtors/search", body)

    async def search_financial_income_statement(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/financial-income-statement/search — DRF."""
        return await self.client.post(f"{BASE_FINANCIAL}/financial-income-statement/search", _financial_body(args))

    async def search_biweekly(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/biweekly/search — Total a pagar e receber quinzenal."""
        body = _financial_body(args)
        return await self.client.post(f"{BASE_FINANCIAL}/biweekly/search", body)

    async def search_ranking_supplier_biggers(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/ranking-supplier-biggers/search — Maiores fornecedores."""
        return await self.client.post(f"{BASE_FINANCIAL}/ranking-supplier-biggers/search", _financial_body(args))

    async def search_ranking_supplier_debtors(self, args: dict[str, Any]) -> Any:
        """POST financial-panel/ranking-supplier-debtors/search — Fornecedores com maiores débitos."""
        return await self.client.post(f"{BASE_FINANCIAL}/ranking-supplier-debtors/search", _financial_body(args))

    # ── Painel de Vendedor ─────────────────────────────────────────────────

    async def search_seller_panel_totals(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/totals/search — Totais do painel de vendedor."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_SELLER}/totals/search", body)

    async def search_seller_top_customers(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/seller/top-customers — Melhores clientes do vendedor."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_SELLER}/seller/top-customers", body)

    async def search_seller_period_birthday(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/seller/period-birthday — Aniversariantes do período."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_SELLER}/seller/period-birthday", body)

    async def search_seller_sales_target(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/sales-target/search — Meta do vendedor."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_SELLER}/sales-target/search", body)

    async def search_customer_purchased_products(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/seller/customer-purchased-products — Produtos comprados pelo cliente."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_SELLER}/seller/customer-purchased-products", body)

    async def search_seller_pending_conditionals(self, args: dict[str, Any]) -> Any:
        """POST seller-panel/seller/pending-conditionals — Condicionais pendentes do vendedor."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE_SELLER}/seller/pending-conditionals", body)
