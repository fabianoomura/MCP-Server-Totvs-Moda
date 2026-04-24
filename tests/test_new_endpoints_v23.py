"""
Contract tests for all v2.3.0 new endpoints.

Each test verifies:
- Correct HTTP method
- Correct URL
- Required fields validated
- Body shape matches TOTVS swagger

Total: 15 new endpoints × 1-2 tests each = 20 tests
"""
import json
import pytest
import respx
from httpx import Response

from tools.sales_order import SalesOrderTools
from tools.product import ProductTools
from tools.accounts_receivable import AccountsReceivableTools

from conftest import TOTVS_BASE, TOKEN_URL


def _mock_token():
    return respx.post(TOKEN_URL).mock(
        return_value=Response(
            200,
            json={"access_token": "fake-token", "expires_in": 3600, "token_type": "Bearer"},
        )
    )


def _body(route):
    """Helper: last call's JSON body."""
    return json.loads(route.calls.last.request.content)


# ════════════════════════════════════════════════════════════════════════════
# SALES ORDER — 10 new endpoints
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_add_order_items_posts_to_items_endpoint(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/items").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.add_order_items({
        "branchCode": 1,
        "orderCode": 12345,
        "items": [{"productCode": 10001, "productSku": "SKU-M", "quantity": 2, "price": 99.90}],
    })

    assert route.called
    body = _body(route)
    assert body["branchCode"] == 1
    assert body["orderCode"] == 12345
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_add_order_items_requires_items(client):
    tools = SalesOrderTools(client)
    with pytest.raises(ValueError, match="'items' é obrigatório"):
        await tools.add_order_items({"branchCode": 1, "orderCode": 1})


@pytest.mark.asyncio
@respx.mock
async def test_remove_order_item_uses_DELETE(client):
    _mock_token()
    route = respx.delete(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/items").mock(
        return_value=Response(204)
    )

    tools = SalesOrderTools(client)
    await tools.remove_order_item({
        "branchCode": 1, "orderCode": 12345, "productCode": 10001, "productSku": "SKU-M",
    })

    assert route.called
    # DELETE sends via query params — must be PascalCase per swagger
    qs = dict(route.calls.last.request.url.params)
    assert qs["BranchCode"] == "1"
    assert qs["OrderCode"] == "12345"
    assert qs["ProductCode"] == "10001"
    assert qs["ProductSku"] == "SKU-M"


@pytest.mark.asyncio
@respx.mock
async def test_cancel_order_items(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/cancel-items").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.cancel_order_items({
        "branchCode": 1, "orderCode": 12345,
        "items": [{"productCode": 10001, "productSku": "SKU-M", "quantityToCancel": 1}],
    })

    assert route.called
    body = _body(route)
    assert body["items"][0]["quantityToCancel"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_change_order_item_quantity(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/quantity-items").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.change_order_item_quantity({
        "orderId": "ORD-ABC-123",
        "items": [{"productCode": 10001, "newQuantity": 5}],
    })

    assert route.called
    body = _body(route)
    assert body["orderId"] == "ORD-ABC-123"
    assert "branchCode" not in body  # orderId is exclusive
    assert body["items"][0]["newQuantity"] == 5


@pytest.mark.asyncio
@respx.mock
async def test_update_order_items_additional(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/additional-items").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.update_order_items_additional({
        "branchCode": 1, "orderCode": 12345,
        "items": [{"productCode": 10001, "customerOrderCode": 99}],
    })

    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_add_order_observation(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/observations-order").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.add_order_observation({
        "branchCode": 1, "orderCode": 12345,
        "observation": "Entregar na portaria",
        "visualizationType": "Delivery",
    })

    assert route.called
    body = _body(route)
    assert body["observation"] == "Entregar na portaria"
    assert body["visualizationType"] == "Delivery"


@pytest.mark.asyncio
async def test_add_order_observation_requires_text(client):
    tools = SalesOrderTools(client)
    with pytest.raises(ValueError, match="'observation' é obrigatório"):
        await tools.add_order_observation({"branchCode": 1, "orderCode": 1})


@pytest.mark.asyncio
@respx.mock
async def test_update_order_shipping(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/shipping-order").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.update_order_shipping({
        "branchCode": 1, "orderCode": 12345,
        "shippingCompanyCode": 999,
        "freightType": "CIF",
        "freightValue": 15.00,
    })

    assert route.called
    body = _body(route)
    assert body["shippingCompanyCode"] == 999
    assert body["freightType"] == "CIF"


@pytest.mark.asyncio
@respx.mock
async def test_update_order_additional(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/additional-order").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.update_order_additional({
        "branchCode": 1, "orderCode": 12345,
        "trackingId": "BR123456789",
        "ecommerceStage": "Shipped",
    })

    assert route.called
    body = _body(route)
    assert body["trackingId"] == "BR123456789"
    assert body["ecommerceStage"] == "Shipped"


