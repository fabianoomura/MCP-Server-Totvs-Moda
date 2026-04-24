"""Tests for the aggregator tools — high-level composition."""
import sys
import types
import pytest
import respx
from httpx import Response

from tools.aggregators import AggregatorTools

from conftest import TOTVS_BASE, TOKEN_URL


@pytest.fixture(autouse=True)
def fake_context_cache(monkeypatch):
    """Fornece context_cache com filial padrão para os testes desse arquivo."""
    fake = types.ModuleType("context_cache")
    fake.CACHE = {"branches": [1]}
    monkeypatch.setitem(sys.modules, "context_cache", fake)
    yield fake


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
