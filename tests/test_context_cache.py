"""
Tests for context_cache v3.1.

Cobre:
- _load_price_and_cost_types descobre via produtos vendidos
- get_slim_context retorna só essencial
- get_full_context retorna tudo
- Resiliência: falhas parciais não quebram tudo
"""
import pytest
import respx
from httpx import Response

import context_cache
from conftest import TOTVS_BASE, TOKEN_URL


def _mock_token():
    return respx.post(TOKEN_URL).mock(
        return_value=Response(200, json={
            "access_token": "fake", "expires_in": 3600, "token_type": "Bearer"
        })
    )


@pytest.fixture(autouse=True)
def reset_cache():
    """Reseta o cache global entre testes."""
    context_cache.CACHE = {}
    yield
    context_cache.CACHE = {}


# ── Slim mode vs full ──────────────────────────────────────────────────────

def test_slim_context_excludes_heavy_fields():
    """get_slim_context não deve trazer dados gigantes."""
    context_cache.CACHE = {
        "loadedAt": "2026-04-25T00:00:00Z",
        "branches": [1],
        "priceTypes": [{"priceCode": 1, "priceName": "VENDA"}],
        "costTypes": [],
        "operations": [{"code": i, "name": f"Op{i}"} for i in range(50)],
        "paymentConditions": [{"code": i, "name": f"Cond{i}"} for i in range(30)],
        "rawHugeData": "a" * 100000,  # 100KB de lixo
    }

    slim = context_cache.get_slim_context()

    assert "rawHugeData" not in slim
    assert len(slim["operations"]) == 5  # corta em 5
    assert len(slim["paymentConditions"]) == 5
    assert slim["branches"] == [1]
    assert slim["priceTypes"][0]["priceCode"] == 1


def test_full_context_includes_everything():
    """get_full_context retorna o cache inteiro."""
    context_cache.CACHE = {
        "branches": [1],
        "operations": [{"code": i} for i in range(50)],
        "extraData": "anything",
    }

    full = context_cache.get_full_context()
    assert len(full["operations"]) == 50
    assert full["extraData"] == "anything"


def test_slim_context_handles_empty_cache():
    """get_slim_context não deve quebrar se cache estiver vazio."""
    context_cache.CACHE = {}
    slim = context_cache.get_slim_context()

    assert slim["branches"] == []
    assert slim["priceTypes"] == []
    assert slim["operations"] == []


# ── Discovery de priceTypes/costTypes ──────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_discovery_finds_price_types_via_top_products(client, monkeypatch):
    """priceTypes deve ser descoberto via produtos vendidos recentemente."""
    _mock_token()
    monkeypatch.setenv("TOTVS_BRANCH_CODES", "1")

    # Mock orders search → 1 pedido com 2 produtos
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={
            "items": [{
                "orderCode": 1,
                "items": [
                    {"productCode": 100, "name": "A"},
                    {"productCode": 200, "name": "B"},
                ]
            }]
        })
    )

    # Mock prices search → revela priceCode 1 e 3 ativos
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/prices/search").mock(
        return_value=Response(200, json={
            "items": [
                {
                    "productCode": 100,
                    "prices": [
                        {"priceCode": 1, "priceName": "VAREJO", "price": 100},
                        {"priceCode": 3, "priceName": "ATACADO", "price": 80},
                    ]
                },
                {
                    "productCode": 200,
                    "prices": [
                        {"priceCode": 1, "priceName": "VAREJO", "price": 50},
                    ]
                },
            ]
        })
    )

    # Mock costs search → revela costCode 1
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/costs/search").mock(
        return_value=Response(200, json={
            "items": [
                {
                    "productCode": 100,
                    "costs": [
                        {"costCode": 1, "costName": "PADRAO", "cost": 40},
                    ]
                },
            ]
        })
    )

    # Mock outros endpoints (operations, payment_conditions) — só pra não falhar
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/general/v2/operations").mock(
        return_value=Response(200, json={"items": []})
    )
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/general/v2/payment-conditions").mock(
        return_value=Response(200, json={"items": []})
    )

    cache = await context_cache.load_context(client)

    # priceTypes deve ter 2 entradas únicas (1 e 3), ordenadas
    assert len(cache["priceTypes"]) == 2
    assert cache["priceTypes"][0]["priceCode"] == 1
    assert cache["priceTypes"][0]["priceName"] == "VAREJO"
    assert cache["priceTypes"][1]["priceCode"] == 3
    assert cache["priceTypes"][1]["priceName"] == "ATACADO"

    # costTypes deve ter 1 entrada
    assert len(cache["costTypes"]) == 1
    assert cache["costTypes"][0]["costCode"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_discovery_resilient_to_no_orders(client, monkeypatch):
    """Se nenhum pedido recente, priceTypes fica vazio mas não quebra."""
    _mock_token()
    monkeypatch.setenv("TOTVS_BRANCH_CODES", "1")

    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={"items": []})
    )
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/general/v2/operations").mock(
        return_value=Response(200, json={"items": []})
    )
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/general/v2/payment-conditions").mock(
        return_value=Response(200, json={"items": []})
    )

    cache = await context_cache.load_context(client)

    # Não deve falhar, só devolver vazio
    assert cache["priceTypes"] == []
    assert cache["costTypes"] == []
    assert cache["branches"] == [1]


@pytest.mark.asyncio
@respx.mock
async def test_load_context_resilient_to_endpoint_failures(client, monkeypatch):
    """Falha em um endpoint não deve quebrar o load inteiro."""
    _mock_token()
    monkeypatch.setenv("TOTVS_BRANCH_CODES", "1")

    # operations falha
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/general/v2/operations").mock(
        return_value=Response(500, json={"error": "boom"})
    )
    # payment conditions falha
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/general/v2/payment-conditions").mock(
        return_value=Response(500, json={"error": "boom"})
    )
    # orders ok mas vazio
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={"items": []})
    )

    cache = await context_cache.load_context(client)

    # branches vem do env, sempre carrega
    assert cache["branches"] == [1]
    # outros vazios mas estrutura presente
    assert "operations" in cache
    assert "priceTypes" in cache


@pytest.mark.asyncio
@respx.mock
async def test_branches_from_env_var(client, monkeypatch):
    """TOTVS_BRANCH_CODES com múltiplas filiais é parseado corretamente."""
    _mock_token()
    monkeypatch.setenv("TOTVS_BRANCH_CODES", "1,2,5")

    respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={"items": []})
    )
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/general/v2/operations").mock(
        return_value=Response(200, json={"items": []})
    )
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/general/v2/payment-conditions").mock(
        return_value=Response(200, json={"items": []})
    )

    cache = await context_cache.load_context(client)
    assert cache["branches"] == [1, 2, 5]
