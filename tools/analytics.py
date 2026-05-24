"""
Optional Analytics Tools
========================
Gateway isolado para endpoints de Analytics/painel do TOTVS Moda.

Analytics e paineis podem depender de modulo contratado/permissoes especificas.
Por isso o server expoe um unico tool opcional, habilitado por
TOTVS_ENABLE_ANALYTICS=true, em vez de publicar dezenas de tools no contexto.
"""
from __future__ import annotations

from typing import Any

from totvs_client import TotvsClient
from tools._fields import apply_fields


ENDPOINTS: dict[str, dict[str, str]] = {
    "analytics_v2_branch_fiscal_movement_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/branch-fiscal-movement/search"},
    "analytics_v2_branch_sale": {"method": "GET", "path": "/api/totvsmoda/analytics/v2/branch-sale"},
    "analytics_v2_buyer_fiscal_movement_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/buyer-fiscal-movement/search"},
    "analytics_v2_fiscal_movement_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/fiscal-movement/search"},
    "analytics_v2_operation_fiscal_movement_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/operation-fiscal-movement/search"},
    "analytics_v2_payment_fiscal_movement_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/payment-fiscal-movement/search"},
    "analytics_v2_person_fiscal_movement_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/person-fiscal-movement/search"},
    "analytics_v2_product_fiscal_movement_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/product-fiscal-movement/search"},
    "analytics_v2_representative_fiscal_movement_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/representative-fiscal-movement/search"},
    "analytics_v2_seller_fiscal_movement_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-fiscal-movement/search"},
    "analytics_v2_seller_panel_product_classification_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-panel/product-classification/search"},
    "analytics_v2_seller_panel_sales_target_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-panel/sales-target/search"},
    "analytics_v2_seller_panel_sales_vs_returns_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-panel/sales-vs-returns/search"},
    "analytics_v2_seller_panel_seller_code": {"method": "GET", "path": "/api/totvsmoda/analytics/v2/seller-panel/seller-code"},
    "analytics_v2_seller_panel_seller_brancheslist": {"method": "GET", "path": "/api/totvsmoda/analytics/v2/seller-panel/seller/branchesList"},
    "analytics_v2_seller_panel_seller_conditional_rate": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-panel/seller/conditional-rate"},
    "analytics_v2_seller_panel_seller_customer_purchased_products": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-panel/seller/customer-purchased-products"},
    "analytics_v2_seller_panel_seller_day_count_customers": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-panel/seller/day-count-customers"},
    "analytics_v2_seller_panel_seller_pending_conditionals": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-panel/seller/pending-conditionals"},
    "analytics_v2_seller_panel_seller_period_birthday": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-panel/seller/period-birthday"},
    "analytics_v2_seller_panel_seller_top_customers": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-panel/seller/top-customers"},
    "analytics_v2_seller_panel_totals_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-panel/totals/search"},
    "analytics_v2_seller_panel_weekdays_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/seller-panel/weekdays/search"},
    "analytics_v2_stock_fiscal_movement_search": {"method": "POST", "path": "/api/totvsmoda/analytics/v2/stock-fiscal-movement/search"},
    "ecommerce_sales_order_v2_best_selling_products_search": {"method": "POST", "path": "/api/totvsmoda/ecommerce-sales-order/v2/best-selling-products/search"},
    "ecommerce_sales_order_v2_orders_customer_quantity_search": {"method": "POST", "path": "/api/totvsmoda/ecommerce-sales-order/v2/orders-customer-quantity/search"},
    "ecommerce_sales_order_v2_sales_quantity_hour_search": {"method": "POST", "path": "/api/totvsmoda/ecommerce-sales-order/v2/sales-quantity-hour/search"},
    "ecommerce_sales_order_v2_sales_quantity_weekday_search": {"method": "POST", "path": "/api/totvsmoda/ecommerce-sales-order/v2/sales-quantity-weekday/search"},
    "financial_panel_v2_account_balance_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/account-balance/search"},
    "financial_panel_v2_amount_received_document_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/amount-received-document/search"},
    "financial_panel_v2_average_payment_period_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/average-payment-period/search"},
    "financial_panel_v2_average_receipt_period_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/average-receipt-period/search"},
    "financial_panel_v2_biweekly_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/biweekly/search"},
    "financial_panel_v2_financial_income_statement_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/financial-income-statement/search"},
    "financial_panel_v2_open_amount_document_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/open-amount-document/search"},
    "financial_panel_v2_overdue_cards_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/overdue-cards/search"},
    "financial_panel_v2_ranking_customer_biggers_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/ranking-customer-biggers/search"},
    "financial_panel_v2_ranking_customer_debtors_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/ranking-customer-debtors/search"},
    "financial_panel_v2_ranking_supplier_biggers_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/ranking-supplier-biggers/search"},
    "financial_panel_v2_ranking_supplier_debtors_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/ranking-supplier-debtors/search"},
    "financial_panel_v2_total_payable_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/total-payable/search"},
    "financial_panel_v2_total_receivable_search": {"method": "POST", "path": "/api/totvsmoda/financial-panel/v2/total-receivable/search"},
    "manufacturing_v2_defect_finalization_search": {"method": "POST", "path": "/api/totvsmoda/manufacturing/v2/defect-finalization/search"},
    "manufacturing_v2_defect_panel_search": {"method": "POST", "path": "/api/totvsmoda/manufacturing/v2/defect-panel/search"},
    "manufacturing_v2_fifteendays_finalization_search": {"method": "POST", "path": "/api/totvsmoda/manufacturing/v2/fifteenDays-finalization/search"},
    "manufacturing_v2_normal_finalization_search": {"method": "POST", "path": "/api/totvsmoda/manufacturing/v2/normal-finalization/search"},
    "manufacturing_v2_quantity_location_search": {"method": "POST", "path": "/api/totvsmoda/manufacturing/v2/quantity-location/search"},
    "manufacturing_v2_quantity_part_location_search": {"method": "POST", "path": "/api/totvsmoda/manufacturing/v2/quantity-part-location/search"},
    "manufacturing_v2_throughput_movement_place_search": {"method": "POST", "path": "/api/totvsmoda/manufacturing/v2/throughput-movement-place/search"},
    "sale_panel_v2_branch_ranking_search": {"method": "POST", "path": "/api/totvsmoda/sale-panel/v2/branch-ranking/search"},
    "sale_panel_v2_document_types_search": {"method": "POST", "path": "/api/totvsmoda/sale-panel/v2/document-types/search"},
    "sale_panel_v2_hours_search": {"method": "POST", "path": "/api/totvsmoda/sale-panel/v2/hours/search"},
    "sale_panel_v2_product_classification_types": {"method": "GET", "path": "/api/totvsmoda/sale-panel/v2/product-classification-types"},
    "sale_panel_v2_product_classifications_search": {"method": "POST", "path": "/api/totvsmoda/sale-panel/v2/product-classifications/search"},
    "sale_panel_v2_sellers_list_search": {"method": "POST", "path": "/api/totvsmoda/sale-panel/v2/sellers-list/search"},
    "sale_panel_v2_sellers_search": {"method": "POST", "path": "/api/totvsmoda/sale-panel/v2/sellers/search"},
    "sale_panel_v2_totals_branch_type_search": {"method": "POST", "path": "/api/totvsmoda/sale-panel/v2/totals-branch-type/search"},
    "sale_panel_v2_totals_branch_search": {"method": "POST", "path": "/api/totvsmoda/sale-panel/v2/totals-branch/search"},
    "sale_panel_v2_totals_seller_search": {"method": "POST", "path": "/api/totvsmoda/sale-panel/v2/totals-seller/search"},
    "sale_panel_v2_totals_search": {"method": "POST", "path": "/api/totvsmoda/sale-panel/v2/totals/search"},
    "sale_panel_v2_weekdays_search": {"method": "POST", "path": "/api/totvsmoda/sale-panel/v2/weekdays/search"},
}


class AnalyticsTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def call_endpoint(self, args: dict[str, Any]) -> Any:
        """Chama um endpoint Analytics/painel por chave registrada."""
        endpoint = args.get("endpoint")
        if not endpoint:
            raise ValueError("'endpoint' e obrigatorio para totvs_analytics_call")

        spec = ENDPOINTS.get(endpoint)
        if not spec:
            available = ", ".join(sorted(ENDPOINTS))
            raise ValueError(f"Endpoint Analytics desconhecido: {endpoint}. Disponiveis: {available}")

        method = spec["method"]
        path = spec["path"]

        if method == "GET":
            params = args.get("params")
            if params is None:
                params = {
                    k: v
                    for k, v in args.items()
                    if k not in {"endpoint", "body", "fields"} and v is not None
                }
            result = await self.client.get(path, params=params or None)
            return apply_fields(result, args)

        body = args.get("body")
        if body is None:
            body = {
                k: v
                for k, v in args.items()
                if k not in {"endpoint", "params", "fields"} and v is not None
            }
        result = await self.client.post(path, body)
        return apply_fields(result, args)
