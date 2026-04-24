"""
Shared pytest fixtures.
"""
import os
import sys
import types
import pytest
import pytest_asyncio
import respx
from httpx import Response

from totvs_client import TotvsClient


TOTVS_BASE = "https://totvs.test:9443"
TOKEN_URL = f"{TOTVS_BASE}/api/totvsmoda/authorization/v2/token"


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch):
    """Ensure deterministic env for all tests."""
    monkeypatch.setenv("TOTVS_TLS_VERIFY", "false")
    monkeypatch.setenv("TOTVS_MAX_RETRIES", "2")
    monkeypatch.setenv("TOTVS_TIMEOUT", "5")


@pytest.fixture(autouse=True)
def fake_context_cache_global(monkeypatch, request):
    """Provide a default context_cache with branches=[1] for all tests.

    Tests that need a specific cache configuration can override this fixture
    within their own module (like test_defaults.py does).

    This autouse fixture is skipped for tests that explicitly define their
    own fake_context_cache — pytest's closest-scope rule handles that.
    """
    # Don't override if the test module already defines its own
    if "fake_context_cache" in request.fixturenames and request.fixturename != "fake_context_cache_global":
        return

    fake = types.ModuleType("context_cache")
    fake.CACHE = {"branches": [1]}
    monkeypatch.setitem(sys.modules, "context_cache", fake)
    return fake


@pytest_asyncio.fixture
async def client():
    """Fresh TotvsClient per test."""
    c = TotvsClient(
        base_url=TOTVS_BASE,
        client_id="test_id",
        client_secret="test_secret",
        username="test_user",
        password="test_pass",
    )
    yield c
    await c.aclose()


@pytest.fixture
def token_route():
    """Sets up a respx route that satisfies the OAuth2 token endpoint."""
    def _setup(expires_in: int = 3600):
        return respx.post(TOKEN_URL).mock(
            return_value=Response(
                200,
                json={
                    "access_token": "fake-token-xyz",
                    "expires_in": expires_in,
                    "token_type": "Bearer",
                },
            )
        )
    return _setup
