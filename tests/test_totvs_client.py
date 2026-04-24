"""
Tests for totvs_client.py — the core HTTP layer.
"""
import pytest
import respx
from httpx import Response, TimeoutException

from totvs_client import TotvsApiError, TotvsAuthError

from conftest import TOTVS_BASE, TOKEN_URL


def _mock_token():
    return respx.post(TOKEN_URL).mock(
        return_value=Response(
            200,
            json={"access_token": "fake-token", "expires_in": 3600, "token_type": "Bearer"},
        )
    )


# ── AUTH ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_token_is_acquired_on_first_call(client):
    token = _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/test").mock(
        return_value=Response(200, json={"ok": True})
    )
    result = await client.get("/api/totvsmoda/test")
    assert result == {"ok": True}
    assert token.called
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_token_is_cached_across_calls(client):
    token = _mock_token()
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/a").mock(return_value=Response(200, json={}))
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/b").mock(return_value=Response(200, json={}))
    await client.get("/api/totvsmoda/a")
    await client.get("/api/totvsmoda/b")
    assert token.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_auth_failure_raises_totvs_auth_error(client):
    respx.post(TOKEN_URL).mock(return_value=Response(401, json={"error": "invalid_grant"}))
    with pytest.raises(TotvsAuthError):
        await client.get("/api/totvsmoda/anything")


# ── REACTIVE 401 ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_401_triggers_reauth_and_retry(client):
    token = _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/resource").mock(
        side_effect=[
            Response(401, json={"error": "token_invalid"}),
            Response(200, json={"data": "ok"}),
        ]
    )
    result = await client.get("/api/totvsmoda/resource")
    assert result == {"data": "ok"}
    assert route.call_count == 2
    assert token.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_401_is_retried_only_once(client):
    _mock_token()
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/resource").mock(
        return_value=Response(401, json={"messages": [{"code": "Unauthorized", "message": "denied"}]})
    )
    with pytest.raises(TotvsApiError) as exc:
        await client.get("/api/totvsmoda/resource")
    assert exc.value.status_code == 401


# ── RETRY on 5xx ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_5xx_is_retried_with_backoff(client, monkeypatch):
    import totvs_client as tc
    monkeypatch.setattr(tc, "DEFAULT_BACKOFF_BASE", 0.0)
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/flaky").mock(
        side_effect=[
            Response(503, text="Service Unavailable"),
            Response(200, json={"recovered": True}),
        ]
    )
    result = await client.get("/api/totvsmoda/flaky")
    assert result == {"recovered": True}
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_5xx_exhausts_retries_and_raises(client, monkeypatch):
    import totvs_client as tc
    monkeypatch.setattr(tc, "DEFAULT_BACKOFF_BASE", 0.0)
    _mock_token()
    respx.get(f"{TOTVS_BASE}/api/totvsmoda/broken").mock(
        return_value=Response(500, text="Internal Server Error")
    )
    with pytest.raises(TotvsApiError) as exc:
        await client.get("/api/totvsmoda/broken")
    assert exc.value.status_code == 500


@pytest.mark.asyncio
@respx.mock
async def test_network_error_is_retried(client, monkeypatch):
    import totvs_client as tc
    monkeypatch.setattr(tc, "DEFAULT_BACKOFF_BASE", 0.0)
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/slow").mock(
        side_effect=[
            TimeoutException("timeout"),
            Response(200, json={"fast_now": True}),
        ]
    )
    result = await client.get("/api/totvsmoda/slow")
    assert result == {"fast_now": True}
    assert route.call_count == 2


# ── STRUCTURED ERRORS ───────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_error_code_preserved_for_not_found(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/update").mock(
        return_value=Response(
            400,
            json={"messages": [{"code": "NotFound", "message": "ProductCode 123 not found", "severity": "Error"}]},
        )
    )
    with pytest.raises(TotvsApiError) as exc_info:
        await client.post("/api/totvsmoda/update", {"productCode": 123})
    exc = exc_info.value
    assert exc.status_code == 400
    assert exc.has_code("NotFound") is True
    assert exc.has_code("AlreadyExist") is False


@pytest.mark.asyncio
@respx.mock
async def test_error_code_preserved_for_already_exist(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/create").mock(
        return_value=Response(
            400,
            json={
                "messages": [
                    {"code": "AlreadyExist", "message": "ProductCode 1 TypeCode 11 already exist", "severity": "Error"},
                    {"code": "AlreadyExist", "message": "ProductCode 2 TypeCode 11 already exist", "severity": "Error"},
                ]
            },
        )
    )
    with pytest.raises(TotvsApiError) as exc_info:
        await client.post("/api/totvsmoda/create", {})
    assert exc_info.value.has_code("AlreadyExist") is True


@pytest.mark.asyncio
@respx.mock
async def test_unstructured_error_fallback(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/weird").mock(
        return_value=Response(400, text="NotFound: unknown resource")
    )
    with pytest.raises(TotvsApiError) as exc_info:
        await client.post("/api/totvsmoda/weird", {})
    assert exc_info.value.has_code("NotFound") is True


# ── UPSERT ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_upsert_uses_update_when_record_exists(client):
    _mock_token()
    update_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/values/update").mock(
        return_value=Response(200, json={"ok": True})
    )
    create_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/values/create")
    result = await client.upsert(
        update_path="/api/totvsmoda/values/update",
        create_path="/api/totvsmoda/values/create",
        body={"productCode": 123},
    )
    assert result["operation"] == "updated"
    assert result["result"] == {"ok": True}
    assert update_route.called
    assert not create_route.called


@pytest.mark.asyncio
@respx.mock
async def test_upsert_falls_back_to_create_on_not_found(client):
    _mock_token()
    update_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/values/update").mock(
        return_value=Response(400, json={"messages": [{"code": "NotFound", "message": "doesnt exist"}]})
    )
    create_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/values/create").mock(
        return_value=Response(201, json={"created_id": 999})
    )
    result = await client.upsert(
        update_path="/api/totvsmoda/values/update",
        create_path="/api/totvsmoda/values/create",
        body={"productCode": 123},
    )
    assert result["operation"] == "created"
    assert result["result"] == {"created_id": 999}
    assert update_route.called
    assert create_route.called


@pytest.mark.asyncio
@respx.mock
async def test_upsert_raises_on_non_not_found_error(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/values/update").mock(
        return_value=Response(400, json={"messages": [{"code": "ValidationError", "message": "bad data"}]})
    )
    create_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/values/create")
    with pytest.raises(TotvsApiError) as exc:
        await client.upsert(
            update_path="/api/totvsmoda/values/update",
            create_path="/api/totvsmoda/values/create",
            body={},
        )
    assert exc.value.has_code("ValidationError")
    assert not create_route.called


# ── HTTP METHODS ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_put_method_works(client):
    """PUT /data used by update_product_data — bug fix from Phase 1."""
    _mock_token()
    route = respx.put(f"{TOTVS_BASE}/api/totvsmoda/product/v2/data").mock(
        return_value=Response(200, json={"updated": True})
    )
    await client.put("/api/totvsmoda/product/v2/data", {"productCode": 1})
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_delete_method_works(client):
    _mock_token()
    route = respx.delete(f"{TOTVS_BASE}/api/totvsmoda/resource").mock(
        return_value=Response(204)
    )
    result = await client.delete("/api/totvsmoda/resource", params={"id": 1})
    assert route.called
    assert result["success"] is True
