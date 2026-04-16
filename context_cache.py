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

    BASE_PRODUCT    = "/api/totvsmoda/product/v2"
    BASE_GENERAL    = "/api/totvsmoda/general/v2"
    BASE_MANAGEMENT = "/api/totvsmoda/management/v2"

    async def safe_get(path: str, params: dict | None = None) -> Any:
        try:
            return await client.get(path, params=params)
        except Exception as e:
            logger.warning(f"Context load failed for {path}: {e}")
            return None

    logger.info("Carregando contexto do TOTVS...")

    # general/v2 — sem parâmetros obrigatórios
    operations     = await safe_get(f"{BASE_GENERAL}/operations", params={"IsInactive": "false", "PageSize": 1000})
    pay_conditions = await safe_get(f"{BASE_GENERAL}/payment-conditions")
    pay_plans      = await safe_get(f"{BASE_GENERAL}/payment-plans")

    # product/v2
    price_headers   = await safe_get(f"{BASE_PRODUCT}/price-tables-headers")
    classifications = await safe_get(f"{BASE_PRODUCT}/classifications")
    categories      = await safe_get(f"{BASE_PRODUCT}/category")
    grids           = await safe_get(f"{BASE_PRODUCT}/grid")
    measure_units   = await safe_get(f"{BASE_PRODUCT}/measurement-unit")

    # management/v2/users — lista usuários (serve para descobrir filiais via branchCode)
    users = await safe_get(f"{BASE_MANAGEMENT}/users", params={"PageSize": 1000})

    _cache = {
        "operations":        operations,
        "paymentConditions": pay_conditions,
        "paymentPlans":      pay_plans,
        "priceTables":       price_headers,
        "classifications":   classifications,
        "categories":        categories,
        "grids":             grids,
        "measurementUnits":  measure_units,
        "users":             users,
    }
    _loaded = True
    logger.info(f"Contexto carregado: {list(_cache.keys())}")


def get() -> dict[str, Any]:
    return _cache


def is_loaded() -> bool:
    return _loaded
