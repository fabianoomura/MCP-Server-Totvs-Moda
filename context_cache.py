"""
Context Cache
=============
Carregado na inicialização do servidor. Busca dados de referência do TOTVS
e armazena em memória para uso em consultas, criações e alterações.
"""
import logging
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

    # ── Filiais únicas extraídas dos usuários ─────────────────────────────────
    branches: list[dict] = []
    if users and isinstance(users, dict):
        user_items = users.get("items") or users.get("Users") or []
        seen_branches: set = set()
        for u in user_items:
            bc   = u.get("branchCode") or u.get("BranchCode")
            name = u.get("branchName") or u.get("BranchName") or u.get("companyName") or u.get("CompanyName") or ""
            if bc and bc not in seen_branches:
                seen_branches.add(bc)
                branches.append({"branchCode": bc, "branchName": name})
        branches.sort(key=lambda x: x["branchCode"])
        logger.info(f"Filiais detectadas via usuários: {[b['branchCode'] for b in branches]}")

    # ── Descoberta de tipos de preço e custo ──────────────────────────────────
    # Estratégia: pegar produto mais vendido nos últimos 30 dias (ou qualquer produto)
    # e consultar preços/custos com range amplo de códigos para extrair os tipos disponíveis.

    price_types: list[dict] = []
    cost_types: list[dict]  = []

    # Usar primeiro branchCode já extraído (ou 1 como fallback)
    branch_code: int = branches[0]["branchCode"] if branches else 1

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
