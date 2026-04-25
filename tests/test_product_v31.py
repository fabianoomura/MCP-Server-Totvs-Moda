"""
Tests for v3.1 product module changes.

Cobre:
- update_product_price_only injects valueType="Price"
- update_product_cost injects valueType="Cost"
- Aceita aliases P/C
- update_product_simple usa endpoint PUT /products/{code}/{branchCode}
- update_product_data auto-roteia: simples vs batch
- Upsert (try update, fallback create) funciona com NotFound
"""
import json
import sys
import types
import pytest
import respx
from httpx import Response

# Importar fixtures globais via conftest
from conftest import TOTVS_BASE, TOKEN_URL


def _mock_token():
    return respx.post(TOKEN_URL).mock(
        return_value=Response(200, json={
            "access_token": "fake", "expires_in": 3600, "token_type": "Bearer"
        })
    )


# ── update_product_price_only ───────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_update_price_only_injects_Price(client):
    """price_only deve forçar valueType='Price' mesmo se LLM passar outra coisa."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/update").mock(
        return_value=Response(200, json={"ok": True})
    )

    from tools.product import ProductTools
    tools = ProductTools(client)

    result = await tools.update_product_price_only({
        "productCode": 10000,
        "branchCode": 1,
        "valueCode": 1,
        "value": 357.0,
    })

    assert route.called
    body = json.loads(route.calls.last.request.content)
    assert body["products"][0]["values"][0]["valueType"] == "Price"
    assert body["products"][0]["values"][0]["value"] == 357.0
    assert body["products"][0]["values"][0]["valueCode"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_update_cost_injects_Cost(client):
    """cost deve forçar valueType='Cost'."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/update").mock(
        return_value=Response(200, json={"ok": True})
    )

    from tools.product import ProductTools
    tools = ProductTools(client)

    await tools.update_product_cost({
        "productCode": 10000,
        "branchCode": 1,
        "valueCode": 1,
        "value": 100.0,
    })

    body = json.loads(route.calls.last.request.content)
    assert body["products"][0]["values"][0]["valueType"] == "Cost"


