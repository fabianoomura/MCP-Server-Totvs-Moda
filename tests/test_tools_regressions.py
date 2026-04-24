"""
Regression tests for bugs found in Phase 1 review + contract tests for tools.

Every bug we fixed has a test here — if someone reintroduces the bug,
CI catches it before it reaches production.
"""
import pytest
import respx
from httpx import Response

from tools.sales_order import SalesOrderTools
from tools.product import ProductTools
from tools.accounts_receivable import AccountsReceivableTools
from tools.voucher import VoucherTools
from tools.image import ImageTools
from tools.logistics import LogisticsTools
from tools.convenience import ConvenienceTools

from conftest import TOTVS_BASE, TOKEN_URL


def _mock_token():
    return respx.post(TOKEN_URL).mock(
        return_value=Response(
            200,
            json={"access_token": "fake-token", "expires_in": 3600, "token_type": "Bearer"},
        )
    )


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 BUG #1 — update_product_data must use PUT, not POST
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_update_product_data_uses_PUT_not_POST(client):
    """Regression: swagger specifies PUT /product/v2/data — POST returns 405."""
    _mock_token()
    put_route = respx.put(f"{TOTVS_BASE}/api/totvsmoda/product/v2/data").mock(
        return_value=Response(200, json={"updated": True})
    )
    post_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/data")

    tools = ProductTools(client)
    await tools.update_product_data({"productCode": 123, "description": "x"})

    assert put_route.called, "Must use PUT"
    assert not post_route.called, "Must NOT use POST"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 BUG #2 — image endpoints must match swagger
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_search_product_images_uses_product_search_endpoint(client):
    """Regression: old code used /product-images which doesn't exist.
    Real endpoint is /product/search."""
    _mock_token()
    wrong_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/image/v2/product-images")
    right_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/image/v2/product/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = ImageTools(client)
    await tools.search_product_images({"referenceCode": "REF-1"})

    assert right_route.called
    assert not wrong_route.called


@pytest.mark.asyncio
@respx.mock
async def test_upload_product_image_uses_product_endpoint(client):
    """Regression: real endpoint is POST /image/v2/product, not /product-images."""
    _mock_token()
    right_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/image/v2/product").mock(
        return_value=Response(201, json={"ok": True})
    )

    tools = ImageTools(client)
    await tools.upload_product_image({"imageBase64": "abc123"})

    assert right_route.called


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 BUG #3 — voucher search uses GET, not POST
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_search_voucher_uses_GET_not_POST(client):
    """Regression: swagger says GET /voucher/v2/search with query params."""
    _mock_token()
    post_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/voucher/v2/search")
    get_route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/voucher/v2/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = VoucherTools(client)
    await tools.search_voucher({"voucherCode": "ABC123"})

    assert get_route.called
    assert not post_route.called


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 BUG #4 — change_order_status uses statusOrder field + valid enum
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_change_order_status_sends_statusOrder_field(client):
    """Regression: old code sent 'newStatus' but swagger expects 'statusOrder'."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/change-status").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.change_order_status({
        "branchCode": 1,
        "orderCode": 12345,
        "statusOrder": "BillingReleased",
    })

    assert route.called
    sent_body = route.calls.last.request.content
    import json
    body = json.loads(sent_body)
    assert body.get("statusOrder") == "BillingReleased"
    assert "newStatus" not in body, "Field 'newStatus' must not be in the request"


@pytest.mark.asyncio
@respx.mock
async def test_change_order_status_accepts_legacy_newStatus_alias(client):
    """Backwards-compat: if caller passes old 'newStatus' key, it still works."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/change-status").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.change_order_status({
        "branchCode": 1,
        "orderCode": 12345,
        "newStatus": "Blocked",
    })

    import json
    body = json.loads(route.calls.last.request.content)
    assert body["statusOrder"] == "Blocked", "newStatus should be translated to statusOrder"


@pytest.mark.asyncio
async def test_change_order_status_requires_status(client):
    """If neither statusOrder nor newStatus provided, raise ValueError."""
    tools = SalesOrderTools(client)
    with pytest.raises(ValueError, match="statusOrder"):
        await tools.change_order_status({"branchCode": 1, "orderCode": 12345})


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 BUG #5 — change_charge_type requires customer identifier
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_change_charge_type_requires_customer_identifier(client):
    """If neither customerCode nor customerCpfCnpj provided, raise ValueError."""
    tools = AccountsReceivableTools(client)
    with pytest.raises(ValueError, match="customerCode OU customerCpfCnpj"):
        await tools.change_charge_type({
            "branchCode": 1,
            "receivableCode": 100,
            "installmentCode": 1,
            "chargeType": 2,
        })


