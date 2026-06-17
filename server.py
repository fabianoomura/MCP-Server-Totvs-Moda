"""
TOTVS Moda MCP Server v3.10.0
=============================
MCP server para API V2 do TOTVS Moda.
15 módulos | 200+ tools | OAuth2 ROPC

Author: ATL4S
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from totvs_client import TotvsClient
import context_cache
from tools.sales_order import SalesOrderTools
from tools.product import ProductTools
from tools.person import PersonTools
from tools.accounts_receivable import AccountsReceivableTools
from tools.fiscal import FiscalTools
from tools.general import GeneralTools
from tools.account_payable import AccountPayableTools
from tools.purchase_order import PurchaseOrderTools
from tools.seller import SellerTools
from tools.voucher import VoucherTools
from tools.other_modules import ManagementTools, GlobalTools, ProductionOrderTools
from tools.data_package import DataPackageTools
from tools.image import ImageTools
from tools.logistics import LogisticsTools
from tools.aggregators import AggregatorTools
from tools.product_engineering import ProductEngineeringTools
from tools.material_request import MaterialRequestTools
from tools.product_prototype import ProductPrototypeTools
from tools.analytics import AnalyticsTools
import usage_tracker
import usage_analyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("totvs-moda-mcp")

server = Server("totvs-moda-mcp")

_client: TotvsClient | None = None
_modules: dict[str, Any] = {}
ANALYTICS_ENABLED = os.environ.get("TOTVS_ENABLE_ANALYTICS", "").lower() in {"1", "true", "yes", "sim"}
_dotenv_loaded = False

WRITE_TOOL_ANNOTATIONS: dict[str, bool] = {
    "destructiveHint": True,
    "idempotentHint": False,
    "readOnlyHint": False,
    "openWorldHint": True,
}


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "sim"}


def _max_response_items() -> int:
    """Max items[] length before truncation. 0 = unlimited."""
    val = os.environ.get("TOTVS_MAX_RESPONSE_ITEMS", "").strip()
    return int(val) if val else 500


def _truncate_response(result: Any) -> Any:
    """Truncate items[] in responses that exceed the configured limit.

    Adds _truncated=True and _totalItems so the LLM knows data was cut.
    Preserves pagination metadata (totalHits, page, pageSize, hasNext).
    """
    limit = _max_response_items()
    if limit <= 0 or not isinstance(result, dict):
        return result
    items = result.get("items")
    if not isinstance(items, list) or len(items) <= limit:
        return result
    total = len(items)
    truncated = dict(result)
    truncated["items"] = items[:limit]
    truncated["_truncated"] = True
    truncated["_totalItems"] = total
    return truncated


def _load_dotenv_once() -> None:
    """Load a local .env file without adding a runtime dependency.

    Default behavior is conservative: .env only fills missing variables.
    Set TOTVS_DOTENV_OVERRIDE=true to force .env to replace inherited env vars.
    Set TOTVS_ENV_FILE to point at a specific file when the MCP client starts
    from a different working directory.
    """
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True

    explicit = os.environ.get("TOTVS_ENV_FILE", "").strip()
    candidates = [Path(explicit)] if explicit else [Path.cwd() / ".env", Path(__file__).resolve().parent / ".env"]
    env_path = next((path for path in candidates if path and path.exists()), None)
    if not env_path:
        return

    override = _truthy_env("TOTVS_DOTENV_OVERRIDE")
    loaded: list[str] = []
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not key:
                continue
            if override or not os.environ.get(key):
                os.environ[key] = value
                loaded.append(key)
        if loaded:
            logger.info("Loaded TOTVS env keys from %s: %s", env_path, ", ".join(sorted(loaded)))
    except OSError as exc:
        logger.warning("Failed to load TOTVS_ENV_FILE/.env: %s", exc)


def get_client() -> TotvsClient:
    global _client
    if _client is None:
        _load_dotenv_once()
        _client = TotvsClient(
            base_url=os.environ["TOTVS_BASE_URL"],
            client_id=os.environ["TOTVS_CLIENT_ID"],
            client_secret=os.environ["TOTVS_CLIENT_SECRET"],
            username=os.environ["TOTVS_USERNAME"],
            password=os.environ["TOTVS_PASSWORD"],
        )
    return _client


def get_modules() -> dict[str, Any]:
    global _modules
    if not _modules:
        c = get_client()
        _modules = {
            "sales_order":         SalesOrderTools(c),
            "product":             ProductTools(c),
            "person":              PersonTools(c),
            "accounts_receivable": AccountsReceivableTools(c),
            "fiscal":              FiscalTools(c),
            "general":             GeneralTools(c),
            "account_payable":     AccountPayableTools(c),
            "purchase_order":      PurchaseOrderTools(c),
            "seller":              SellerTools(c),
            "voucher":             VoucherTools(c),
            "management":          ManagementTools(c),
            "global":              GlobalTools(c),
            "production_order":    ProductionOrderTools(c),
            "data_package":        DataPackageTools(c),
            "image":               ImageTools(c),
            "logistics":           LogisticsTools(c),
            "aggregators":         AggregatorTools(c),
            "product_engineering": ProductEngineeringTools(c),
            "material_request":     MaterialRequestTools(c),
            "product_prototype":    ProductPrototypeTools(c),
            "analytics":            AnalyticsTools(c),
        }
    return _modules


# ---------------------------------------------------------------------------
# Instructions builder
# ---------------------------------------------------------------------------

def _build_instructions() -> str:
    """Monta guia de uso do servidor MCP.

    Lê TOTVS_OPERATION_CONTEXT do ambiente para injetar contexto específico
    da empresa (ex: significado real dos status de pedido, fluxo operacional).
    """
    operation_context = os.environ.get("TOTVS_OPERATION_CONTEXT", "").strip()

    default_status = (
        "Os status do TOTVS são genéricos — o significado real varia por operação.\n"
        "Status padrão: Blocked=bloqueado, InProgress=em andamento, "
        "InAnalysis=em análise, InComposition=em composição, "
        "Attended=faturado/atendido, Canceled=cancelado.\n"
        "Consulte o gestor da empresa para entender o fluxo real antes de interpretar os dados."
    )

    status_section = operation_context if operation_context else default_status

    return f"""# TOTVS Moda MCP Server — Guia de uso

