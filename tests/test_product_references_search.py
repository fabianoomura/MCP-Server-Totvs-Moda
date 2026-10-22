"""
POST /product/v2/references/search — ReferenceInDto exige `filter` e `option`
como campos irmãos no topo do body; `option.branchInfoCode` é obrigatório.
Sem isso, a API real responde 400 EmptyField em toda chamada.
"""

import json

import pytest
import respx
from httpx import Response

from conftest import TOTVS_BASE, TOKEN_URL


def _mock_oauth():
    respx.post(TOKEN_URL).mock(
        return_value=Response(200, json={
            "access_token": "fake", "expires_in": 3600, "token_type": "Bearer"
        })
    )


@pytest.mark.asyncio
@respx.mock
async def test_search_references_sends_option_as_sibling_of_filter(client):
    _mock_oauth()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/references/search").mock(
        return_value=Response(200, json={"items": [], "totalHits": 0})
    )

    from tools.product import ProductTools
    tools = ProductTools(client)

    await tools.search_references({"referenceCodeList": ["6624126004"]})

    body = json.loads(route.calls.last.request.content)
    assert body["option"] == {"branchInfoCode": 1}
    assert body["filter"] == {"referenceCodeList": ["6624126004"]}
    assert "option" not in body["filter"]


@pytest.mark.asyncio
@respx.mock
async def test_search_references_respects_explicit_option(client):
    _mock_oauth()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/references/search").mock(
        return_value=Response(200, json={"items": [], "totalHits": 0})
    )

    from tools.product import ProductTools
    tools = ProductTools(client)

    await tools.search_references({
        "referenceCodeList": ["6624126004"],
        "option": {"branchInfoCode": 2, "classificationTypeCodeList": [9]},
    })

    body = json.loads(route.calls.last.request.content)
    assert body["option"] == {"branchInfoCode": 2, "classificationTypeCodeList": [9]}
