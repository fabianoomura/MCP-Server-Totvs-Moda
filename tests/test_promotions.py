"""
Tests for promotion tools: search_promotions (GET /promotion) and the
corrected update_promotion_price (POST /promotion-values/update).
"""
import json

import pytest
import respx
from httpx import Response

from tools.product import ProductTools

TOTVS_BASE = "https://totvs.test:9443"
PROD = f"{TOTVS_BASE}/api/totvsmoda/product/v2"


@pytest.mark.asyncio
@respx.mock
async def test_search_promotions_get_with_pascal_params(client, token_route):
    token_route()
    route = respx.get(f"{PROD}/promotion").mock(return_value=Response(200, json={"items": []}))
    tools = ProductTools(client)
    await tools.search_promotions({"branchCode": 1, "status": "Open", "promotionCode": 50})

    assert route.called
    params = route.calls.last.request.url.params
    assert params["BranchCode"] == "1"
    assert params["Status"] == "Open"
    assert params["PromotionCode"] == "50"


@pytest.mark.asyncio
@respx.mock
async def test_update_promotion_simple_mode_body(client, token_route):
    token_route()
    route = respx.post(f"{PROD}/promotion-values/update").mock(
        return_value=Response(200, json={"ok": True})
    )
    tools = ProductTools(client)
    await tools.update_promotion_price({
        "branchCode": 1, "promotionCode": 50, "productCode": 13965, "promotionValue": 337,
    })
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "branchCode": 1,
        "promotionCode": 50,
        "items": [{"productCode": 13965, "promotionValue": 337}],
    }


@pytest.mark.asyncio
@respx.mock
async def test_update_promotion_batch_mode_body(client, token_route):
    token_route()
    route = respx.post(f"{PROD}/promotion-values/update").mock(
        return_value=Response(200, json={"ok": True})
    )
    tools = ProductTools(client)
    await tools.update_promotion_price({
        "branchCode": 1, "promotionCode": 50,
        "items": [{"productCode": 1, "promotionValue": 10}, {"productCode": 2, "promotionValue": 20}],
    })
    body = json.loads(route.calls.last.request.content)
    assert body["promotionCode"] == 50
    assert body["items"] == [
        {"productCode": 1, "promotionValue": 10},
        {"productCode": 2, "promotionValue": 20},
    ]


@pytest.mark.asyncio
@respx.mock
async def test_update_promotion_price_alias(client, token_route):
    """promotionPrice is accepted as an alias of promotionValue (compat)."""
    token_route()
    route = respx.post(f"{PROD}/promotion-values/update").mock(
        return_value=Response(200, json={"ok": True})
    )
    tools = ProductTools(client)
    await tools.update_promotion_price({
        "branchCode": 1, "promotionCode": 50, "productCode": 9, "promotionPrice": 99,
    })
    body = json.loads(route.calls.last.request.content)
    assert body["items"] == [{"productCode": 9, "promotionValue": 99}]