@pytest.mark.asyncio
@respx.mock
async def test_search_batch_items_uses_GET_with_query(client):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/batch-items").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = SalesOrderTools(client)
    await tools.search_batch_items({
        "status": "Pending",
        "startChangeDate": "2026-04-01T00:00:00",
        "endChangeDate": "2026-04-30T23:59:59",
    })

    assert route.called
    qs = dict(route.calls.last.request.url.params)
    assert qs["Status"] == "Pending"
    assert qs["StartChangeDate"] == "2026-04-01T00:00:00"
    assert qs["EndChangeDate"] == "2026-04-30T23:59:59"


@pytest.mark.asyncio
@respx.mock
async def test_create_order_relationship_counts(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/relationship-counts").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.create_order_relationship_counts({
        "branchCode": 1, "orderCode": 12345,
        "counts": [{"countCode": 999}],
    })

    assert route.called
    body = _body(route)
    assert body["counts"] == [{"countCode": 999}]


# ════════════════════════════════════════════════════════════════════════════
# PRODUCT — 3 new endpoints
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_update_barcode(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/barcodes/update").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = ProductTools(client)
    await tools.update_barcode({
        "productCode": 10001, "oldBarcode": "789123456789", "newBarcode": "789123456790",
    })

    assert route.called
    body = _body(route)
    assert body["newBarcode"] == "789123456790"


@pytest.mark.asyncio
@respx.mock
async def test_create_reference(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/references").mock(
        return_value=Response(201, json={"referenceId": 99})
    )

    tools = ProductTools(client)
    await tools.create_reference({
        "referenceCode": "REF-NEW-01",
        "description": "Nova Referência",
        "categoryCode": 1,
    })

    assert route.called
    body = _body(route)
    assert body["referenceCode"] == "REF-NEW-01"


@pytest.mark.asyncio
@respx.mock
async def test_create_classification_type(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/classifications").mock(
        return_value=Response(201, json={"ok": True})
    )

    tools = ProductTools(client)
    await tools.create_classification_type({
        "typeCode": 999,
        "description": "Nova Classificação",
    })

    assert route.called
    body = _body(route)
    assert body["typeCode"] == 999


# ════════════════════════════════════════════════════════════════════════════
# ACCOUNTS RECEIVABLE — 2 new endpoints (completes module)
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_move_gift_check(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/accounts-receivable/v2/gift-check-movements").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = AccountsReceivableTools(client)
    await tools.move_gift_check({
        "value": 50.00,
        "branchCode": 1, "customerCode": 100, "barCode": "GC12345",
    })

    assert route.called
    body = _body(route)
    assert body["value"] == 50.00
    assert body["barCode"] == "GC12345"


@pytest.mark.asyncio
async def test_move_gift_check_requires_value(client):
    tools = AccountsReceivableTools(client)
    with pytest.raises(ValueError, match="'value' é obrigatório"):
        await tools.move_gift_check({"branchCode": 1})


@pytest.mark.asyncio
@respx.mock
async def test_upsert_invoice_commission(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/accounts-receivable/v2/comission").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = AccountsReceivableTools(client)
    await tools.upsert_invoice_commission({
        "branchCode": 1,
        "customerCode": 100,
        "receivableCode": 5000,
        "installments": [{"installmentCode": 1, "commissionedCode": 99, "commissionedPercentage": 3.5}],
    })

    assert route.called
    body = _body(route)
    assert body["receivableCode"] == 5000
    assert body["installments"][0]["commissionedPercentage"] == 3.5


@pytest.mark.asyncio
async def test_upsert_invoice_commission_requires_receivable(client):
    tools = AccountsReceivableTools(client)
    with pytest.raises(ValueError, match="'receivableCode' é obrigatório"):
        await tools.upsert_invoice_commission({
            "customerCode": 100,
            "installments": [{"installmentCode": 1}],
        })


@pytest.mark.asyncio
async def test_upsert_invoice_commission_requires_installments(client):
    tools = AccountsReceivableTools(client)
    with pytest.raises(ValueError, match="'installments' é obrigatório"):
        await tools.upsert_invoice_commission({
            "customerCode": 100,
            "receivableCode": 5000,
        })


@pytest.mark.asyncio
async def test_upsert_invoice_commission_requires_customer(client):
    tools = AccountsReceivableTools(client)
    with pytest.raises(ValueError, match="customerCode OU customerCpfCnpj"):
        await tools.upsert_invoice_commission({
            "receivableCode": 5000,
            "installments": [{"installmentCode": 1}],
        })
