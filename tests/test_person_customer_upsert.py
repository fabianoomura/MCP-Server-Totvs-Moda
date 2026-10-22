"""
Upsert de clientes PF/PJ: contrato real dos DTOs e aliases planos.

A API espera `name`, `branchInsertCode` e listas `emails[]`/`phones[]`.
Os aliases planos (`corporateName`, `branchCode`, `email`, `phone`) do
schema antigo devem ser convertidos — não repassados cru.
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
async def test_individual_customer_flat_aliases_are_converted(client):
    _mock_oauth()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/individual-customers").mock(
        return_value=Response(200, json={"success": True})
    )

    from tools.person import PersonTools
    tools = PersonTools(client)

    await tools.create_or_update_individual_customer({
        "cpf": "12345678901",
        "name": "Fulana",
        "email": "f@x.com",
        "phone": "11999998888",
        "branchCode": 1,
    })

    body = json.loads(route.calls.last.request.content)
    assert body["branchInsertCode"] == 1
    assert body["emails"] == [{"email": "f@x.com", "isDefault": True}]
    assert body["phones"] == [{"number": "11999998888", "isDefault": True}]
    for alias in ("email", "phone", "branchCode"):
        assert alias not in body


@pytest.mark.asyncio
@respx.mock
async def test_individual_customer_dto_lists_pass_through(client):
    _mock_oauth()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/individual-customers").mock(
        return_value=Response(200, json={"success": True})
    )

    from tools.person import PersonTools
    tools = PersonTools(client)

    phones = [{"typeCode": 1, "number": "11999998888", "isDefault": True}]
    classifications = [{"classificationTypeCode": 2, "classificationCode": "006"}]
    await tools.create_or_update_individual_customer({
        "cpf": "12345678901",
        "name": "Fulana",
        "phones": phones,
        "classifications": classifications,
        "addresses": [{"addressType": "Commercial", "cep": "01410002", "number": 816}],
    })

    body = json.loads(route.calls.last.request.content)
    assert body["phones"] == phones
    assert body["classifications"] == classifications
    assert body["addresses"][0]["addressType"] == "Commercial"


@pytest.mark.asyncio
@respx.mock
async def test_legal_customer_corporate_name_maps_to_name(client):
    _mock_oauth()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/legal-customers").mock(
        return_value=Response(200, json={"success": True})
    )

    from tools.person import PersonTools
    tools = PersonTools(client)

    await tools.create_or_update_legal_customer({
        "cnpj": "12345678000199",
        "corporateName": "Empresa LTDA",
        "fantasyName": "Empresa",
        "classifications": [{"classificationTypeCode": 2, "classificationCode": "006"}],
    })

    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "Empresa LTDA"
    assert "corporateName" not in body
    assert body["fantasyName"] == "Empresa"
    assert body["classifications"] == [{"classificationTypeCode": 2, "classificationCode": "006"}]


@pytest.mark.asyncio
@respx.mock
async def test_legal_customer_explicit_name_wins_over_alias(client):
    _mock_oauth()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/legal-customers").mock(
        return_value=Response(200, json={"success": True})
    )

    from tools.person import PersonTools
    tools = PersonTools(client)

    await tools.create_or_update_legal_customer({
        "cnpj": "12345678000199",
        "corporateName": "Alias Ignorado",
        "name": "Razão Social Real",
    })

    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "Razão Social Real"
    assert "corporateName" not in body
