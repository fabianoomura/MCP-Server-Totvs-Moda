"""
Tests for the opt-in open/settled classification on accounts receivable
(roadmap #2).
"""
import pytest
import respx
from httpx import Response

from tools.accounts_receivable import AccountsReceivableTools

TOTVS_BASE = "https://totvs.test:9443"
RECV = f"{TOTVS_BASE}/api/totvsmoda/accounts-receivable/v2"


@pytest.mark.asyncio
@respx.mock
async def test_receivable_status_flags_and_summary(client, token_route):
    token_route()
    respx.post(f"{RECV}/documents/search").mock(
        return_value=Response(200, json={"items": [
            {"receivableCode": 1, "installmentValue": 100.0, "paidValue": 0, "settlementDate": None},
            {"receivableCode": 2, "installmentValue": 200.0, "paidValue": 200.0, "settlementDate": "2026-06-16"},
            {"receivableCode": 3, "installmentValue": 50.0, "paidValue": 0, "settlementDate": None},
        ]})
    )
    tools = AccountsReceivableTools(client)
    out = await tools.search_documents({"branchCodeList": [1], "withStatusFlags": True})

    items = out["items"]
    assert items[0]["isOpen"] is True
    assert items[0]["openValue"] == 100.0
    assert items[1]["isSettled"] is True
    assert items[1]["isOpen"] is False
    assert out["receivableSummary"]["open"] == {"count": 2, "value": 150.0}
    assert out["receivableSummary"]["settled"] == {"count": 1, "value": 200.0}


@pytest.mark.asyncio
@respx.mock
async def test_receivable_without_flags_unchanged(client, token_route):
    token_route()
    respx.post(f"{RECV}/documents/search").mock(
        return_value=Response(200, json={"items": [
            {"receivableCode": 1, "installmentValue": 100.0, "paidValue": 0},
        ]})
    )
    tools = AccountsReceivableTools(client)
    out = await tools.search_documents({"branchCodeList": [1]})

    assert "isOpen" not in out["items"][0]
    assert "receivableSummary" not in out
