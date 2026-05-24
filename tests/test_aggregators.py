"""Tests for the aggregator tools — high-level composition."""
import json
import sys
import types
import pytest
import respx
from httpx import Response

import response_cache as cache
from tools.aggregators import AggregatorTools

from conftest import TOTVS_BASE, TOKEN_URL


@pytest.fixture(autouse=True)
def fake_context_cache(monkeypatch):
    """Fornece context_cache com filial padrão para os testes desse arquivo."""
    fake = types.ModuleType("context_cache")
    fake.CACHE = {
        "branches": [1],
        "operationalDefaults": {
            "priceCodeList": [9],
            "costCodeList": [7, 8],
            "stockCodeList": [3],
            "purchaseOrderOpenStatusList": [1, 3, 5],
        },
    }
    monkeypatch.setitem(sys.modules, "context_cache", fake)
    yield fake


@pytest.fixture(autouse=True)
def clear_response_cache():
    cache.invalidate()
    yield
    cache.invalidate()


def _mock_token():
    return respx.post(TOKEN_URL).mock(
        return_value=Response(
            200,
            json={"access_token": "fake-token", "expires_in": 3600, "token_type": "Bearer"},
        )
    )


# ── get_products_sold ───────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_get_products_sold_aggregates_quantities(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={
            "items": [
                {
                    "orderCode": 1,
                    "items": [
                        {"productCode": 100, "name": "Camiseta", "quantity": 2, "price": 50.0},
                        {"productCode": 200, "name": "Calça",    "quantity": 1, "price": 150.0},
                    ],
                },
                {
                    "orderCode": 2,
                    "items": [
                        {"productCode": 100, "name": "Camiseta", "quantity": 3, "price": 50.0},
                    ],
                },
            ],
        })
    )

    tools = AggregatorTools(client)
    result = await tools.get_products_sold({
        "startDate": "2026-04-01", "endDate": "2026-04-30",
    })

    assert result["totalOrders"] == 2
    top = {p["productCode"]: p for p in result["topProducts"]}
    assert top[100]["totalQuantity"] == 5
    assert top[100]["totalValue"] == 250.0
    assert top[100]["orderCount"] == 2
    assert top[200]["totalQuantity"] == 1
    assert top[200]["orderCount"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_products_sold_respects_topN(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={
            "items": [{
                "orderCode": 1,
                "items": [
                    {"productCode": i, "name": f"P{i}", "quantity": i, "price": 10.0}
                    for i in range(1, 21)
                ],
            }],
        })
    )

    tools = AggregatorTools(client)
    result = await tools.get_products_sold({
        "startDate": "2026-04-01", "endDate": "2026-04-30", "topN": 3,
    })

    assert len(result["topProducts"]) == 3
    assert result["topProducts"][0]["productCode"] == 20


@pytest.mark.asyncio
@respx.mock
async def test_get_products_sold_order_by_value(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={
            "items": [{
                "orderCode": 1,
                "items": [
                    {"productCode": 1, "name": "Cheap bulk", "quantity": 100, "price": 1.0},
                    {"productCode": 2, "name": "Expensive", "quantity": 2,   "price": 500.0},
                ],
            }],
        })
    )

    tools = AggregatorTools(client)
    by_qty = await tools.get_products_sold({
        "startDate": "2026-04-01", "endDate": "2026-04-30", "orderBy": "quantity",
    })
    by_val = await tools.get_products_sold({
        "startDate": "2026-04-01", "endDate": "2026-04-30", "orderBy": "value",
    })

    assert by_qty["topProducts"][0]["productCode"] == 1
    assert by_val["topProducts"][0]["productCode"] == 2


# ── sales_summary_by_period ─────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_sales_summary_groups_by_branch(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={
            "items": [
                {"branchCode": 1, "totalAmountOrder": 100.0, "statusOrder": "BillingReleased"},
                {"branchCode": 1, "totalAmountOrder": 200.0, "statusOrder": "InProgress"},
                {"branchCode": 2, "totalAmountOrder": 50.0,  "statusOrder": "BillingReleased"},
            ],
        })
    )

    tools = AggregatorTools(client)
    result = await tools.sales_summary_by_period({
        "startDate": "2026-04-01", "endDate": "2026-04-30", "groupBy": "branch",
    })

    assert result["totalValue"] == 350.0
    assert result["totalOrders"] == 3
    groups = {g["key"]: g for g in result["groups"]}
    assert groups["1"]["orderCount"] == 2
    assert groups["1"]["totalValue"] == 300.0
    assert groups["2"]["totalValue"] == 50.0


