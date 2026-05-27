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

logger = logging.getLogger("totvs-moda-mcp.image")
BASE = "/api/totvsmoda/image/v2"


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
        """POST /product/search — Lista imagens de produto por filtro."""
        excluded = ("page", "pageSize", "order", "fields", "expand")
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
        return await self.client.post(f"{BASE}/product/search", body)

    async def upload_product_image(self, args: dict[str, Any]) -> Any:
        """POST /product — ⚠️ Upload de imagem de produto (base64)."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/product", body)

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
