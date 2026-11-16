"""
POST /production-order/v2/orders — inclusão de OP liberada na API.
O contrato tem pares mutuamente exclusivos; a tool rejeita antes de chamar a API.
"""

import json

import pytest
import respx
from httpx import Response

from conftest import TOTVS_BASE, TOKEN_URL

ORDERS_URL = f"{TOTVS_BASE}/api/totvsmoda/production-order/v2/orders"


def _mock_oauth():
    respx.post(TOKEN_URL).mock(
        return_value=Response(200, json={
            "access_token": "fake", "expires_in": 3600, "token_type": "Bearer"
        })
    )


def _order(**overrides):
    order = {
        "branchCode": 30,
        "cycleCode": 2022,
        "personCode": 17,
        "finalizationOperation": 8602,
        "rawMaterialRemovalOperation": 8600,
        "rawMaterialReturnOperation": 8601,
        "status": 10,
        "items": [{
            "productCode": 16970,
            "quantity": 10,
            "materials": [{"materialCode": 1008318, "quantityConsumption": 1}],
            "services": [{"serviceCode": 22, "quantity": 1, "value": 5.5}],
        }],
    }
    order.update(overrides)
    return order


def _tools(client):
    from tools.other_modules import ProductionOrderTools
    return ProductionOrderTools(client)


@pytest.mark.asyncio
@respx.mock
async def test_create_production_order_posts_full_contract(client):
    _mock_oauth()
    route = respx.post(ORDERS_URL).mock(return_value=Response(200, json={"orderCode": 1}))

    await _tools(client).create_production_order(_order(
        personOrderCode="1020",
        salesOrders=[{"branchCode": 30, "orderCode": 844}],
        classifications=[{"typeCode": 1, "classificationCode": "1"}],
        observations=[{"observation": "Teste"}],
        priority=None,
    ))

    body = json.loads(route.calls.last.request.content)
    assert body["cycleCode"] == 2022
    assert body["items"][0]["materials"] == [{"materialCode": 1008318, "quantityConsumption": 1}]
    assert body["salesOrders"] == [{"branchCode": 30, "orderCode": 844}]
    assert "priority" not in body


@pytest.mark.asyncio
@respx.mock
async def test_create_production_order_programming_by_code_defaults_branch(client):
    _mock_oauth()
    route = respx.post(ORDERS_URL).mock(return_value=Response(200, json={}))

    await _tools(client).create_production_order(_order(programming={"programmingCode": 3}))

    body = json.loads(route.calls.last.request.content)
    assert body["programming"] == {"programmingCode": 3, "branchCode": 30}


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_order, message", [
    (_order(items=[]), "items"),
    (_order(items=[{"quantity": 1}]), "productCode ou barCode"),
    (_order(items=[{"productCode": 1, "barCode": "X", "quantity": 1}]), "productCode ou barCode"),
    (_order(items=[{"productCode": 1, "quantity": 1, "materials": [
        {"materialCode": 2, "quantityConsumption": 1, "totalQuantityConsumption": 10}]}]),
     "quantityConsumption ou totalQuantityConsumption"),
    (_order(items=[{"productCode": 1, "quantity": 1, "materials": [
        {"materialCode": 2, "barCode": "Y", "quantityConsumption": 1}]}]),
     "materialCode ou barCode"),
    (_order(items=[{"productCode": 1, "quantity": 1, "services": [
        {"serviceCode": 22, "quantity": 1, "totalQuantity": 10}]}]),
     "quantity ou totalQuantity"),
    (_order(programming={"programmingCode": 3, "locations": [{"orderSequence": 1, "locationCode": 22}]}),
     "programming"),
])
@respx.mock
async def test_create_production_order_rejects_ambiguous_payload(client, bad_order, message):
    route = respx.post(ORDERS_URL).mock(return_value=Response(200, json={}))

    with pytest.raises(ValueError, match=message):
        await _tools(client).create_production_order(bad_order)

    assert not route.called


def test_create_production_order_is_flagged_as_write():
    import server
    assert "totvs_create_production_order" in server._write_tool_names()