@pytest.mark.asyncio
@respx.mock
async def test_update_price_only_overrides_wrong_valueType(client):
    """Se LLM passa valueType='Cost' por engano, price_only força 'Price'."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/update").mock(
        return_value=Response(200, json={"ok": True})
    )

    from tools.product import ProductTools
    tools = ProductTools(client)

    # Modo lote com valueType errado
    await tools.update_product_price_only({
        "products": [{
            "productCode": 10000,
            "values": [{
                "branchCode": 1, "valueType": "Cost",  # ← errado!
                "valueCode": 1, "value": 357.0,
            }]
        }]
    })

    body = json.loads(route.calls.last.request.content)
    # Deve ter forçado Price, ignorando o Cost passado
    assert body["products"][0]["values"][0]["valueType"] == "Price"


@pytest.mark.asyncio
@respx.mock
async def test_upsert_fallback_to_create_on_not_found(client):
    """Se update retornar NotFound, deve cair pra create."""
    _mock_token()
    update_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/update").mock(
        return_value=Response(400, json={
            "errors": [{"code": "NotFound", "message": "Price not found",
                        "detailedMessage": "..."}]
        })
    )
    create_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/create").mock(
        return_value=Response(200, json={"created": True})
    )

    from tools.product import ProductTools
    tools = ProductTools(client)

    result = await tools.update_product_price_only({
        "productCode": 99999,  # produto novo, sem preço
        "branchCode": 1,
        "valueCode": 1,
        "value": 100.0,
    })

    # Deve ter chamado os dois
    assert update_route.called
    assert create_route.called
    # E retornado operation=created
    assert result["operation"] == "created"


# ── update_product_simple ───────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_update_product_simple_uses_path_params(client):
    """update_product_simple deve usar PUT /products/{code}/{branchCode}."""
    _mock_token()
    # productCode=10000, branchCode=1 → URL /products/10000/1
    route = respx.put(f"{TOTVS_BASE}/api/totvsmoda/product/v2/products/10000/1").mock(
        return_value=Response(200, json={"ok": True})
    )

    from tools.product import ProductTools
    tools = ProductTools(client)

    await tools.update_product_simple({
        "productCode": 10000,
        "branchCode": 1,
        "weight": 1.5,
    })

    assert route.called
    body = json.loads(route.calls.last.request.content)
    # productCode e branchCode NÃO devem aparecer no body (estão na URL)
    assert "productCode" not in body
    assert "branchCode" not in body
    # Mas o weight sim
    assert body["weight"] == 1.5


@pytest.mark.asyncio
@respx.mock
async def test_update_product_simple_supports_multiple_fields(client):
    """update_product_simple deve aceitar peso + NCM + flags juntos."""
    _mock_token()
    route = respx.put(f"{TOTVS_BASE}/api/totvsmoda/product/v2/products/10000/1").mock(
        return_value=Response(200, json={"ok": True})
    )

    from tools.product import ProductTools
    tools = ProductTools(client)

    await tools.update_product_simple({
        "productCode": 10000,
        "branchCode": 1,
        "weight": 2.5,
        "ncmCode": "94049000",
        "isInactive": False,
    })

    body = json.loads(route.calls.last.request.content)
    assert body["weight"] == 2.5
    assert body["ncmCode"] == "94049000"
    assert body["isInactive"] is False


# ── update_product_data — auto-roteamento ───────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_update_product_data_simple_mode_routes_to_simple_endpoint(client):
    """update_product_data com productCode (singular) deve ir pro endpoint simples."""
    _mock_token()
    simple_route = respx.put(
        f"{TOTVS_BASE}/api/totvsmoda/product/v2/products/10000/1"
    ).mock(return_value=Response(200, json={"ok": True}))

    from tools.product import ProductTools
    tools = ProductTools(client)

    await tools.update_product_data({
        "productCode": 10000,
        "branchCode": 1,
        "weight": 1.5,
    })

    assert simple_route.called
    body = json.loads(simple_route.calls.last.request.content)
    assert body["weight"] == 1.5


@pytest.mark.asyncio
@respx.mock
async def test_update_product_data_batch_mode_uses_filter_wrapper(client):
    """update_product_data com productCodeList deve ir pro endpoint batch."""
    _mock_token()
    batch_route = respx.put(
        f"{TOTVS_BASE}/api/totvsmoda/product/v2/data"
    ).mock(return_value=Response(200, json={"ok": True}))

    from tools.product import ProductTools
    tools = ProductTools(client)

    await tools.update_product_data({
        "productCodeList": [100, 200, 300],
        "weight": 1.5,
    })

    assert batch_route.called
    body = json.loads(batch_route.calls.last.request.content)
    # Modo batch tem wrapper "filter"
    assert "filter" in body
    assert body["filter"]["productCodeList"] == [100, 200, 300]
    # weight no nível raiz, fora do filter
    assert body["weight"] == 1.5


@pytest.mark.asyncio
@respx.mock
async def test_update_product_data_batch_requires_filter(client):
    """Modo batch sem filtro deve falhar com erro claro."""
    _mock_token()
    from tools.product import ProductTools
    tools = ProductTools(client)

    with pytest.raises(ValueError, match="filtro"):
        await tools.update_product_data({"weight": 1.5})


# ── Compat: update_product_price antigo ainda funciona ─────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_legacy_update_product_price_with_valueType_routes_correctly(client):
    """update_product_price (deprecada) com valueType='Cost' deve chamar update_product_cost."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/update").mock(
        return_value=Response(200, json={"ok": True})
    )

    from tools.product import ProductTools
    tools = ProductTools(client)

    await tools.update_product_price({
        "productCode": 10000,
        "branchCode": 1,
        "valueCode": 1,
        "value": 50.0,
        "valueType": "C",  # ← atalho 'C' deve virar 'Cost'
    })

    body = json.loads(route.calls.last.request.content)
    assert body["products"][0]["values"][0]["valueType"] == "Cost"


@pytest.mark.asyncio
@respx.mock
async def test_legacy_update_product_price_default_routes_to_price(client):
    """update_product_price sem valueType (None) deve assumir Price."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/update").mock(
        return_value=Response(200, json={"ok": True})
    )

    from tools.product import ProductTools
    tools = ProductTools(client)

    await tools.update_product_price({
        "productCode": 10000,
        "branchCode": 1,
        "valueCode": 1,
        "value": 50.0,
        # Sem valueType — deve assumir Price (preserva compat com chamadas antigas)
    })

    body = json.loads(route.calls.last.request.content)
    assert body["products"][0]["values"][0]["valueType"] == "Price"