@pytest.mark.asyncio
@respx.mock
async def test_sales_summary_groups_by_status(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={
            "items": [
                {"branchCode": 1, "totalAmountOrder": 100.0, "statusOrder": "BillingReleased"},
                {"branchCode": 1, "totalAmountOrder": 200.0, "statusOrder": "InProgress"},
                {"branchCode": 1, "totalAmountOrder": 50.0,  "statusOrder": "BillingReleased"},
            ],
        })
    )

    tools = AggregatorTools(client)
    result = await tools.sales_summary_by_period({
        "startDate": "2026-04-01", "endDate": "2026-04-30", "groupBy": "status",
    })

    groups = {g["key"]: g for g in result["groups"]}
    assert groups["BillingReleased"]["orderCount"] == 2
    assert groups["BillingReleased"]["totalValue"] == 150.0


# ── top_customers ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_top_customers_ranks_by_value(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={
            "items": [
                {"customerCode": 100, "customerName": "Alice", "totalAmountOrder": 500.0},
                {"customerCode": 200, "customerName": "Bob",   "totalAmountOrder": 200.0},
                {"customerCode": 100, "customerName": "Alice", "totalAmountOrder": 300.0},
            ],
        })
    )

    tools = AggregatorTools(client)
    result = await tools.top_customers({
        "startDate": "2026-04-01", "endDate": "2026-04-30",
    })

    customers = result["customers"]
    assert customers[0]["customerCode"] == 100
    assert customers[0]["totalValue"] == 800.0
    assert customers[0]["orderCount"] == 2
    assert customers[0]["averageOrderValue"] == 400.0


# ── low_stock_alert ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_low_stock_alert_filters_below_threshold(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/balances/search").mock(
        return_value=Response(200, json={
            "items": [
                {"productCode": 1, "name": "A", "productSku": "A-M", "balance": 2},
                {"productCode": 2, "name": "B", "productSku": "B-M", "balance": 50},
                {"productCode": 3, "name": "C", "productSku": "C-M", "balance": 5},
            ],
        })
    )

    tools = AggregatorTools(client)
    result = await tools.low_stock_alert({"threshold": 10, "branchCode": 1})

    assert result["lowStockCount"] == 2
    assert result["products"][0]["productCode"] == 1
    assert result["products"][0]["balance"] == 2
    assert result["products"][1]["productCode"] == 3


# ── orders_by_status_summary ────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_orders_by_status_percentages_sum_100(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={
            "items": [
                {"statusOrder": "BillingReleased", "totalAmountOrder": 300.0},
                {"statusOrder": "BillingReleased", "totalAmountOrder": 300.0},
                {"statusOrder": "InProgress",      "totalAmountOrder": 200.0},
                {"statusOrder": "Blocked",         "totalAmountOrder": 200.0},
            ],
        })
    )

    tools = AggregatorTools(client)
    result = await tools.orders_by_status_summary({
        "startDate": "2026-04-01", "endDate": "2026-04-30",
    })

    assert result["totalOrders"] == 4
    assert result["totalValue"] == 1000.0
    percentages = sum(s["percentage"] for s in result["byStatus"])
    assert abs(percentages - 100) < 0.01

    by_status = {s["status"]: s for s in result["byStatus"]}
    assert by_status["BillingReleased"]["percentage"] == 60.0
    assert by_status["InProgress"]["percentage"] == 20.0


@pytest.mark.asyncio
@respx.mock
async def test_open_purchase_orders_scans_pages_and_filters_open(client):
    _mock_token()

    def handler(request):
        body = json.loads(request.content)
        page = body["page"]
        items = {
            1: [
                {"orderCode": 100, "supplierCode": 10, "supplierName": "Closed", "status": 4, "totalAmountOrder": 500.0},
                {"orderCode": 101, "supplierCode": 11, "supplierName": "Alpha", "status": 5, "totalAmountOrder": 100.0},
            ],
            2: [
                {"orderCode": 102, "supplierCode": 12, "supplierName": "Beta", "status": 3, "totalAmountOrder": 250.0},
            ],
        }[page]
        return Response(200, json={"count": 3, "totalPages": 2, "items": items})

    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/purchase-order/v2/search").mock(side_effect=handler)

    tools = AggregatorTools(client)
    result = await tools.open_purchase_orders({"branchCodeList": [1], "pageSize": 2, "concurrency": 5})

    assert route.call_count == 2
    assert result["totalScanned"] == 3
    assert result["openCount"] == 2
    assert result["openTotalValue"] == 350.0
    assert result["byStatus"] == [
        {"status": 3, "count": 1, "totalValue": 250.0},
        {"status": 5, "count": 1, "totalValue": 100.0},
    ]
    assert [item["orderCode"] for item in result["latestOpen"]] == [102, 101]
    assert [item["orderCode"] for item in result["largestOpen"]] == [102, 101]
    assert result["pageStats"]["pages"] == 2


