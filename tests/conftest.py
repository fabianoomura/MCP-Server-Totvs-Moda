"""
Shared fixtures and constants for TOTVS Moda MCP tests.
"""
import pytest
import pytest_asyncio
from totvs_client import TotvsClient

TOTVS_BASE = "http://test-totvs.local"
TOKEN_URL = f"{TOTVS_BASE}/api/totvsmoda/authorization/v2/token"


@pytest_asyncio.fixture
async def client():
    """TotvsClient apontando para servidor de teste (sem conexão real)."""
    return TotvsClient(
        base_url=TOTVS_BASE,
        client_id="test-client",
        client_secret="test-secret",
        username="test-user",
        password="test-pass",
    )