## Regra fundamental
TODAS as consultas e operações no TOTVS devem ser feitas via tools MCP disponíveis.
Não crie scripts Python, não use requests/httpx diretamente, não tente acessar a API manualmente.
Se uma informação não estiver disponível via tools, informe ao usuário em vez de improvisar.

## Como começar
1. Chame `totvs_get_context` para ver filiais, tabelas de preço/custo e operações da empresa
2. Use as datas no formato ISO 8601 (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)
3. Use o parâmetro `fields` nas buscas para reduzir tokens: ex. `fields=['orderCode','customerName','totalValue']`

## Validação de conexão e autenticação
- `totvs_get_context` pode retornar dados de cache carregados no startup; ele NÃO prova que a autenticação em tempo real ainda está válida.
- Se `totvs_get_context` funcionar mas outras tools retornarem `InvalidUserPassword`, trate como configuração/ambiente do processo MCP, não como falha da pergunta.
- Nesse caso, peça para reiniciar o MCP Server/cliente e conferir se `TOTVS_USERNAME` e `TOTVS_PASSWORD` do mcp.json/env são os mesmos do `.env` esperado.
- Se o cliente MCP estiver usando credenciais antigas, configure `TOTVS_ENV_FILE` com o caminho absoluto do `.env` correto e `TOTVS_DOTENV_OVERRIDE=true`, depois reinicie o MCP.
- Para validar conexão real, use uma consulta read-only pequena, por exemplo `totvs_sales_today_summary` com `topN=1` ou uma busca paginada com `pageSize=1`.
- Não entre em loop tentando tools de cliente/produto quando a API retornar erro de autenticação.

## Tools por categoria

### Regra de escolha para vendas
- Perguntas como "vendas de hoje", "o que vendi hoje", "traga as vendas de hj", "resumo de vendas" ou "quanto vendi" devem usar `totvs_sales_today_summary`.
- Se o usuario pedir vendas + financeiro do dia, use `totvs_daily_dashboard`.
- NUNCA use `totvs_get_person_statistics` para responder vendas gerais; essa tool e apenas para um cliente especifico ja identificado.

### Pedidos de venda
- `totvs_search_orders` — busca por data, status, cliente, código. Use `expand='items'` APENAS quando precisar dos produtos
- `totvs_orders_by_status_summary` — distribuição de pedidos por status (quantos bloqueados, faturados etc.)
- `totvs_sales_summary_by_period` — faturamento agregado por filial, status ou dia
- `totvs_top_customers` — ranking de clientes por faturamento no período
- `totvs_create_order` — cria pedido de venda
- `totvs_change_order_status` — altera status do pedido
- `totvs_cancel_order` — cancela pedido (irreversível)
- `totvs_add_order_items` / `totvs_remove_order_item` — adiciona/remove itens

### Produtos
- `totvs_search_products` — busca por nome, referência, código
- `totvs_get_product` — dados completos de um produto
- `totvs_search_product_prices` — preços por tabela (requer `priceCodeList` — veja em `totvs_get_context`)
- `totvs_search_product_costs` — custos: `costCodeList=[1]`=reposição, `[2]`=última compra
- `totvs_search_product_balances` — saldo em estoque por filial/grade
- `totvs_update_product_price_only` — atualiza preço de venda
- `totvs_update_product_cost` — atualiza custo
- `totvs_update_product_simple` — atualiza dados básicos (peso, NCM, flags)
- `totvs_get_products_sold` — ranking de produtos mais vendidos no período

