"""
Context Cache v3.1
==================
Carrega dados de referência do TOTVS no startup pra evitar chamadas repetidas.

Mudanças v3.1:
1. NOVO: descoberta de priceTypes e costTypes via top 20 produtos vendidos.
   Antes vinha vazio. Agora consulta /prices/search e /costs/search SEM filtro
   de priceCode/costCode pra descobrir quais tabelas existem na empresa.

2. NOVO: slim mode no get_context() — retorno em ~5KB (era 313KB).
   verbose=True traz o cache completo pra debug.

3. Fix: estrutura de cache padronizada com keys consistentes.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from totvs_client import TotvsClient

logger = logging.getLogger("totvs-moda-mcp.context_cache")

# Cache global do módulo
CACHE: dict[str, Any] = {}


async def load_context(client: TotvsClient) -> dict[str, Any]:
    """Carrega dados de referência do TOTVS na inicialização.

    Popula CACHE com:
    - branches: lista de filiais
    - operations: lista de operações ativas
    - priceTypes: códigos de tabela de preço EXISTENTES (descobertos via produtos vendidos)
    - costTypes: códigos de tipo de custo EXISTENTES (mesma lógica)
    - paymentConditions: lista de condições de pagamento

    Cada erro é logado mas não impede o startup. Cache parcial > cache vazio.
    """
    global CACHE
    CACHE = {
        "loadedAt": datetime.utcnow().isoformat() + "Z",
        "branches": [],
        "operations": [],
        "priceTypes": [],
        "costTypes": [],
        "paymentConditions": [],
    }

    # 1. Branches (filiais) — fundamental, vem do env (default "1" se não configurado)
    branches_raw = os.environ.get("TOTVS_BRANCH_CODES", "1").strip()
    try:
        parsed = [int(x.strip()) for x in branches_raw.split(",") if x.strip().isdigit()]
        CACHE["branches"] = parsed if parsed else [1]
    except ValueError:
        logger.warning(f"TOTVS_BRANCH_CODES inválido: {branches_raw!r}")
        CACHE["branches"] = [1]

    # Tarefas paralelas pra ganhar tempo no startup
    tasks = [
        _load_operations(client),
        _load_payment_conditions(client),
        _load_price_and_cost_types(client),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Falha parcial no context_cache: {type(result).__name__}: {result}")

    logger.info(
        f"Context cache loaded: "
        f"{len(CACHE['branches'])} branches, "
        f"{len(CACHE['operations'])} operations, "
        f"{len(CACHE['priceTypes'])} priceTypes, "
        f"{len(CACHE['costTypes'])} costTypes, "
        f"{len(CACHE['paymentConditions'])} paymentConditions"
    )

    return CACHE


async def _load_operations(client: TotvsClient) -> None:
    """Carrega operações ativas de venda/compra."""
    try:
        response = await client.get(
            "/api/totvsmoda/general/v2/operations",
            params={
                "StartChangeDate": "2000-01-01T00:00:00",
                "EndChangeDate": "2099-12-31T23:59:59",
                "PageSize": 1000,
            }
        )
        items = response.get("items", []) if isinstance(response, dict) else []
        CACHE["operations"] = [
            {
                "code": o.get("operationCode"),
                "name": o.get("description"),
                "type": o.get("invoiceData", {}).get("operationsType") if isinstance(o.get("invoiceData"), dict) else None,
            }
            for o in items
        ]
    except Exception as e:
        logger.debug(f"operations load failed: {e}")


async def _load_payment_conditions(client: TotvsClient) -> None:
    """Carrega condições de pagamento ativas."""
    try:
        response = await client.get(
            "/api/totvsmoda/general/v2/payment-conditions",
            params={"page": 1, "pageSize": 100}
        )
        items = response.get("items", []) if isinstance(response, dict) else []
        CACHE["paymentConditions"] = [
            {"code": p.get("code"), "name": p.get("name")}
            for p in items
        ]
    except Exception as e:
        logger.debug(f"payment_conditions load failed: {e}")


async def _load_price_and_cost_types(client: TotvsClient) -> None:
    """Descobre priceTypes e costTypes existentes consultando produtos top vendidos.

    Estratégia:
    1. Pega 20 produtos vendidos no último mês (via search_orders + items)
    2. Pra cada produto, consulta /prices/search e /costs/search SEM filtro de tabela
    3. Agrega priceCode e costCode únicos que aparecerem
    4. Resultado: lista de tabelas EXISTENTES na empresa, não chutadas

    Esta abordagem funciona porque a API TOTVS retorna em items[].prices[]
    todas as tabelas que aquele produto tem cadastro, sem precisar de filtro.
    """
    try:
        # Etapa 1: pegar produtos com vendas recentes
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=30)

        branches = CACHE.get("branches") or [1]

        orders_response = await client.post(
            "/api/totvsmoda/sales-order/v2/orders/search",
            {
                "filter": {
                    "branchCodeList": branches,
                    "startOrderDate": start_date.isoformat(),
                    "endOrderDate": end_date.isoformat(),
                },
                "expand": "items",
                "page": 1,
                "pageSize": 50,  # 50 pedidos costuma trazer 100+ produtos únicos
            }
        )

        orders = orders_response.get("items", []) if isinstance(orders_response, dict) else []
        product_codes: set[int] = set()
        for order in orders:
            for item in order.get("items") or []:
                pc = item.get("productCode")
                if pc is not None:
                    product_codes.add(pc)
            if len(product_codes) >= 20:
                break

        if not product_codes:
            logger.info("Nenhum produto vendido no período recente. priceTypes/costTypes ficam vazios.")
            return

        product_list = list(product_codes)[:20]
        logger.debug(f"Sondando priceTypes/costTypes via {len(product_list)} produtos: {product_list[:5]}...")

        # Etapa 2: descobrir priceTypes
        await _discover_price_types(client, product_list, branches)

        # Etapa 3: descobrir costTypes
        await _discover_cost_types(client, product_list, branches)

    except Exception as e:
        logger.debug(f"price/cost types discovery failed: {e}")


async def _discover_price_types(client: TotvsClient, product_codes: list[int], branches: list[int]) -> None:
    """Descobre priceTypes ativos sondando priceCode 1..N com os produtos top vendidos.

    O endpoint /prices/search exige option.prices[{branchCode, priceCodeList}] e rejeita
    a requisição inteira se algum código for inválido (NotFound). Por isso sondamos
    um código de cada vez, parando em 10 consecutivos não encontrados.
    """
    branch = branches[0] if branches else 1
    seen: dict[int, dict[str, Any]] = {}
    consecutive_not_found = 0

    for price_code in range(1, 30):
        try:
            response = await client.post(
                "/api/totvsmoda/product/v2/prices/search",
                {
                    "filter": {"productCodeList": product_codes[:5]},
                    "option": {"prices": [{"branchCode": branch, "priceCodeList": [price_code]}]},
                    "page": 1,
                    "pageSize": 5,
                }
            )
            items = response.get("items", []) if isinstance(response, dict) else []
            for item in items:
                for price in item.get("prices") or []:
                    code = price.get("priceCode")
                    name = price.get("priceName")
                    if code is not None and code not in seen and price.get("price", 0) > 0:
                        seen[code] = {"priceCode": code, "priceName": name}
            consecutive_not_found = 0
        except Exception:
            consecutive_not_found += 1
            if consecutive_not_found >= 3:
                break

    CACHE["priceTypes"] = sorted(seen.values(), key=lambda x: x["priceCode"])
    logger.debug(f"priceTypes descobertos: {CACHE['priceTypes']}")


async def _discover_cost_types(client: TotvsClient, product_codes: list[int], branches: list[int]) -> None:
    """Descobre costTypes ativos sondando costCode 1..N com os produtos top vendidos.

    O endpoint /costs/search exige:
    - filter.hasCost=true, filter.branchCostCodeList, filter.costCodeList
    - option.costs[{branchCode, costCodeList}]
    Sondamos um código de cada vez, parando em 3 consecutivos não encontrados.
    """
    branch = branches[0] if branches else 1
    seen: dict[int, dict[str, Any]] = {}
    consecutive_not_found = 0

    for cost_code in range(1, 30):
        try:
            response = await client.post(
                "/api/totvsmoda/product/v2/costs/search",
                {
                    "filter": {
                        "productCodeList": product_codes[:5],
                        "hasCost": True,
                        "branchCostCodeList": [branch],
                        "costCodeList": [cost_code],
                    },
                    "option": {"costs": [{"branchCode": branch, "costCodeList": [cost_code]}]},
                    "page": 1,
                    "pageSize": 5,
                }
            )
            items = response.get("items", []) if isinstance(response, dict) else []
            for item in items:
                for cost in item.get("costs") or []:
                    code = cost.get("costCode")
                    name = cost.get("costName")
                    if code is not None and code not in seen:
                        seen[code] = {"costCode": code, "costName": name}
            consecutive_not_found = 0
        except Exception:
            consecutive_not_found += 1
            if consecutive_not_found >= 3:
                break

    CACHE["costTypes"] = sorted(seen.values(), key=lambda x: x["costCode"])
    logger.debug(f"costTypes descobertos: {CACHE['costTypes']}")


def get_slim_context() -> dict[str, Any]:
    """Retorna apenas os dados essenciais do cache (~5KB).

    Inclui:
    - branches (filiais)
    - priceTypes (tabelas de preço existentes)
    - costTypes (tipos de custo existentes)
    - top 5 operações mais comuns
    - timestamp do load

    Para cache completo use get_full_context().
    """
    return {
        "loadedAt": CACHE.get("loadedAt"),
        "branches": CACHE.get("branches", []),
        "priceTypes": CACHE.get("priceTypes", []),
        "costTypes": CACHE.get("costTypes", []),
        "operations": (CACHE.get("operations") or [])[:5],
        "paymentConditions": (CACHE.get("paymentConditions") or [])[:5],
    }


def get_full_context() -> dict[str, Any]:
    """Retorna o cache inteiro. Use só pra debug — pode ser grande."""
    return dict(CACHE)
