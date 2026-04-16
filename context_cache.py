"""
Context Cache
=============
Carregado na inicialização do servidor. Busca dados de referência do TOTVS
e armazena em memória para uso em consultas, criações e alterações.
"""
import logging
import os
from datetime import datetime, timedelta
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
    BASE_ECOMMERCE  = "/api/totvsmoda/ecommerce-sales-order/v2"

    async def safe_get(path: str, params: dict | None = None) -> Any:
        try:
            return await client.get(path, params=params)
        except Exception as e:
            logger.warning(f"Context load failed for {path}: {e}")
            return None

    async def safe_post(path: str, body: dict) -> Any:
        try:
            return await client.post(path, body)
        except Exception as e:
            logger.warning(f"Context load failed for {path}: {e}")
            return None

    logger.info("Carregando contexto do TOTVS...")

    # general/v2
    operations     = await safe_get(f"{BASE_GENERAL}/operations", params={"StartChangeDate": "2000-01-01T00:00:00", "EndChangeDate": "2099-12-31T23:59:59", "PageSize": 1000})
    pay_conditions = await safe_get(f"{BASE_GENERAL}/payment-conditions")
    pay_plans      = await safe_get(f"{BASE_GENERAL}/payment-plans")

    # product/v2
    price_headers   = await safe_get(f"{BASE_PRODUCT}/price-tables-headers")
    classifications = await safe_get(f"{BASE_PRODUCT}/classifications")
    categories      = await safe_get(f"{BASE_PRODUCT}/category")
    grids           = await safe_get(f"{BASE_PRODUCT}/grid")
    measure_units   = await safe_get(f"{BASE_PRODUCT}/measurement-unit")

    # management/v2/users
    users = await safe_get(f"{BASE_MANAGEMENT}/users", params={"PageSize": 1000})

    # ── Filiais via variável de ambiente TOTVS_BRANCH_CODES ───────────────────
    _raw = os.environ.get("TOTVS_BRANCH_CODES", "1")
    branches: list[int] = [int(x.strip()) for x in _raw.split(",") if x.strip().isdigit()]
    if not branches:
        branches = [1]
    logger.info(f"Filiais configuradas: {branches}")

    # ── Descoberta de tipos de preço e custo ──────────────────────────────────
    # Estratégia: pegar produto mais vendido nos últimos 30 dias (ou qualquer produto)
    # e consultar preços/custos com range amplo de códigos para extrair os tipos disponíveis.

    price_types: list[dict] = []
    cost_types: list[dict]  = []

    branch_code: int = branches[0]

    # Tentar pegar produto mais vendido nos últimos 30 dias
    today = datetime.now()
    start_date = (today - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")
    end_date   = today.strftime("%Y-%m-%dT23:59:59")

    sample_product_code: int | None = None

    best_selling = await safe_post(
        f"{BASE_ECOMMERCE}/best-selling-products/search",
        {"startDate": start_date, "endDate": end_date, "pageSize": 1},
    )
    if best_selling and isinstance(best_selling, dict):
        items = best_selling.get("items") or best_selling.get("Items") or []
        if items:
            pc = items[0].get("productCode") or items[0].get("ProductCode")
            if pc:
                sample_product_code = int(pc)

    # Fallback: qualquer produto do catálogo
    if not sample_product_code:
        any_product = await safe_post(f"{BASE_PRODUCT}/products/search", {"pageSize": 1})
        if any_product and isinstance(any_product, dict):
            items = any_product.get("items") or any_product.get("Items") or []
            if items:
                pc = items[0].get("productCode") or items[0].get("ProductCode")
                if pc:
                    sample_product_code = int(pc)

    if sample_product_code:
        logger.info(f"Descobrindo tipos de preço/custo via produto {sample_product_code} (filial {branch_code})...")

        # Consultar preços com range 1..20 para capturar todos os tipos cadastrados
        prices_data = await safe_post(f"{BASE_PRODUCT}/prices/search", {
            "filter": {"productCodeList": [sample_product_code]},
            "option": {"prices": [{"branchCode": branch_code, "priceCodeList": list(range(1, 21))}]},
        })
        if prices_data and isinstance(prices_data, dict):
            seen: set = set()
            items = prices_data.get("items") or prices_data.get("Items") or []
            for item in items:
                for p in (item.get("prices") or item.get("Prices") or []):
                    code = p.get("priceCode") or p.get("PriceCode")
                    name = p.get("priceName") or p.get("PriceName") or ""
                    if code is not None and code not in seen:
                        seen.add(code)
                        price_types.append({"priceCode": code, "priceName": name})

        # Consultar custos
        costs_data = await safe_post(f"{BASE_PRODUCT}/costs/search", {
            "filter": {"productCodeList": [sample_product_code]},
            "option": {"branchCode": branch_code},
        })
        if costs_data and isinstance(costs_data, dict):
            seen = set()
            items = costs_data.get("items") or costs_data.get("Items") or []
            for item in items:
                for c in (item.get("costs") or item.get("Costs") or []):
                    code = c.get("costCode") or c.get("CostCode")
                    name = c.get("costName") or c.get("CostName") or ""
                    if code is not None and code not in seen:
                        seen.add(code)
                        cost_types.append({"costCode": code, "costName": name})

        logger.info(f"Tipos de preço descobertos: {price_types}")
        logger.info(f"Tipos de custo descobertos: {cost_types}")
    else:
        logger.warning("Nenhum produto encontrado para descoberta de tipos de preço/custo.")

    _cache = {
        "branches":          branches,
        "operations":        operations,
        "paymentConditions": pay_conditions,
        "paymentPlans":      pay_plans,
        "priceTables":       price_headers,
        "classifications":   classifications,
        "categories":        categories,
        "grids":             grids,
        "measurementUnits":  measure_units,
        "users":             users,
        "priceTypes":        price_types,
        "costTypes":         cost_types,
    }
    _loaded = True
    logger.info(f"Contexto carregado: {list(_cache.keys())}")


def get() -> dict[str, Any]:
    return _cache


def is_loaded() -> bool:
    return _loaded