@pytest.mark.asyncio
@respx.mock
async def test_open_production_orders_scans_pages_and_filters_pending(client):
    _mock_token()

    def handler(request):
        body = json.loads(request.content)
        page = body["page"]
        items = {
            1: [
                {
                    "orderCode": 200,
                    "productCode": 1,
                    "productName": "Done",
                    "status": 30,
                    "quantity": 10,
                    "finishedQuantity": 10,
                    "pendingQuantity": 0,
                    "endDate": "2026-05-01",
                },
                {
                    "orderCode": 201,
                    "productCode": 2,
                    "productName": "Open A",
                    "status": 20,
                    "quantity": 20,
                    "finishedQuantity": 5,
                    "pendingQuantity": 15,
                    "endDate": None,
                    "estimatedEndDate": "2026-05-20",
                },
            ],
            2: [
                {
                    "orderCode": 202,
                    "productCode": 3,
                    "productName": "Open B",
                    "status": 40,
                    "quantity": 30,
                    "finishedQuantity": 10,
                    "pendingQuantity": 20,
                    "endDate": None,
                    "estimatedEndDate": "2026-05-30",
                },
            ],
        }[page]
        return Response(200, json={"count": 3, "totalPages": 2, "items": items})

    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/production-order/v2/orders/search").mock(side_effect=handler)

    tools = AggregatorTools(client)
    result = await tools.open_production_orders({
        "branchCodeList": [1],
        "pageSize": 2,
        "concurrency": 5,
        "asOfDate": "2026-05-22",
    })

    assert route.call_count == 2
    assert result["totalScanned"] == 3
    assert result["openCount"] == 2
    assert result["totalQuantity"] == 50.0
    assert result["finishedQuantity"] == 15.0
    assert result["pendingQuantity"] == 35.0
    assert result["overdueCount"] == 1
    assert result["byStatus"] == [
        {"status": 20, "count": 1, "pendingQuantity": 15.0},
        {"status": 40, "count": 1, "pendingQuantity": 20.0},
    ]
    assert [item["orderCode"] for item in result["latestOpen"]] == [202, 201]
    assert [item["orderCode"] for item in result["largestPending"]] == [202, 201]
    assert result["pageStats"]["pages"] == 2


@pytest.mark.asyncio
@respx.mock
async def test_product_360_collects_product_sections(client):
    _mock_token()
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/product/v2/products/13180/1").mock(
        return_value=Response(200, json={"productCode": 13180, "productName": "Colcha"})
    )
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/balances/search").mock(
        return_value=Response(200, json={"items": [{"productCode": 13180, "stock": 2}]})
    )
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/prices/search").mock(
        return_value=Response(200, json={"items": [{"productCode": 13180, "price": 1107.0}]})
    )
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/costs/search").mock(
        return_value=Response(200, json={"items": [{"productCode": 13180, "cost": 266.04}]})
    )
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/compositions").mock(
        return_value=Response(200, json={"items": [{"componentCode": 1000258}]})
    )
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/product-engineering/v2/consumption-sheet/search").mock(
        return_value=Response(200, json={"items": [{"rawMaterialCode": 1000258}]})
    )

    tools = AggregatorTools(client)
    result = await tools.product_360({"productCode": 13180, "branchCode": 1})

    assert result["productCode"] == 13180
    assert result["summary"]["balanceItems"] == 1
    balance_body = json.loads(
        respx.calls[[call.request.url.path for call in respx.calls].index("/api/totvsmoda/product/v2/balances/search")]
        .request.content
    )
    price_body = json.loads(
        respx.calls[[call.request.url.path for call in respx.calls].index("/api/totvsmoda/product/v2/prices/search")]
        .request.content
    )
    cost_body = json.loads(
        respx.calls[[call.request.url.path for call in respx.calls].index("/api/totvsmoda/product/v2/costs/search")]
        .request.content
    )
    assert balance_body["option"]["balances"][0]["stockCodeList"] == [3]
    assert price_body["option"]["prices"][0]["priceCodeList"] == [9]
    assert cost_body["option"]["costs"][0]["costCodeList"] == [7, 8]
    assert result["summary"]["balanceItems"] == 1
    assert result["summary"]["priceItems"] == 1
    assert result["summary"]["costItems"] == 1
    assert result["summary"]["compositionItems"] == 1
    assert result["summary"]["consumptionItems"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_order_360_uses_branch_from_order_and_fetches_dependents(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={"items": [{"orderCode": 120040, "branchCode": 2}]})
    )
    invoices_route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/invoices").mock(
        return_value=Response(200, json=[{"invoiceCode": 143218}])
    )
    pending_route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/pending-items").mock(
        return_value=Response(200, json=[])
    )

    tools = AggregatorTools(client)
    result = await tools.order_360({"orderCode": 120040})

    assert result["found"] is True
    assert result["branchCode"] == 2
    assert result["summary"]["invoiceCount"] == 1
    assert result["summary"]["pendingItemCount"] == 0
    assert invoices_route.calls.last.request.url.params["branchCode"] == "2"
    assert pending_route.calls.last.request.url.params["branchCode"] == "2"


