"""
Image Tools
===========
API Image v2 — /api/totvsmoda/image/v2/
Imagens de produtos (upload, consulta, remoção).
"""
import logging
from typing import Any
from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.image")
BASE = "/api/totvsmoda/image/v2"


class ImageTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def get_product_images(self, args: dict[str, Any]) -> Any:
        """GET /product-images — Imagens de um produto por referência."""
        params: dict[str, Any] = {"ReferenceCode": args["referenceCode"]}
        if args.get("branchCode") is not None:
            params["BranchCode"] = args["branchCode"]
        return await self.client.get(f"{BASE}/product-images", params=params)

    async def upload_product_image(self, args: dict[str, Any]) -> Any:
        """POST /product-images — ⚠️ Upload de imagem de produto (base64)."""
        body: dict[str, Any] = {
            "referenceCode": args["referenceCode"],
            "imageBase64": args["imageBase64"],
        }
        for field in ("branchCode", "imageType", "order", "colorCode"):
            if args.get(field) is not None:
                body[field] = args[field]
        return await self.client.post(f"{BASE}/product-images", body)

    async def delete_product_image(self, args: dict[str, Any]) -> Any:
        """DELETE /product-images — ⚠️ Remove imagem de produto."""
        params: dict[str, Any] = {"ReferenceCode": args["referenceCode"]}
        if args.get("imageType") is not None:
            params["ImageType"] = args["imageType"]
        if args.get("order") is not None:
            params["Order"] = args["order"]
        return await self.client.delete(f"{BASE}/product-images", params=params)
