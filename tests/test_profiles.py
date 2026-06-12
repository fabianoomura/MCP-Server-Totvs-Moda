"""
Tests for TOTVS_PROFILE tool exposure.
"""
import json
from types import SimpleNamespace

import pytest

import server


def _tool_names(tools):
    return {tool.name for tool in tools}


@pytest.mark.asyncio
async def test_vendedor_profile_does_not_list_or_execute_cancel_order(monkeypatch):
    monkeypatch.setenv("TOTVS_PROFILE", "vendedor")

    names = _tool_names(await server.handle_list_tools())
    assert "totvs_cancel_order" not in names

    result = await server.handle_call_tool(
        "totvs_cancel_order",
        {"branchCode": 1, "orderCode": 123, "reasonCancellationCode": 99},
    )
    payload = json.loads(result[0].text)
    assert "não habilitada no perfil atual" in payload["error"]


@pytest.mark.asyncio
async def test_leitura_profile_excludes_write_tools(monkeypatch):
    monkeypatch.setenv("TOTVS_PROFILE", "leitura")

    names = _tool_names(await server.handle_list_tools())
    write_names = {tool.name for tool in server.TOOLS if getattr(tool, "annotations", None)}

    assert len(write_names) == 7
    assert names.isdisjoint(write_names)


@pytest.mark.asyncio
async def test_tools_extra_adds_write_to_leitura_and_allows_execution(monkeypatch):
    async def cancel_order(args):
        return {"cancelled": args["orderCode"]}

    monkeypatch.setenv("TOTVS_PROFILE", "leitura")
    monkeypatch.setenv("TOTVS_TOOLS_EXTRA", "totvs_cancel_order")
    monkeypatch.setattr(
        server,
        "get_modules",
        lambda: {"sales_order": SimpleNamespace(cancel_order=cancel_order)},
    )

    names = _tool_names(await server.handle_list_tools())
    assert "totvs_cancel_order" in names

    result = await server.handle_call_tool(
        "totvs_cancel_order",
        {"branchCode": 1, "orderCode": 123, "reasonCancellationCode": 99},
    )
    assert json.loads(result[0].text) == {"cancelled": 123}


@pytest.mark.asyncio
async def test_tools_exclude_removes_tool_from_completo(monkeypatch):
    monkeypatch.delenv("TOTVS_PROFILE", raising=False)
    monkeypatch.setenv("TOTVS_TOOLS_EXCLUDE", "totvs_search_orders")

    names = _tool_names(await server.handle_list_tools())
    assert "totvs_search_orders" not in names


@pytest.mark.asyncio
async def test_default_profile_is_current_full_tool_list(monkeypatch):
    monkeypatch.delenv("TOTVS_PROFILE", raising=False)
    monkeypatch.delenv("TOTVS_TOOLS_EXTRA", raising=False)
    monkeypatch.delenv("TOTVS_TOOLS_EXCLUDE", raising=False)

    tools = await server.handle_list_tools()
    assert len(tools) == len(server.TOOLS)
    assert _tool_names(tools) == {tool.name for tool in server.TOOLS}


@pytest.mark.asyncio
async def test_call_tool_outside_profile_returns_clear_error(monkeypatch):
    monkeypatch.setenv("TOTVS_PROFILE", "vendedor")

    result = await server.handle_call_tool("totvs_create_voucher", {"branchCode": 1, "value": 10})
    payload = json.loads(result[0].text)

    assert "não habilitada no perfil atual" in payload["error"]
