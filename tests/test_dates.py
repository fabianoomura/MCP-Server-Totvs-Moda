"""
Tests for tools/_dates.py — single-day range expansion (roadmap #4).
"""
import json

import pytest
import respx
from httpx import Response

from tools._dates import expand_equal_day, normalize_day_ranges
from tools.account_payable import AccountPayableTools

TOTVS_BASE = "https://totvs.test:9443"
PAYABLE = f"{TOTVS_BASE}/api/totvsmoda/accounts-payable/v2"


# ── unit ─────────────────────────────────────────────────────────────────────

def test_expand_equal_day_same_date():
    assert expand_equal_day("2026-06-16", "2026-06-16") == (
        "2026-06-16T00:00:00",
        "2026-06-16T23:59:59",
    )


def test_expand_equal_day_distinct_untouched():
    assert expand_equal_day("2026-06-16", "2026-06-17") == ("2026-06-16", "2026-06-17")


def test_expand_equal_day_with_time_untouched():
    pair = ("2026-06-16T08:00:00", "2026-06-16T08:00:00")
    assert expand_equal_day(*pair) == pair


def test_normalize_day_ranges_expired():
    out = normalize_day_ranges(
        {"startExpiredDate": "2026-06-16", "endExpiredDate": "2026-06-16"}
    )
    assert out["startExpiredDate"] == "2026-06-16T00:00:00"
    assert out["endExpiredDate"] == "2026-06-16T23:59:59"


def test_normalize_day_ranges_open_ended_untouched():
    out = normalize_day_ranges({"startIssueDate": "2026-06-16"})
    assert out["startIssueDate"] == "2026-06-16"


# ── integration: payable search expands the same-day filter ──────────────────

@pytest.mark.asyncio
@respx.mock
async def test_payable_search_expands_single_day(client, token_route):
    token_route()
    route = respx.post(f"{PAYABLE}/duplicates/search").mock(
        return_value=Response(200, json={"items": []})
    )
    tools = AccountPayableTools(client)
    await tools.search_duplicates({
        "branchCodeList": [1],
        "startExpiredDate": "2026-06-16",
        "endExpiredDate": "2026-06-16",
        "status": "Normal",
    })
    body = json.loads(route.calls.last.request.content)
    assert body["filter"]["startExpiredDate"] == "2026-06-16T00:00:00"
    assert body["filter"]["endExpiredDate"] == "2026-06-16T23:59:59"
