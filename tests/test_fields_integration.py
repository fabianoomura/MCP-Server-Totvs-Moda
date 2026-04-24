"""
Integration test: fields parameter on a real tool.

Demonstrates the pattern that all search tools should adopt in v2.5.
"""
import json
import sys
import types
import pytest
import respx
from httpx import Response

from tools._fields import apply_fields

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
            json={"access_token": "fake", "expires_in": 3600, "token_type": "Bearer"},
        )
    )


@pytest.mark.asyncio
@respx.mock
async def test_search_orders_with_fields_returns_reduced_response(client):
    """When fields is passed, response is trimmed."""
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={
            "items": [
                {
                    "orderCode": 1, "orderDate": "2026-04-01", "branchCode": 1,
                    "customerCode": 100, "customerName": "Alice",
                    "customerCpfCnpj": "12345", "orderStatus": "BillingReleased",
                    "totalValue": 500.0, "representativeCode": 10,
                    "items": [
                        {"productCode": 1, "name": "A", "quantity": 2,
                         "price": 50, "discount": 0, "sku": "A-M"},
                    ],
                }
            ],
            "totalHits": 1,
        })
    )

    from tools.sales_order import SalesOrderTools
    tools = SalesOrderTools(client)

    full = await tools.search_orders({
        "startOrderDate": "2026-04-01",
        "endOrderDate": "2026-04-30",
    })
    full_size = len(json.dumps(full))

    raw = await tools.search_orders({
        "startOrderDate": "2026-04-01",
        "endOrderDate": "2026-04-30",
    })
    trimmed = apply_fields(raw, {"fields": ["orderCode", "customerName", "totalValue"]})
    trimmed_size = len(json.dumps(trimmed))

    assert trimmed["items"][0] == {
        "orderCode": 1, "customerName": "Alice", "totalValue": 500.0,
    }
    assert trimmed["totalHits"] == 1
    assert trimmed_size < full_size * 0.4


@pytest.mark.asyncio
@respx.mock
async def test_search_orders_with_nested_fields(client):
    """fields supports nested paths like items.productCode."""
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={
            "items": [
                {
                    "orderCode": 1, "branchCode": 1,
                    "items": [
                        {"productCode": 100, "name": "A", "quantity": 2, "price": 50, "discount": 0},
                        {"productCode": 200, "name": "B", "quantity": 1, "price": 150, "discount": 10},
                    ],
                }
            ],
            "totalHits": 1,
        })
    )

    from tools.sales_order import SalesOrderTools
    tools = SalesOrderTools(client)

    raw = await tools.search_orders({
        "startOrderDate": "2026-04-01",
        "endOrderDate": "2026-04-30",
    })
    trimmed = apply_fields(raw, {"fields": [
        "orderCode", "items.productCode", "items.quantity"
    ]})

    order = trimmed["items"][0]
    assert order["orderCode"] == 1
    assert "branchCode" not in order
    assert len(order["items"]) == 2
    assert order["items"][0] == {"productCode": 100, "quantity": 2}
    assert "name" not in order["items"][0]
    assert "price" not in order["items"][0]