@pytest.mark.asyncio
@respx.mock
async def test_invoice_360_collects_header_and_products(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/fiscal/v2/invoices/search").mock(
        return_value=Response(200, json={"items": [{"invoiceCode": 143218}]})
    )
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/fiscal/v2/invoice-products/search").mock(
        return_value=Response(200, json={"items": [{"productCode": 13180}, {"productCode": 1000258}]})
    )

    tools = AggregatorTools(client)
    result = await tools.invoice_360({"invoiceCode": 143218, "branchCodeList": [1]})

    assert result["summary"]["invoiceCount"] == 1
    assert result["summary"]["productCount"] == 2


@pytest.mark.asyncio
@respx.mock
async def test_sales_today_summary_groups_status(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={"items": [
            {"orderCode": 1, "customerCode": 10, "customerName": "A", "statusOrder": "Blocked", "totalAmountOrder": 100},
            {"orderCode": 2, "customerCode": 20, "customerName": "B", "statusOrder": "Attended", "totalAmountOrder": 50},
            {"orderCode": 3, "customerCode": 30, "customerName": "C", "statusOrder": "Blocked", "totalAmountOrder": 25},
        ]})
    )

    tools = AggregatorTools(client)
    result = await tools.sales_today_summary({"date": "2026-05-22", "branchCodeList": [1]})

    assert result["totalOrders"] == 3
    assert result["totalValue"] == 175.0
    by_status = {item["status"]: item for item in result["byStatus"]}
    assert by_status["Blocked"]["count"] == 2
    assert by_status["Blocked"]["totalValue"] == 125.0


@pytest.mark.asyncio
@respx.mock
async def test_new_customers_today_checks_history_counts(client):
    _mock_token()

    def handler(request):
        body = json.loads(request.content)
        flt = body.get("filter", {})
        customer_codes = flt.get("customerCodeList")
        if not customer_codes:
            return Response(200, json={"items": [
                {"orderCode": 1, "customerCode": 10, "customerName": "New", "totalAmountOrder": 100},
                {"orderCode": 2, "customerCode": 20, "customerName": "Old", "totalAmountOrder": 50},
            ]})
        count = 1 if customer_codes == [10] else 3
        return Response(200, json={"count": count, "items": [{"orderCode": 1}]})

    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(side_effect=handler)

    tools = AggregatorTools(client)
    result = await tools.new_customers_today({"date": "2026-05-22", "branchCodeList": [1]})

    assert result["todayCustomerCount"] == 2
    assert result["newCustomerCount"] == 1
    assert result["customers"][0]["customerCode"] == 10


@pytest.mark.asyncio
@respx.mock
async def test_daily_dashboard_returns_partial_errors(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={"items": [
            {"orderCode": 1, "customerName": "A", "statusOrder": "Blocked", "totalAmountOrder": 100}
        ]})
    )
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/accounts-receivable/v2/documents/search").mock(
        return_value=Response(404, json={})
    )
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/accounts-payable/v2/duplicates/search").mock(
        return_value=Response(400, json=[{"message": "bad filter"}])
    )

    tools = AggregatorTools(client)
    result = await tools.daily_dashboard({"date": "2026-05-22", "branchCodeList": [1]})

    assert result["sales"]["totalOrders"] == 1
    assert "error" in result["receivable"]
    assert "error" in result["payable"]


@pytest.mark.asyncio
@respx.mock
async def test_stock_available_maps_finished_product_kind(client):
    _mock_token()

    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/balances/search").mock(
        return_value=Response(200, json={"items": [
            {
                "productCode": 14679,
                "productName": "LENCOL ELASTICO CANTEIRO DE FLORES CASAL",
                "colorName": "CANTEIRO DE FLORES",
                "sizeName": "CASAL",
                "balances": [{"stock": 8, "salesOrder": 0}],
            },
            {
                "productCode": 1,
                "productName": "SEM ESTOQUE",
                "balances": [{"stock": 0}],
            },
        ], "hasNext": False})
    )

    tools = AggregatorTools(client)
    result = await tools.stock_available({"branchCode": 1, "productKind": "finished", "minStock": 1})

    body = json.loads(route.calls.last.request.content)
    assert body["filter"]["branchInfo"] == {
        "branchCode": 1,
        "isActive": True,
        "isFinishedProduct": True,
        "isRawMaterial": False,
        "isBulkMaterial": False,
    }
    assert result["productKind"] == "finished"
    assert result["onlyActive"] is True
    assert result["totalSkus"] == 1
    assert result["pageStats"]["pages"] == 1
    assert result["products"][0]["productCode"] == 14679