### Clientes
- `totvs_search_individual_customers` — PF por nome ou CPF
- `totvs_search_legal_customers` — PJ por nome ou CNPJ
- `totvs_get_person_statistics` — histórico de UM cliente específico: total comprado, ticket médio, primeira/última compra. Não use para vendas gerais/de hoje.
- `totvs_create_or_update_individual_customer` — cadastra/atualiza PF
- `totvs_create_or_update_legal_customer` — cadastra/atualiza PJ

### Financeiro (contas a receber)
- `totvs_search_receivable_documents` — títulos a receber com filtros por vencimento. Use `withStatusFlags=true` para separar venda x recebimento (`billingSide`) e ver aberto x recebido sem somar em dobro
- `totvs_get_bank_slip` — boleto bancário
- `totvs_get_payment_link` — link de pagamento
- `totvs_search_customer_financial_balance` — saldo financeiro do cliente

### Fiscal
- `totvs_search_fiscal_invoices` — NF-e emitidas
- `totvs_get_nfe_xml` — XML da NF-e
- `totvs_get_danfe` — DANFE em PDF: salva o arquivo na pasta de saída (`TOTVS_OUTPUT_DIR`, default Downloads) e retorna o caminho; `returnBase64=true` para o base64 cru

### Estoque / Logística
- `totvs_low_stock_alert` — produtos abaixo de saldo mínimo
- `totvs_stock_available` — **todos os produtos com estoque > 0 (já filtrado, pronta entrega)**
- `totvs_get_kardex_movement` — movimentações de estoque
- `totvs_create_material_movement` — movimentação de material

### Painéis rápidos (1 chamada = resposta completa)
- `totvs_daily_dashboard` — **vendas + receber + pagar do dia, tudo junto**
- `totvs_customer_360` — **dados + histórico + recompra do cliente, tudo junto**
- `totvs_product_360` — **produto + estoque + preço + custo + ficha técnica**
- `totvs_raw_material_360` — **matéria-prima + saldo/custo + usos na ficha**
- `totvs_order_360` — **pedido + itens + notas + pendências**
- `totvs_invoice_360` — **NF + produtos da nota**
- `totvs_sales_today_summary` — **vendas do dia já agregadas**
- `totvs_new_customers_today` — **clientes novos do dia por primeira compra**
- `totvs_open_purchase_orders` — **pedidos de compra em aberto, paginado em paralelo**
- `totvs_open_production_orders` — **ordens de produção em aberto, paginado em paralelo**

## Fluxo de status de pedidos
{status_section}

## Dicas importantes
- Tools marcadas com ⚠️ ESCRITA modificam dados no ERP — confirme com o usuário antes de executar
- `totvs_get_context` retorna os `priceCode` e `costCode` válidos para esta empresa
- **PREFIRA tools compostas** para respostas rápidas: `totvs_daily_dashboard` em vez de sales+receivable+payable separados
- **PREFIRA `totvs_customer_360`** em vez de buscar pedidos do cliente manualmente
- **PREFIRA `totvs_product_360`** para dados completos de produto
- **PREFIRA `totvs_order_360`** para dados completos de pedido
- **PREFIRA `totvs_invoice_360`** para dados completos de NF
- **PREFIRA `totvs_sales_today_summary`** para vendas de hoje
- **PREFIRA `totvs_new_customers_today`** para clientes novos hoje
- **PREFIRA `totvs_stock_available`** em vez de paginar todos os saldos
- **PREFIRA `totvs_open_purchase_orders`** para pedidos de compra em aberto
- **PREFIRA `totvs_open_production_orders`** para ordens de produção em aberto
- Para agregar vendas por produto use `totvs_get_products_sold` (não busque pedidos e some manualmente)
- Para ranking de clientes use `totvs_top_customers` (não busque pedidos e some manualmente)

