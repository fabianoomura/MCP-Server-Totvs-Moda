"""
Tests for tools/_output.py and the file-saving behavior of get_danfe and
search_product_images (roadmap #3).
"""
import base64

import pytest
import respx
from httpx import Response

from tools._output import (
    resolve_output_dir,
    save_base64,
    safe_filename,
    extract_access_key,
)
from tools.fiscal import FiscalTools
from tools.image import ImageTools

TOTVS_BASE = "https://totvs.test:9443"
FISCAL = f"{TOTVS_BASE}/api/totvsmoda/fiscal/v2"
IMAGE = f"{TOTVS_BASE}/api/totvsmoda/image/v2"

ACCESS_KEY = "41260621833409000169550010001448971158175697"  # 44 digits

# Payloads padded so the base64 is > 100 chars (the threshold below which the
# tools treat a value as a placeholder and skip it).
PDF_BYTES = b"%PDF-1.5\n" + b"0" * 200 + b"\n%%EOF"
PDF_B64 = base64.b64encode(PDF_BYTES).decode()
JPG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 200
JPG_B64 = base64.b64encode(JPG_BYTES).decode()


# ── _output helpers ─────────────────────────────────────────────────────────

def test_resolve_output_dir_env_override(tmp_path, monkeypatch):
    target = tmp_path / "saida"
    monkeypatch.setenv("TOTVS_OUTPUT_DIR", str(target))
    d = resolve_output_dir()
    assert d == target
    assert target.is_dir()


def test_save_base64_writes_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TOTVS_OUTPUT_DIR", str(tmp_path))
    meta = save_base64(PDF_B64, "x.pdf")
    assert meta["fileName"] == "x.pdf"
    assert meta["sizeBytes"] == len(PDF_BYTES)
    assert (tmp_path / "x.pdf").read_bytes() == PDF_BYTES


def test_save_base64_invalid_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("TOTVS_OUTPUT_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        save_base64("AAAAA", "bad.bin")  # incorrect padding


def test_safe_filename_sanitizes():
    assert safe_filename("a b/c:d.pdf") == "a-b-c-d.pdf"
    assert safe_filename("") == "arquivo"


def test_extract_access_key_from_raw():
    assert extract_access_key(f"<chNFe>{ACCESS_KEY}</chNFe>") == ACCESS_KEY


def test_extract_access_key_from_base64():
    xml = f"<NFe><chNFe>{ACCESS_KEY}</chNFe></NFe>"
    b64 = base64.b64encode(xml.encode()).decode()
    assert extract_access_key(b64) == ACCESS_KEY


def test_extract_access_key_none():
    assert extract_access_key("sem chave aqui") is None


# ── get_danfe ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_get_danfe_saves_file(client, token_route, tmp_path, monkeypatch):
    monkeypatch.setenv("TOTVS_OUTPUT_DIR", str(tmp_path))
    token_route()
    respx.post(f"{FISCAL}/danfe-search").mock(
        return_value=Response(200, json={"danfePdfBase64": PDF_B64, "invoiceStatus": "Authorized"})
    )
    tools = FiscalTools(client)
    out = await tools.get_danfe({"mainInvoiceXml": f"<chNFe>{ACCESS_KEY}</chNFe>"})

    assert "danfePdfBase64" not in out
    assert out["fileName"] == f"DANFE-{ACCESS_KEY}.pdf"
    assert out["invoiceStatus"] == "Authorized"
    saved = tmp_path / f"DANFE-{ACCESS_KEY}.pdf"
    assert saved.read_bytes() == PDF_BYTES


@pytest.mark.asyncio
@respx.mock
async def test_get_danfe_return_base64_flag(client, token_route, tmp_path, monkeypatch):
    monkeypatch.setenv("TOTVS_OUTPUT_DIR", str(tmp_path))
    token_route()
    respx.post(f"{FISCAL}/danfe-search").mock(
        return_value=Response(200, json={"danfePdfBase64": PDF_B64})
    )
    tools = FiscalTools(client)
    out = await tools.get_danfe(
        {"mainInvoiceXml": "<xml/>", "returnBase64": True}
    )
    assert out == {"danfePdfBase64": PDF_B64}
    assert not list(tmp_path.iterdir())  # nothing written


@pytest.mark.asyncio
@respx.mock
async def test_get_danfe_by_access_key_fetches_xml(client, token_route, tmp_path, monkeypatch):
    """Only accessKey given → XML is fetched from /xml-contents and forwarded."""
    monkeypatch.setenv("TOTVS_OUTPUT_DIR", str(tmp_path))
    token_route()
    xml_b64 = base64.b64encode(f"<chNFe>{ACCESS_KEY}</chNFe>".encode()).decode()
    xml_route = respx.get(f"{FISCAL}/xml-contents/{ACCESS_KEY}").mock(
        return_value=Response(200, json={"invoiceStatus": "Authorized", "mainInvoiceXml": xml_b64})
    )
    danfe_route = respx.post(f"{FISCAL}/danfe-search").mock(
        return_value=Response(200, json={"danfePdfBase64": PDF_B64})
    )
    tools = FiscalTools(client)
    out = await tools.get_danfe({"accessKey": ACCESS_KEY})

    assert xml_route.called
    import json as _json
    assert _json.loads(danfe_route.calls[0].request.content)["mainInvoiceXml"] == xml_b64
    assert out["fileName"] == f"DANFE-{ACCESS_KEY}.pdf"
    assert (tmp_path / f"DANFE-{ACCESS_KEY}.pdf").read_bytes() == PDF_BYTES


@pytest.mark.asyncio
async def test_get_danfe_requires_xml_or_key(client):
    with pytest.raises(ValueError):
        await FiscalTools(client).get_danfe({})


# ── search_product_images ────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_search_product_images_saves_file(client, token_route, tmp_path, monkeypatch):
    monkeypatch.setenv("TOTVS_OUTPUT_DIR", str(tmp_path))
    token_route()
    respx.post(f"{IMAGE}/product/search").mock(
        return_value=Response(200, json={
            "items": [{
                "productCode": 20,
                "images": {"imageCode": 3, "imageName": "lencol-astros", "imageFile": JPG_B64},
            }],
        })
    )
    tools = ImageTools(client)
    out = await tools.search_product_images({"productCodeList": [20]})

    img = out["items"][0]["images"]
    assert "imageFile" not in img
    assert img["savedFile"].endswith("lencol-astros.jpg")
    assert (tmp_path / "lencol-astros.jpg").read_bytes() == JPG_BYTES


@pytest.mark.asyncio
@respx.mock
async def test_search_product_images_return_base64_flag(client, token_route, tmp_path, monkeypatch):
    monkeypatch.setenv("TOTVS_OUTPUT_DIR", str(tmp_path))
    token_route()
    respx.post(f"{IMAGE}/product/search").mock(
        return_value=Response(200, json={
            "items": [{"productCode": 20, "images": {"imageFile": JPG_B64}}],
        })
    )
    tools = ImageTools(client)
    out = await tools.search_product_images({"productCodeList": [20], "returnBase64": True})
    assert out["items"][0]["images"]["imageFile"] == JPG_B64
    assert not list(tmp_path.iterdir())
