"""
Context Cache
=============
Carregado na inicialização do servidor. Busca dados de referência do TOTVS
e armazena em memória para uso em consultas, criações e alterações.
"""
import logging
from typing import Any

logger = logging.getLogger("totvs-moda-mcp.context")

_cache: dict[str, Any] = {}
_loaded: bool = False


async def load(client: Any) -> None:
    """Busca todos os dados de referência do TOTVS e armazena no cache."""
    global _cache, _loaded

    BASE_PRODUCT = "/api/totvsmoda/product/v2"
    BASE_GENERAL = "/api/totvsmoda/general/v2"
    BASE_PERSON   = "/api/totvsmoda/person/v2"

    async def safe_get(path: str, params: dict | None = None) -> Any:
        try:
            return await client.get(path, params=params)
        except Exception as e:
            logger.warning(f"Context load failed for {path}: {e}")
            return None

    logger.info("Carregando contexto do TOTVS...")

    branches_raw  = await safe_get(f"{BASE_GENERAL}/branch-parameter")
    operations    = await safe_get(f"{BASE_GENERAL}/operations")
    pay_conditions = await safe_get(f"{BASE_GENERAL}/payment-conditions")
    price_headers = await safe_get(f"{BASE_PRODUCT}/price-tables-headers")
    classifications = await safe_get(f"{BASE_PRODUCT}/classifications")
    categories    = await safe_get(f"{BASE_PRODUCT}/category")
    grids         = await safe_get(f"{BASE_PRODUCT}/grid")
    measure_units = await safe_get(f"{BASE_PRODUCT}/measurement-unit")

    # Normaliza lista de filiais
    branches = []
    if isinstance(branches_raw, list):
        branches = [
            {"code": b.get("branchCode"), "name": b.get("name") or b.get("branchName")}
            for b in branches_raw
        ]
    elif isinstance(branches_raw, dict):
        items = branches_raw.get("items") or branches_raw.get("branches") or []
        branches = [
            {"code": b.get("branchCode") or b.get("code"), "name": b.get("name") or b.get("branchName")}
            for b in items
        ]

    _cache = {
        "branches":       branches,
        "operations":     operations,
        "paymentConditions": pay_conditions,
        "priceTables":    price_headers,
        "classifications": classifications,
        "categories":     categories,
        "grids":          grids,
        "measurementUnits": measure_units,
    }
    _loaded = True
    logger.info(f"Contexto carregado: {list(_cache.keys())}")


def get() -> dict[str, Any]:
    return _cache


def is_loaded() -> bool:
    return _loaded