## Convenções importantes (v3.11+)
- **Datas de "dia"**: para "vence hoje", "emitidas hoje" etc., pode passar a MESMA data em início e fim (ou só uma data) — a tool expande para o dia inteiro automaticamente (não precisa montar `00:00:00`/`23:59:59`).
- **Arquivos grandes (DANFE/imagem)**: `totvs_get_danfe` e `totvs_search_product_images` salvam o arquivo na pasta de saída (`TOTVS_OUTPUT_DIR`, default Downloads) e retornam o caminho, em vez do base64 (que estoura o limite de tokens). Use `returnBase64=true` se precisar do conteúdo cru.
- **Contas a receber sem somar em dobro**: a busca retorna o lado VENDA (a receber, `billingType` 1/2) e o lado RECEBIMENTO (caixa, 3/4) — não some os dois. Passe `withStatusFlags=true` para receber `billingSide`, `isOpen`/`isSettled`/`openValue` e o `receivableSummary {open, settled, receiptSide}`.
- **Campos (`fields=`)**: se um nome não existir na resposta, vem um aviso em `_fieldsWarning`. Nomes que costumam confundir (ex.: `totalValue` x `value`, status da NF em `eletronic.electronicInvoiceStatus`, valor de item em `netValue`) estão documentados em `docs/FIELDS.md`.
"""


def _build_connect_instructions() -> str:
    """Instruções curtas entregues ao cliente MCP no handshake de conexão.

    Ao contrário de `_build_instructions()` (guia completo, sob demanda via
    `totvs_get_instructions`), este texto é injetado automaticamente no campo
    `instructions` do `initialize` e fica sempre visível para o LLM. Por isso
    é deliberadamente enxuto: regras fundamentais + ponteiros para o resto.
    """
    return (
        "# TOTVS Moda MCP — leia antes de usar\n\n"
        "Servidor MCP para a API V2 do TOTVS Moda (ERP de confecção/moda). "
        "Permite consultar e operar pedidos, produtos, clientes, financeiro, "
        "fiscal, estoque e produção via tools.\n\n"
        "## Regras fundamentais\n"
        "1. TUDO no TOTVS deve passar pelas tools MCP. Não escreva scripts, não "
        "use requests/httpx, não invente endpoints. Se algo não existe como tool, "
        "diga isso ao usuário em vez de improvisar.\n"
        "2. Leituras (search, get, dashboards, visões 360) podem rodar direto. "
        "Operações de ESCRITA — criar, alterar, cancelar, baixar, estornar, "
        "remover — exigem confirmação explícita do usuário antes de executar. "
        "Essas tools têm `⚠️ ESCRITA` na descrição.\n"
        "3. PREFIRA tools compostas a montar a resposta na mão: "
        "`totvs_daily_dashboard`, `totvs_customer_360`, `totvs_product_360`, "
        "`totvs_order_360`, `totvs_invoice_360`, `totvs_sales_today_summary`, "
        "`totvs_stock_available`.\n"
        "4. Use `fields=[...]` nas buscas para reduzir tokens e datas em ISO 8601.\n"
        "5. Convenções v3.11: filtros de \"dia\" aceitam uma data única (ex.: vence hoje); "
        "`totvs_get_danfe` e `totvs_search_product_images` salvam arquivo (pasta de saída, "
        "default Downloads) e retornam o caminho (`returnBase64=true` para o cru); em contas "
        "a receber use `withStatusFlags=true` para separar venda x recebimento e não somar em "
        "dobro. Campos que confundem em `docs/FIELDS.md`.\n\n"
        "## Como começar\n"
        "1. Chame `totvs_get_context` para descobrir filiais, tabelas de preço/custo "
        "e operações desta empresa (os códigos variam por empresa — não chute).\n"
        "2. Chame `totvs_get_instructions` para o guia completo: tools por "
        "categoria, regra de escolha para vendas, status de pedido e validação "
        "de conexão/autenticação.\n\n"
        "Observação: `totvs_get_context` pode vir de cache do startup e não prova "
        "autenticação em tempo real. Se ele funcionar mas outra tool retornar "
        "`InvalidUserPassword`, trate como configuração de ambiente do processo "
        "MCP, não como falha da pergunta."
    )


# ---------------------------------------------------------------------------
# Tools — aggregated from domain modules (schemas live in tools/*.py)
# ---------------------------------------------------------------------------

from tools.sales_order import TOOLS as _SALES_ORDER_TOOLS, ROUTES as _SALES_ORDER_ROUTES
from tools.product import TOOLS as _PRODUCT_TOOLS, ROUTES as _PRODUCT_ROUTES
from tools.product_engineering import TOOLS as _PRODUCT_ENG_TOOLS, ROUTES as _PRODUCT_ENG_ROUTES
from tools.material_request import TOOLS as _MATERIAL_REQ_TOOLS, ROUTES as _MATERIAL_REQ_ROUTES
from tools.product_prototype import TOOLS as _PROTOTYPE_TOOLS, ROUTES as _PROTOTYPE_ROUTES
from tools.logistics import TOOLS as _LOGISTICS_TOOLS, ROUTES as _LOGISTICS_ROUTES
from tools.person import TOOLS as _PERSON_TOOLS, ROUTES as _PERSON_ROUTES
from tools.accounts_receivable import TOOLS as _AR_TOOLS, ROUTES as _AR_ROUTES
from tools.fiscal import TOOLS as _FISCAL_TOOLS, ROUTES as _FISCAL_ROUTES
from tools.general import TOOLS as _GENERAL_TOOLS, ROUTES as _GENERAL_ROUTES
from tools.account_payable import TOOLS as _AP_TOOLS, ROUTES as _AP_ROUTES
from tools.purchase_order import TOOLS as _PO_TOOLS, ROUTES as _PO_ROUTES
from tools.seller import TOOLS as _SELLER_TOOLS, ROUTES as _SELLER_ROUTES
from tools.voucher import TOOLS as _VOUCHER_TOOLS, ROUTES as _VOUCHER_ROUTES
from tools.other_modules import (
    MANAGEMENT_TOOLS as _MGMT_TOOLS, MANAGEMENT_ROUTES as _MGMT_ROUTES,
    GLOBAL_TOOLS as _GLOBAL_TOOLS, GLOBAL_ROUTES as _GLOBAL_ROUTES,
    PRODUCTION_ORDER_TOOLS as _PRODORD_TOOLS, PRODUCTION_ORDER_ROUTES as _PRODORD_ROUTES,
)
from tools.image import TOOLS as _IMAGE_TOOLS, ROUTES as _IMAGE_ROUTES
from tools.data_package import TOOLS as _DPKG_TOOLS, ROUTES as _DPKG_ROUTES
from tools.aggregators import TOOLS as _AGG_TOOLS, ROUTES as _AGG_ROUTES


# -- Special tools (handled inline in handle_call_tool) --------------------

_SPECIAL_TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_get_instructions",
        description=(
            "LEIA ISTO PRIMEIRO em uma nova conversa sobre o TOTVS. "
            "Retorna guia completo: quais tools usar para cada tarefa, fluxo de status de pedidos, "
            "contexto operacional da empresa, e dicas de uso. "
            "Chame antes de qualquer outra tool quando não souber por onde começar."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="totvs_get_context",
        description=(
            "Retorna dados de referência da empresa: filiais, tabelas de preço/custo "
            "EXISTENTES, operações, condições de pagamento. "
            "Pode vir de cache; NÃO use como prova de autenticação em tempo real. "
            "Se outras tools retornarem InvalidUserPassword, reinicie o MCP e confira env/mcp.json. "
            "Por padrão retorna SLIM (~5KB com top 5 de cada lista). "
            "Use verbose=true pra retornar tudo (pode ser grande, ~50-300KB). "
            "Use isto pra descobrir priceCode/costCode válidos antes de chamar "
            "totvs_search_prices ou totvs_update_product_price_only."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "verbose": {
                    "type": "boolean",
                    "default": False,
                    "description": "Se true, retorna cache completo. Default: slim."
                }
            }
        }
    ),
    types.Tool(name="totvs_get_usage_insights", description="Análise de padrões de uso do MCP server. Retorna: tools mais usadas, sequências frequentes, horários de pico, padrões de parâmetros e sugestões de otimização. Use para entender como o sistema está sendo utilizado e onde otimizar. Dados locais, sem chamada externa.",
        inputSchema={"type":"object","properties":{
            "days":{"type":"integer","description":"Dias para análise (default 30)","default":30}
        }}),
]

# -- Build a name→Tool index from all modules -----------------------------

_ALL_MODULE_TOOLS: dict[str, types.Tool] = {}
for _tlist in (
    _SALES_ORDER_TOOLS, _PRODUCT_TOOLS, _PRODUCT_ENG_TOOLS, _MATERIAL_REQ_TOOLS,
    _PROTOTYPE_TOOLS, _LOGISTICS_TOOLS, _PERSON_TOOLS, _AR_TOOLS, _FISCAL_TOOLS,
    _GENERAL_TOOLS, _AP_TOOLS, _PO_TOOLS, _SELLER_TOOLS, _VOUCHER_TOOLS,
    _MGMT_TOOLS, _GLOBAL_TOOLS, _PRODORD_TOOLS, _IMAGE_TOOLS, _DPKG_TOOLS,
    _AGG_TOOLS, _SPECIAL_TOOLS,
):
    for _t in _tlist:
        _ALL_MODULE_TOOLS[_t.name] = _t

# Canonical order — must match the pre-refactor TOOLS list exactly.
# This list is the single source of truth for tool exposure order.
_TOOL_ORDER: list[str] = [
    "totvs_search_orders",
    "totvs_get_order_invoices",
    "totvs_get_pending_items",
    "totvs_get_billing_suggestions",
    "totvs_cancel_order",
    "totvs_change_order_status",
    "totvs_update_order_items_price",
    "totvs_add_order_items",
    "totvs_remove_order_item",
    "totvs_cancel_order_items",
    "totvs_change_order_item_quantity",
    "totvs_update_order_items_additional",
    "totvs_add_order_observation",
    "totvs_update_order_shipping",
    "totvs_update_order_additional",
    "totvs_search_batch_items",
    "totvs_get_changed_batch_items",
    "totvs_create_order_relationship_counts",
    "totvs_create_pdv_transaction",
    "totvs_create_order_relationship_batch_items",
    "totvs_suggest_order_batch_items_by_nuance",
    "totvs_create_order",
    "totvs_update_order_header",
    "totvs_get_order_classifications",
    "totvs_get_discount_types",
    "totvs_search_products",
    "totvs_get_product",
    "totvs_search_product_balances",
    "totvs_search_product_prices",
    "totvs_search_price_tables",
    "totvs_search_product_references",
    "totvs_get_product_grid",
    "totvs_search_product_colors",
    "totvs_search_product_batch",
    "totvs_get_kardex_movement",
    "totvs_search_product_compositions",
    "totvs_get_product_additional_field_types",
    "totvs_get_product_classification_types",
    "totvs_get_product_composition_group_product",
    "totvs_get_product_composition_product",
    "totvs_get_product_instruction_items",
    "totvs_get_product_price_table_scales",
    "totvs_get_product_grouper_configurations",
    "totvs_search_consumption_sheet",
    "totvs_search_engineering_services",
    "totvs_get_engineering_operations",
    "totvs_search_engineering_applications",
    "totvs_search_engineering_default",
    "totvs_get_engineering_configurations",
    "totvs_create_engineering_references",
    "totvs_search_material_requests",
    "totvs_create_material_request",
    "totvs_add_material_request_items",
    "totvs_modify_material_request_header",
    "totvs_modify_material_request_items",
    "totvs_remove_material_request_items",
    "totvs_cancel_material_request_items",
    "totvs_approve_material_request",
    "totvs_move_material_request_items",
    "totvs_search_product_prototypes",
    "totvs_create_product_prototype",
    "totvs_update_product_prototype",
    "totvs_search_product_storage",
    "totvs_upsert_product_packaging",
    "totvs_add_product_packaging_quantity",
    "totvs_subtract_product_packaging_quantity",
    "totvs_create_product_classification",
    "totvs_create_product_value",
    "totvs_update_product_price",
    "totvs_update_product_price_only",
    "totvs_update_product_cost",
    "totvs_update_promotion_price",
    "totvs_search_product_codes",
    "totvs_search_product_costs",
    "totvs_get_product_category",
    "totvs_get_product_classifications",
    "totvs_get_measurement_units",
    "totvs_search_omni_changed_balances",
    "totvs_update_product_data",
    "totvs_update_product_simple",
    "totvs_update_product_branch_info_batch",
    "totvs_create_product_barcode",
    "totvs_update_barcode",
    "totvs_create_reference",
    "totvs_create_classification_type",
    "totvs_create_product_batch",
    "totvs_update_product_batch_info",
    "totvs_create_product_batch_preferential_sales_order",
    "totvs_upsert_product_color",
    "totvs_create_product_grid",
    "totvs_search_individual_customers",
    "totvs_search_legal_customers",
    "totvs_get_customer_bonus_balance",
    "totvs_get_person_statistics",
    "totvs_create_or_update_individual_customer",
    "totvs_create_or_update_legal_customer",
    "totvs_get_branches_list",
    "totvs_search_representatives",
    "totvs_get_person_classifications",
    "totvs_remove_person_classification_relationship",
    "totvs_get_email_types",
    "totvs_get_phone_types",
    "totvs_get_contact_types",
    "totvs_search_reception_sale",
    "totvs_consume_bonus",
    "totvs_create_person_message",
    "totvs_relate_customer_representatives",
    "totvs_change_person_message",
    "totvs_search_customer_financial_balance",
    "totvs_search_receivable_documents",
    "totvs_get_bank_slip",
    "totvs_get_payment_link",
    "totvs_get_gift_check_balances",
    "totvs_change_charge_type",
    "totvs_create_receivable_invoice",
    "totvs_settle_invoices",
    "totvs_pay_invoices",
    "totvs_move_gift_check",
    "totvs_upsert_invoice_commission",
    "totvs_create_gift_check",
    "totvs_search_fiscal_invoices",
    "totvs_get_nfe_xml",
    "totvs_get_invoice_item_detail",
    "totvs_get_danfe",
    "totvs_search_invoice_products",
    "totvs_get_cost_center",
    "totvs_get_digital_certificates",
    "totvs_get_pending_conditional_products",
    "totvs_get_disabled_invoices",
    "totvs_print_transaction",
    "totvs_create_nfe_manifestation",
    "totvs_get_payment_conditions",
    "totvs_get_operations",
    "totvs_simulate_payment_plan",
    "totvs_search_devolutions",
    "totvs_get_payment_plans",
    "totvs_get_transactions",
    "totvs_search_transactions",
    "totvs_get_classifications",
    "totvs_create_devolution",
    "totvs_create_transaction",
    "totvs_create_product_count",
    "totvs_create_financial_compensation",
    "totvs_add_product_count_additional_count",
    "totvs_create_relationship_counts",
    "totvs_create_transaction_classification_relationship",
    "totvs_search_payable_duplicates",
    "totvs_search_commissions_paid",
    "totvs_create_duplicate",
    "totvs_group_duplicates",
    "totvs_search_purchase_orders",
    "totvs_create_purchase_order",
    "totvs_cancel_purchase_order",
    "totvs_change_purchase_order_status",
    "totvs_link_purchase_order_batch",
    "totvs_update_purchase_order_item_quantities",
    "totvs_search_sellers",
    "totvs_get_seller_operational_area",
    "totvs_get_seller_operational_area_state",
    "totvs_get_seller_area_by_cep",
    "totvs_get_seller_area_by_city",
    "totvs_search_voucher",
    "totvs_create_voucher",
    "totvs_get_users",
    "totvs_get_global_parameters",
    "totvs_get_branch_parameters",
    "totvs_get_cep",
    "totvs_get_countries",
    "totvs_get_states",
    "totvs_get_cities",
    "totvs_search_production_orders",
    "totvs_get_pending_material_consumption",
    "totvs_create_material_movement",
    "totvs_search_product_images",
    "totvs_upload_product_image",
    "totvs_import_image_no_link",
    "totvs_upload_person_image",
    "totvs_list_person_images",
    "totvs_get_person_image_base64",
    "totvs_update_voucher",
    "totvs_create_customer_vouchers",
    "totvs_list_input_packages",
    "totvs_get_package",
    "totvs_get_package_content",
    "totvs_list_output_packages",
    "totvs_create_input_package",
    "totvs_receive_output_package",
    "totvs_reactivate_package",
    "totvs_get_instructions",
    "totvs_get_context",
    "totvs_get_products_sold",
    "totvs_sales_summary_by_period",
    "totvs_top_customers",
    "totvs_low_stock_alert",
    "totvs_orders_by_status_summary",
    "totvs_daily_dashboard",
    "totvs_customer_360",
    "totvs_stock_available",
    "totvs_product_360",
    "totvs_raw_material_360",
    "totvs_order_360",
    "totvs_invoice_360",
    "totvs_sales_today_summary",
    "totvs_new_customers_today",
    "totvs_sales_by_representative",
    "totvs_sales_by_channel",
    "totvs_overdue_financial_summary",
    "totvs_cash_flow_forecast",
    "totvs_product_stock_by_kind_summary",
    "totvs_open_purchase_orders",
    "totvs_open_production_orders",
    "totvs_get_usage_insights",
]

TOOLS: list[types.Tool] = [_ALL_MODULE_TOOLS[name] for name in _TOOL_ORDER]

# Optional analytics tool (gated by env var)
if ANALYTICS_ENABLED:
    _analytics_tool = types.Tool(
        name="totvs_analytics_call",
        description=(
            "Gateway opcional para Analytics/painel do TOTVS Moda. "
            "Use somente quando TOTVS_ENABLE_ANALYTICS=true e o modulo estiver contratado. "
            "Informe endpoint, params para GET ou body para POST. Use fields para reduzir retorno."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "Chave do endpoint em tools.analytics.ENDPOINTS, ex. financial_panel_v2_total_payable_search.",
                },
                "params": {"type": "object", "description": "Query params para endpoints GET."},
                "body": {"type": "object", "description": "Body JSON para endpoints POST."},
                "fields": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["endpoint"],
        },
    )
    TOOLS.append(_analytics_tool)


# ---------------------------------------------------------------------------
# Routing table — aggregated from domain modules
# ---------------------------------------------------------------------------

ROUTING: dict[str, tuple[str, str]] = {}
for _module_key, _routes in (
    ("sales_order", _SALES_ORDER_ROUTES),
    ("product", _PRODUCT_ROUTES),
    ("product_engineering", _PRODUCT_ENG_ROUTES),
    ("material_request", _MATERIAL_REQ_ROUTES),
    ("product_prototype", _PROTOTYPE_ROUTES),
    ("logistics", _LOGISTICS_ROUTES),
    ("person", _PERSON_ROUTES),
    ("accounts_receivable", _AR_ROUTES),
    ("fiscal", _FISCAL_ROUTES),
    ("general", _GENERAL_ROUTES),
    ("account_payable", _AP_ROUTES),
    ("purchase_order", _PO_ROUTES),
    ("seller", _SELLER_ROUTES),
    ("voucher", _VOUCHER_ROUTES),
    ("management", _MGMT_ROUTES),
    ("global", _GLOBAL_ROUTES),
    ("production_order", _PRODORD_ROUTES),
    ("image", _IMAGE_ROUTES),
    ("data_package", _DPKG_ROUTES),
    ("aggregators", _AGG_ROUTES),
):
    for _tool_name, _method_name in _routes.items():
        ROUTING[_tool_name] = (_module_key, _method_name)

if ANALYTICS_ENABLED:
    ROUTING["totvs_analytics_call"] = ("analytics", "call_endpoint")

SPECIAL_TOOL_NAMES = {
    "totvs_get_instructions",
    "totvs_get_context",
    "totvs_get_usage_insights",
}

VENDOR_PROFILE_TOOLS = {
    "totvs_search_orders",
    "totvs_get_order_invoices",
    "totvs_get_pending_items",
    "totvs_get_billing_suggestions",
    "totvs_get_order_classifications",
    "totvs_get_discount_types",
    "totvs_search_batch_items",
    "totvs_get_changed_batch_items",
    "totvs_search_products",
    "totvs_get_product",
    "totvs_search_product_balances",
    "totvs_search_product_prices",
    "totvs_search_price_tables",
    "totvs_search_product_references",
    "totvs_get_product_grid",
    "totvs_search_product_colors",
    "totvs_search_product_batch",
    "totvs_search_product_codes",
    "totvs_search_product_costs",
    "totvs_get_product_category",
    "totvs_get_product_classifications",
    "totvs_get_measurement_units",
    "totvs_search_individual_customers",
    "totvs_search_legal_customers",
    "totvs_get_customer_bonus_balance",
    "totvs_get_person_statistics",
    "totvs_search_representatives",
    "totvs_sales_today_summary",
    "totvs_customer_360",
    "totvs_product_360",
    "totvs_stock_available",
    "totvs_order_360",
    "totvs_sales_by_representative",
    "totvs_sales_by_channel",
    "totvs_top_customers",
}

FINANCIAL_PROFILE_MODULES = {
    "accounts_receivable",
    "account_payable",
    "fiscal",
}

FINANCIAL_PROFILE_EXTRA_TOOLS = {
    "totvs_customer_360",
    "totvs_daily_dashboard",
    "totvs_invoice_360",
    "totvs_overdue_financial_summary",
    "totvs_cash_flow_forecast",
    "totvs_search_voucher",
}


def _tool_names_from_env(name: str) -> set[str]:
    raw = os.environ.get(name, "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def _write_tool_names() -> set[str]:
    return {tool.name for tool in TOOLS if getattr(tool, "annotations", None)}


def _profile_tool_names() -> set[str]:
    all_tool_names = {tool.name for tool in TOOLS}
    profile = os.environ.get("TOTVS_PROFILE", "completo").strip().lower() or "completo"

    if profile == "leitura":
        names = all_tool_names - _write_tool_names()
    elif profile == "vendedor":
        names = set(VENDOR_PROFILE_TOOLS) & all_tool_names
    elif profile == "financeiro":
        names = {
            name
            for name, (module_key, _method_name) in ROUTING.items()
            if module_key in FINANCIAL_PROFILE_MODULES
        }
        names |= FINANCIAL_PROFILE_EXTRA_TOOLS & all_tool_names
    elif profile == "gestor":
        names = all_tool_names - _write_tool_names()
    else:
        names = set(all_tool_names)

    names |= _tool_names_from_env("TOTVS_TOOLS_EXTRA") & all_tool_names
    names -= _tool_names_from_env("TOTVS_TOOLS_EXCLUDE")
    names |= SPECIAL_TOOL_NAMES & all_tool_names
    return names


def _enabled_tools() -> list[types.Tool]:
    enabled_names = _profile_tool_names()
    return [tool for tool in TOOLS if tool.name in enabled_names]


def _tool_enabled(name: str) -> bool:
    return name in _profile_tool_names()


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return _enabled_tools()


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    logger.info(f"Tool: {name}")
    t0 = time.time()

    # ── instructions tool ─────────────────────────────────────────────────────
    if name == "totvs_get_instructions":
        usage_tracker.track(name, arguments)
        return [types.TextContent(type="text", text=_build_instructions())]

    # ── context tool ──────────────────────────────────────────────────────────
    if name == "totvs_get_context":
        usage_tracker.track(name, arguments)
        if arguments.get("verbose"):
            result = context_cache.get_full_context()
        else:
            result = context_cache.get_slim_context()
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

    # ── usage insights tool ──────────────────────────────────────────────────
    if name == "totvs_get_usage_insights":
        days = arguments.get("days", 30)
        result = usage_analyzer.analyze(days)
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    if name in {tool.name for tool in TOOLS} and not _tool_enabled(name):
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Tool '{name}' não habilitada no perfil atual."},
                    ensure_ascii=False,
                ),
            )
        ]

    route = ROUTING.get(name)
    if not route:
        return [types.TextContent(type="text", text=json.dumps({"error": f"Tool '{name}' não encontrada."}))]

    module_key, method_name = route
    module = get_modules().get(module_key)

    try:
        result = await getattr(module, method_name)(arguments)
        result = _truncate_response(result)
        duration = (time.time() - t0) * 1000
        usage_tracker.track(name, arguments, duration_ms=duration)
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
    except Exception as exc:
        duration = (time.time() - t0) * 1000
        usage_tracker.track(name, arguments, duration_ms=duration)
        logger.exception(f"Erro: {name}")
        return [types.TextContent(type="text", text=json.dumps({"error": str(exc), "tool": name}, ensure_ascii=False))]


async def main() -> None:
    logger.info(f"TOTVS Moda MCP Server v3.10.0 — {len(TOOLS)} tools | {len(get_modules())} módulos")
    try:
        await context_cache.load_context(get_client())
    except Exception as e:
        logger.warning(f"Falha ao carregar contexto na inicialização: {e}")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            InitializationOptions(
                server_name="totvs-moda-mcp",
                server_version="3.10.0",
                instructions=_build_connect_instructions(),
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