@pytest.mark.asyncio
@respx.mock
async def test_change_charge_type_accepts_customer_code(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/accounts-receivable/v2/documents/change-charge-type").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = AccountsReceivableTools(client)
    await tools.change_charge_type({
        "branchCode": 1,
        "receivableCode": 100,
        "installmentCode": 1,
        "chargeType": 2,
        "customerCode": 999,
    })

    import json
    body = json.loads(route.calls.last.request.content)
    assert body["customerCode"] == 999
    assert "customerCpfCnpj" not in body


# ════════════════════════════════════════════════════════════════════════════
# NEW v2.1 — Logistics module
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_search_product_storage_endpoint(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/logistics/v2/product-storages/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = LogisticsTools(client)
    await tools.search_product_storage({"branchCode": 1, "productCodeList": [10001]})

    assert route.called
    import json
    body = json.loads(route.calls.last.request.content)
    assert body["filter"]["branchCode"] == 1
    assert body["filter"]["productCodeList"] == [10001]
    assert body["page"] == 1
    assert body["pageSize"] == 100


@pytest.mark.asyncio
@respx.mock
async def test_add_product_packaging_endpoint(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/logistics/v2/product-packagings/add-quantity").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = LogisticsTools(client)
    await tools.add_product_packaging({
        "branchCode": 1, "productCode": 10001, "packagingCode": 5, "quantity": 10
    })

    assert route.called


# ════════════════════════════════════════════════════════════════════════════
# NEW v2.1 — Convenience tools
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_search_customer_by_document_detects_CPF(client):
    """11 digits → route to /individuals/search."""
    _mock_token()
    pf_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/individuals/search").mock(
        return_value=Response(200, json={"items": []})
    )
    pj_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/legal-entities/search")

    tools = ConvenienceTools(client)
    result = await tools.search_customer_by_document({"document": "123.456.789-00"})

    assert pf_route.called
    assert not pj_route.called
    assert result["_documentType"] == "CPF"
    assert result["_documentClean"] == "12345678900"


@pytest.mark.asyncio
@respx.mock
async def test_search_customer_by_document_detects_CNPJ(client):
    """14 digits → route to /legal-entities/search."""
    _mock_token()
    pf_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/individuals/search")
    pj_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/legal-entities/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = ConvenienceTools(client)
    result = await tools.search_customer_by_document({"document": "12.345.678/0001-99"})

    assert not pf_route.called
    assert pj_route.called
    assert result["_documentType"] == "CNPJ"
    assert result["_documentClean"] == "12345678000199"


@pytest.mark.asyncio
async def test_search_customer_by_document_rejects_empty(client):
    tools = ConvenienceTools(client)
    with pytest.raises(ValueError, match="Documento inválido"):
        await tools.search_customer_by_document({"document": "abc/def"})


@pytest.mark.asyncio
@respx.mock
async def test_upsert_product_value_tries_update_first(client):
    _mock_token()
    update_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/update").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = ConvenienceTools(client)
    result = await tools.upsert_product_value({
        "branchCode": 1, "productCode": 10001, "valueCode": 1, "value": 99.90
    })

    assert result["operation"] == "updated"
    assert update_route.called


@pytest.mark.asyncio
@respx.mock
async def test_upsert_product_value_falls_back_to_create(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/update").mock(
        return_value=Response(400, json={"messages": [{"code": "NotFound", "message": "no such product value"}]})
    )
    create_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/create").mock(
        return_value=Response(201, json={"created": True})
    )

    tools = ConvenienceTools(client)
    result = await tools.upsert_product_value({
        "branchCode": 1, "productCode": 99999, "valueCode": 1, "value": 199.99
    })

    assert result["operation"] == "created"
    assert create_route.called


# ════════════════════════════════════════════════════════════════════════════
# CONTRACT — ensure request body matches TOTVS swagger expectations
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_search_orders_wraps_filter_in_body(client):
    """TOTVS expects {filter: {...}, page, pageSize} — flat args must be wrapped."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={"items": [], "totalHits": 0})
    )

    tools = SalesOrderTools(client)
    await tools.search_orders({
        "startOrderDate": "2026-04-01T00:00:00",
        "endOrderDate": "2026-04-30T23:59:59",
        "orderStatusList": ["Confirmado"],
        "page": 2,
        "pageSize": 50,
    })

    import json
    body = json.loads(route.calls.last.request.content)
    assert "filter" in body
    assert body["filter"]["startOrderDate"] == "2026-04-01T00:00:00"
    assert body["filter"]["orderStatusList"] == ["Confirmado"]
    assert body["page"] == 2
    assert body["pageSize"] == 50


@pytest.mark.asyncio
@respx.mock
async def test_cancel_order_sends_required_reason_code(client):
    """reasonCancellationCode is required per swagger."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/cancel").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.cancel_order({
        "branchCode": 1,
        "orderCode": 12345,
        "reasonCancellationCode": 99,
    })

    import json
    body = json.loads(route.calls.last.request.content)
    assert body["reasonCancellationCode"] == 99


@pytest.mark.asyncio
@respx.mock
async def test_product_search_prices_requires_priceCodeList(client):
    """prices/search requires priceCodeList — ValueError if missing."""
    tools = ProductTools(client)
    with pytest.raises(ValueError, match="priceCodeList"):
        await tools.search_prices({"branchCode": 1, "productCodeList": [10001]})


@pytest.mark.asyncio
@respx.mock
async def test_product_search_price_tables_requires_table_code(client):
    """price-tables/search requires priceTableCode — ValueError if missing."""
    tools = ProductTools(client)
    with pytest.raises(ValueError, match="priceTableCode"):
        await tools.search_price_tables({"branchCode": 1})
