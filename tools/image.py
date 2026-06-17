"""
Image Tools
===========
API Image v2 — /api/totvsmoda/image/v2/
Imagens de produtos (upload, consulta, remoção).
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._output import save_base64, safe_filename

logger = logging.getLogger("totvs-moda-mcp.image")
BASE = "/api/totvsmoda/image/v2"


def _img_ext(b64: str) -> str:
    """Guess image extension from the base64 magic prefix."""
    head = (b64 or "")[:16]
    if head.startswith("iVBOR"):
        return ".png"
    if head.startswith("R0lGOD"):
        return ".gif"
    if head.startswith("UklGR"):
        return ".webp"
    return ".jpg"


def _save_images_in_result(result: Any) -> Any:
    """Decode each item's imageFile base64 to disk, replacing it with a path.

    Keeps the response small (a single product image is easily 80-150 KB of
    base64) while preserving the image metadata. `images` may be a single
    object or a list.
    """
    if not isinstance(result, dict):
        return result
    items = result.get("items")
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        imgs = item.get("images")
        targets = imgs if isinstance(imgs, list) else ([imgs] if isinstance(imgs, dict) else [])
        code = item.get("productCode")
        for img in targets:
            if not isinstance(img, dict):
                continue
            b64 = img.get("imageFile")
            if not isinstance(b64, str) or len(b64) < 100:
                continue
            base = img.get("imageName") or f"produto-{code}-{img.get('imageCode', '')}"
            fname = safe_filename(str(base)) + _img_ext(b64)
            try:
                saved = save_base64(b64, fname)
            except ValueError:
                continue
            img.pop("imageFile", None)
            img["savedFile"] = saved["savedFile"]
            img["sizeKb"] = saved["sizeKb"]
    return result


def _pascal_params(args: dict[str, Any]) -> dict[str, Any]:
    special = {"personCpfCnpj": "CpfCnpj", "cpfCnpj": "CpfCnpj", "imageCode": "ImageCode", "imageId": "ImageCode"}
    return {special.get(k, k[:1].upper() + k[1:]): v for k, v in args.items() if v is not None and k != "fields"}


def _image_body(args: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in args.items() if v is not None}
    if "imageBase64" in body and "base64" not in body:
        body["base64"] = body.pop("imageBase64")
    if "fileName" in body and "name" not in body:
        body["name"] = body.pop("fileName")
    return body


class ImageTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def get_product_images(self, args: dict[str, Any]) -> Any:
        """GET /product-images — Imagens de um produto por referência."""
        params: dict[str, Any] = {"ReferenceCode": args["referenceCode"]}
        if args.get("branchCode") is not None:
            params["BranchCode"] = args["branchCode"]
        return await self.client.get(f"{BASE}/product-images", params=params)

    async def search_product_images(self, args: dict[str, Any]) -> Any:
        """POST /product/search — Lista imagens de produto por filtro.

        Por padrão salva cada imagem em arquivo (pasta de saída, ver
        TOTVS_OUTPUT_DIR; default Downloads) e substitui o base64 pelo caminho,
        evitando estourar o limite de tokens. Use returnBase64=true para o cru.
        """
        excluded = ("page", "pageSize", "order", "fields", "expand", "returnBase64")
        flt = {k: v for k, v in args.items() if k not in excluded and v is not None}
        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        if args.get("order"):
            body["order"] = args["order"]
        if args.get("expand"):
            body["expand"] = args["expand"]
        result = await self.client.post(f"{BASE}/product/search", body)
        if args.get("returnBase64"):
            return result
        return _save_images_in_result(result)

    async def upload_product_image(self, args: dict[str, Any]) -> Any:
        """POST /product — ⚠️ Upload de imagem de produto (base64)."""
        return await self.client.post(f"{BASE}/product", _image_body(args))

    async def import_image_no_link(self, args: dict[str, Any]) -> Any:
        """POST /imports - importa imagem de produto sem vinculo."""
        return await self.client.post("/api/totvsmoda/image/V2/imports", _image_body(args))

    async def upload_person_image(self, args: dict[str, Any]) -> Any:
        """POST /persons - insere imagem de pessoa."""
        return await self.client.post(f"{BASE}/persons", _image_body(args))

    async def list_person_images(self, args: dict[str, Any]) -> Any:
        """GET /persons - lista imagens vinculadas a uma pessoa."""
        result = await self.client.get(f"{BASE}/persons", params=_pascal_params(args) or None)
        return apply_fields(result, args)

    async def get_person_image_base64(self, args: dict[str, Any]) -> Any:
        """GET /person-images - retorna imagem de pessoa por codigo de imagem."""
        result = await self.client.get(f"{BASE}/person-images", params=_pascal_params(args) or None)
        return apply_fields(result, args)

    async def delete_product_image(self, args: dict[str, Any]) -> Any:
        """DELETE /product-images — ⚠️ Remove imagem de produto."""
        params: dict[str, Any] = {"ReferenceCode": args["referenceCode"]}
        if args.get("imageType") is not None:
            params["ImageType"] = args["imageType"]
        if args.get("order") is not None:
            params["Order"] = args["order"]
        return await self.client.delete(f"{BASE}/product-images", params=params)


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_product_images",
        description="Consulta imagens de produto por filtro. Por padrão salva cada imagem em arquivo (pasta de saída, ver TOTVS_OUTPUT_DIR; default Downloads) e retorna o caminho. Use returnBase64=true para receber o base64 cru.",
        inputSchema={
            "type": "object",
            "properties": {
                "referenceCode": {
                    "type": "string"
                },
                "productCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100
                },
                "returnBase64": {
                    "type": "boolean",
                    "description": "Se true, retorna o base64 cru em vez de salvar os arquivos"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_upload_product_image",
        description="⚠️ Importa imagem de produto (com vínculo). Imagem deve estar em base64.",
        inputSchema={
            "type": "object",
            "properties": {
                "productCode": {
                    "type": "integer"
                },
                "referenceCode": {
                    "type": "string"
                },
                "imageBase64": {
                    "type": "string",
                    "description": "Imagem em base64"
                },
                "branchCode": {
                    "type": "integer"
                },
                "imageType": {
                    "type": "string"
                },
                "order": {
                    "type": "integer"
                },
                "colorCode": {
                    "type": "string"
                }
            },
            "required": [
                "imageBase64"
            ]
        },
    ),
    types.Tool(
        name="totvs_import_image_no_link",
        description="⚠️ Importa imagem sem realizar vínculo com produto (vínculo posterior).",
        inputSchema={
            "type": "object",
            "properties": {
                "imageBase64": {
                    "type": "string",
                    "description": "Imagem em base64"
                },
                "fileName": {
                    "type": "string"
                }
            },
            "required": [
                "imageBase64"
            ]
        },
    ),
    types.Tool(
        name="totvs_upload_person_image",
        description="⚠️ Insere imagem de uma pessoa.",
        inputSchema={
            "type": "object",
            "properties": {
                "personCode": {
                    "type": "integer"
                },
                "personCpfCnpj": {
                    "type": "string"
                },
                "imageBase64": {
                    "type": "string"
                }
            },
            "required": [
                "imageBase64"
            ]
        },
    ),
    types.Tool(
        name="totvs_list_person_images",
        description="Lista imagens de uma pessoa.",
        inputSchema={
            "type": "object",
            "properties": {
                "personCode": {
                    "type": "integer"
                },
                "personCpfCnpj": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_person_image_base64",
        description="Retorna imagem de pessoa em base64.",
        inputSchema={
            "type": "object",
            "properties": {
                "personCode": {
                    "type": "integer"
                },
                "imageId": {
                    "type": "string"
                }
            }
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_product_images": "search_product_images",
    "totvs_upload_product_image": "upload_product_image",
    "totvs_import_image_no_link": "import_image_no_link",
    "totvs_upload_person_image": "upload_person_image",
    "totvs_list_person_images": "list_person_images",
    "totvs_get_person_image_base64": "get_person_image_base64",
}