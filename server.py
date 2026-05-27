"""
TOTVS Moda MCP Server v3.8.0
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
- `totvs_search_receivable_documents` — títulos a receber com filtros por vencimento
- `totvs_get_bank_slip` — boleto bancário
- `totvs_get_payment_link` — link de pagamento
- `totvs_search_customer_financial_balance` — saldo financeiro do cliente

### Fiscal
- `totvs_search_fiscal_invoices` — NF-e emitidas
- `totvs_get_nfe_xml` — XML da NF-e
- `totvs_get_danfe` — DANFE em PDF

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
"""


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

TOOLS: list[types.Tool] = [

    # ── SALES ORDER ──────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_orders", description="Busca pedidos de venda (filtros flexíveis). Retorna: items[] com orderCode, orderDate, branchCode, customerCode, customerName, customerCpfCnpj, orderStatus, totalValue, representativeCode. Cada item em items[] tem: productCode, name, productSku, quantity, price, discount, totalValue. Use expand='items' APENAS quando precisar detalhes dos produtos (resposta fica grande). Para agregar vendas por produto use totvs_get_products_sold. Para resumo por filial/status use totvs_sales_summary_by_period. Para top clientes use totvs_top_customers. Suporta filtro por data, status, cliente, CPF, código de integração Shopify (SHP-XXXX), e expand para itens/NF-e/endereço/observações.",
        inputSchema={"type":"object","properties":{
            "startOrderDate":{"type":"string","description":"Data inicial ISO 8601"},
            "endOrderDate":{"type":"string","description":"Data final ISO 8601"},
            "orderCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos TOTVS do pedido"},
            "integrationCodeList":{"type":"array","items":{"type":"string"},"description":"Códigos de integração ex: SHP-1234"},
            "customerCpfCnpjList":{"type":"array","items":{"type":"string"},"description":"CPF/CNPJ dos clientes"},
            "customerCodeList":{"type":"array","items":{"type":"integer"}},
            "orderStatusList":{"type":"array","items":{"type":"string","enum":["InProgress","BillingReleased","PartiallyAnswered","Attended","Blocked","Canceled","InComposition","InAnalysis"]},"description":"Situação do pedido: InProgress, BillingReleased, PartiallyAnswered, Attended, Blocked, Canceled, InComposition, InAnalysis"},
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos das filiais"},
            "operationCodeList":{"type":"array","items":{"type":"integer"}},
            "representativeCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos dos representantes"},
            "representativeCpfCnpjList":{"type":"array","items":{"type":"string"},"description":"CPF/CNPJ dos representantes"},
            "startBillingForecastDate":{"type":"string"},"endBillingForecastDate":{"type":"string"},
            "hasShippingCompany":{"type":"boolean"},
            "hasPdvTransaction":{"type":"boolean"},
            "hasFinancialProcessed":{"type":"boolean"},
            "classifications":{"type":"array","items":{"type":"object","properties":{"type":{"type":"integer"},"codeList":{"type":"array","items":{"type":"string"}}},"required":["type"]},"description":"Filtro por classificações: [{type, codeList}]"},
            "experienceTypeList":{"type":"array","items":{"type":"string","enum":["Ecommerce","ShipFromStore","ClickAndCollect","PickupStore","InfiniteShelf"]},"description":"Tipo de experiência: Ecommerce, ShipFromStore, ClickAndCollect, PickupStore, InfiniteShelf"},
            "change":{"type":"object","description":"Filtro oficial por alteração de dados"},
            "expand":{"type":"string","description":"items,invoices,shippingAddress,observations,invoiceObservations,representativeObservations,classifications,discounts,commissioneds,counts"},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100,"description":"Máximo 500 no Swagger"},
            "order":{"type":"string","description":"Ordenação suportada: branchCode, orderCode, operationCode, customerCode, maxChangeFilterDate, items, batchItems. Use - para desc."},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Ex: ['orderCode','customerName','totalValue']. Suporta notação aninhada: 'items.productCode'."},
        }}),
    types.Tool(name="totvs_get_order_invoices", description="NF-e vinculadas a um pedido de venda.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"},"orderId":{"type":"string"},"maxChangeFilterDate":{"type":"string"},"invoiceStatusType":{"type":"integer"}}}),
    types.Tool(name="totvs_get_pending_items", description="Itens pendentes de faturamento em um pedido.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"},"orderId":{"type":"string"},"maxChangeFilterDate":{"type":"string"}}}),
    types.Tool(name="totvs_get_billing_suggestions", description="Sugestões de faturamento do TOTVS.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"suggestionCode":{"type":"integer"},"startSuggestionDate":{"type":"string"},"endSuggestionDate":{"type":"string"},"suggestionStatusList":{"type":"array","items":{"type":"integer"}},"orderBranchCode":{"type":"integer"},"orderCode":{"type":"integer"},"startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},"order":{"type":"string"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"expand":{"type":"string"}}}),
    types.Tool(name="totvs_cancel_order", description="⚠️ ESCRITA — Cancela pedido de venda (irreversível). Somente pedidos não aceitos na retaguarda podem ser cancelados.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "orderCode":{"type":"integer"},
            "reasonCancellationCode":{"type":"integer","description":"Código do motivo de cancelamento (obrigatório)"},
            "ReasonCancellationDescription":{"type":"string","description":"Descrição do cancelamento (max 80 chars)"}
        },"required":["branchCode","orderCode","reasonCancellationCode"]},
        annotations=WRITE_TOOL_ANNOTATIONS),
    types.Tool(name="totvs_change_order_status", description="⚠️ ESCRITA — Altera situação do pedido. Aceita apenas valores do enum: InProgress (Em andamento), BillingReleased (Liberado p/ faturamento), Blocked (Bloqueado), InComposition (Em composição), InAnalysis (Em análise).",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "orderCode":{"type":"integer"},
            "statusOrder":{"type":"string","enum":["InProgress","BillingReleased","Blocked","InComposition","InAnalysis"],"description":"Nova situação do pedido"},
            "reasonBlockingCode":{"type":"integer","description":"Código do motivo de bloqueio (apenas para statusOrder=Blocked)"},
            "reasonBlockingDescription":{"type":"string","description":"Descrição do motivo de bloqueio"}
        },"required":["branchCode","orderCode","statusOrder"]},
        annotations=WRITE_TOOL_ANNOTATIONS),
    types.Tool(name="totvs_update_order_items_price", description="⚠️ ESCRITA — Altera preço de itens do pedido.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"},"items":{"type":"array","items":{"type":"object","properties":{"itemSequential":{"type":"integer"},"price":{"type":"number"}},"required":["itemSequential","price"]}}},"required":["branchCode","orderCode","items"]},
        annotations=WRITE_TOOL_ANNOTATIONS),

    # ── SALES ORDER v2.3 (item management) ────────────────────────────────────
    types.Tool(name="totvs_add_order_items", description="⚠️ ESCRITA — Adiciona itens a pedido existente. Informe branchCode+orderCode OU orderId + lista 'items'.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "items":{"type":"array","description":"Lista de itens. Cada item exige: productCode, productSku, quantity, price. Opcionais: originalPrice, discountPercentage, discountValue, billingForecastDate, billingStartDate, customerOrderCode, customerProductCode, rollMeasureCode, sequentials, sequentialsValues, groupObservations, commissioneds.","items":{"type":"object"}}
        },"required":["items"]}),
    types.Tool(name="totvs_remove_order_item", description="⚠️ ESCRITA — Remove item de pedido (DELETE). Identifica item por productCode ou productSku.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "productCode":{"type":"integer"},
            "productSku":{"type":"string"}
        }}),
    types.Tool(name="totvs_cancel_order_items", description="⚠️ ESCRITA — Cancela quantidades de itens do pedido.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "items":{"type":"array","description":"Lista CancelOrderItemModel (productCode, productSku, quantityToCancel, reasonCancellationCode)","items":{"type":"object"}}
        },"required":["items"]}),
    types.Tool(name="totvs_change_order_item_quantity", description="⚠️ ESCRITA — Altera quantidade de itens do pedido.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "items":{"type":"array","description":"Lista UpdateOrderItemQuantityModel (productCode, productSku, newQuantity)","items":{"type":"object"}}
        },"required":["items"]}),
    types.Tool(name="totvs_update_order_items_additional", description="⚠️ ESCRITA — Altera dados adicionais de itens (customerOrderCode, customerProductCode, billingForecastDate etc).",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "items":{"type":"array","items":{"type":"object"}}
        },"required":["items"]}),
    types.Tool(name="totvs_add_order_observation", description="⚠️ ESCRITA — Adiciona observação ao pedido.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "observation":{"type":"string"},
            "visualizationType":{"type":"string","description":"Enum VisualizationObservationType"}
        },"required":["observation"]}),
    types.Tool(name="totvs_update_order_shipping", description="⚠️ ESCRITA — Altera dados de transporte do pedido (transportadora, frete, endereço).",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "shippingCompanyCode":{"type":"integer"},
            "shippingCompanyCpfCnpj":{"type":"string"},
            "redispatchingShippingCompanyCode":{"type":"integer"},
            "redispatchingShippingCompanyCpfCnpj":{"type":"string"},
            "redispatchingFreightType":{"type":"integer"},
            "freightType":{"type":"string","description":"Enum FreitghtType"},
            "freightPercentage":{"type":"number"},
            "freightValue":{"type":"number"},
            "shippingAddress":{"type":"object"}
        }}),
    types.Tool(name="totvs_update_order_additional", description="⚠️ ESCRITA — Altera dados adicionais do pedido (tracking, ecommerce, omni, etc).",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "shippingService":{"type":"string"},
            "trackingId":{"type":"string"},
            "ecommerceStage":{"type":"string"},
            "omniSiteId":{"type":"integer"},
            "compensationDays":{"type":"integer"},
            "anticipationDay":{"type":"integer"},
            "entryType":{"type":"string"},
            "experienceType":{"type":"string"}
        }}),
    types.Tool(name="totvs_search_batch_items", description="Consulta lote de pedidos por status e período de alteração.",
        inputSchema={"type":"object","properties":{
            "status":{"type":"string"},
            "startChangeDate":{"type":"string","description":"ISO 8601"},
            "endChangeDate":{"type":"string"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
            "order":{"type":"string"}
        }}),
    types.Tool(name="totvs_get_changed_batch_items", description="Itens de lote associados a pedidos atualizados.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "batchCode":{"type":"integer"},
            "startDate":{"type":"string"},
            "endDate":{"type":"string"}
        }}),
    types.Tool(name="totvs_create_order_relationship_counts", description="⚠️ ESCRITA — Vincula contagens ao pedido.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "counts":{"type":"array","description":"Lista de contagens (countCode, etc)","items":{"type":"object"}}
        },"required":["counts"]}),
    types.Tool(name="totvs_create_pdv_transaction", description="⚠️ ESCRITA — Grava dados de transação TOTVS Moda PDV no pedido.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "transactions":{"type":"array","items":{"type":"object"}}
        }}),
    types.Tool(name="totvs_create_order_relationship_batch_items", description="⚠️ ESCRITA — Relaciona item de lote ao item do pedido de venda.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "items":{"type":"array","items":{"type":"object"}}
        }}),
    types.Tool(name="totvs_suggest_order_batch_items_by_nuance", description="⚠️ ESCRITA — Sugere e grava relacionamento de lote com item do pedido por nuance de cor.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "items":{"type":"array","items":{"type":"object"}}
        }}),

    types.Tool(name="totvs_create_order", description="⚠️ Cria um pedido de venda B2C.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"customerCode":{"type":"integer"},
            "operationCode":{"type":"integer"},"paymentConditionCode":{"type":"integer"},
            "items":{"type":"array","items":{"type":"object"}},
            "orderDate":{"type":"string"}
        },"required":["branchCode","customerCode","operationCode","items"]}),
    types.Tool(name="totvs_update_order_header", description="⚠️ Altera dados de capa (cabeçalho) do pedido.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"orderCode":{"type":"integer"},
            "paymentConditionCode":{"type":"integer"},"representativeCode":{"type":"integer"},
            "observation":{"type":"string"}
        },"required":["branchCode","orderCode"]}),
    types.Tool(name="totvs_get_order_classifications", description="Classificações de pedido disponíveis.",
        inputSchema={"type":"object","properties":{
            "startChangeDate":{"type":"string"},
            "endChangeDate":{"type":"string"},
            "typeCodeList":{"type":"array","items":{"type":"integer"}},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100}
        }}),
    types.Tool(name="totvs_get_discount_types", description="Tipos de desconto disponíveis para pedido de venda.",
        inputSchema={"type":"object","properties":{
            "startChangeDate":{"type":"string"},
            "endChangeDate":{"type":"string"},
            "order":{"type":"string"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100}
        }}),

    # ── PRODUCT ──────────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_products", description="Busca produtos por filtro. NÃO retorna preço/saldo; use tools específicas. Suporta branchInfo para produto acabado/matéria-prima e expand para dados cadastrais ricos.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "productCodeList":{"type":"array","items":{"type":"integer"}},
            "referenceCodeList":{"type":"array","items":{"type":"string"}},
            "productName":{"type":"string"},
            "groupCodeList":{"type":"array","items":{"type":"string"}},
            "startProductCode":{"type":"integer"},
            "endProductCode":{"type":"integer"},
            "change":{"type":"object","description":"ProductChangeFilterModel. Opções inProduct/inBranchInfo/inPrice/inCost/inStock etc funcionam como OU; demais filtros como E."},
            "branchInfo":{"type":"object","description":"{branchCode,isActive,isFinishedProduct,isRawMaterial,isBulkMaterial,isOwnProduction}"},
            "classifications":{"type":"array","items":{"type":"object"},"description":"[{type, codeList}]"},
            "suppliers":{"type":"array","items":{"type":"object"},"description":"[{code, originalCode}]"},
            "manufacturers":{"type":"array","items":{"type":"object"},"description":"[{code}]"},
            "hasPrice":{"type":"boolean"},"branchPriceCodeList":{"type":"array","items":{"type":"integer"}},"priceCodeList":{"type":"array","items":{"type":"integer"}},
            "hasCost":{"type":"boolean"},"branchCostCodeList":{"type":"array","items":{"type":"integer"}},"costCodeList":{"type":"array","items":{"type":"integer"}},
            "hasStock":{"type":"boolean"},"branchStockCode":{"type":"integer"},"stockCode":{"type":"integer"},
            "hasWebInfo":{"type":"boolean"},
            "option":{"type":"object","description":"ReferenceOptionModel. Default usa branchInfoCode da filial."},
            "expand":{"type":"string","description":"barCodes,classifications,additionalFields,suppliers,manufacturers,additionalColorInformation,referenceCategories,referenceCodeSequences,webData,details,branchesProductBlocked,conservationInstructions"},
            "order":{"type":"string","description":"productSku,referenceCode,colorCode,productSize,productCode,maxChangeFilterDate"},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":1000,"description":"Máximo 1000 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}
        }}),
    types.Tool(name="totvs_get_product", description="Dados completos de um produto/pack pelo código.",
        inputSchema={"type":"object","properties":{"code":{"type":"integer"},"branchCode":{"type":"integer","description":"Código da filial"}},"required":["code"]}),
    types.Tool(name="totvs_search_product_balances", description="Consulta saldos de estoque. Retorna items[] com: productCode, name, productSku, branchCode, balance (quantidade disponível), reservedBalance. Aceita filter.branchCodeList, filter.productCodeList, filter.referenceCodeList. Para alertas de estoque baixo (< threshold) use totvs_low_stock_alert. Use fields=['productCode','balance'] se quiser apenas quantidades.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial (padrão 1)"},
            "stockCodeList":{"type":"array","items":{"type":"integer"},"description":"Tipos de saldo (padrão [1])"},
            "isSalesOrder":{"type":"boolean","description":"Incluir saldo reservado em pedidos de venda"},
            "salesOrderStatusList":{"type":"array","items":{"type":"integer"},"description":"Status de pedido considerados quando isSalesOrder=true"},
            "isTransaction":{"type":"boolean"},
            "isProductionPlanning":{"type":"boolean"},
            "isPurchaseOrder":{"type":"boolean"},
            "isProductionOrder":{"type":"boolean"},
            "cycleProductionPlanningCodeList":{"type":"array","items":{"type":"integer"}},
            "productCodeList":{"type":"array","items":{"type":"integer"}},
            "referenceCodeList":{"type":"array","items":{"type":"string"}},
            "branchInfo":{"type":"object","description":"Filtro por empresa: ativo/acabado/matéria-prima/material consumo"},
            "option":{"type":"object","description":"ProductBalanceOptionModel completo; se informado substitui balances padrão"},
            "expand":{"type":"string","description":"locations"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":1000,"description":"Máximo 1000 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."},
        }}),
    types.Tool(
        name="totvs_search_product_prices",
        description=(
            "Consulta preços de produtos. priceCodeList é OBRIGATÓRIO. "
            "Retorna items[] com prices[]={branchCode, priceCode, priceName, price, "
            "promotionalPrice, promotionalInformation, informationOtherPromotions}. "
            "Para alterar use totvs_update_product_price_only ou totvs_update_product_cost. "
            "Use option.prices=[{branchCode, priceCodeList, isPromotionalPrice, isScheduledPrice}] "
            "pra incluir blocos de promoção/agenda. "
            "Use fields=['productCode','prices.price'] para reduzir tokens."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "productCodeList": {"type": "array", "items": {"type": "integer"}},
                "referenceCodeList": {"type": "array", "items": {"type": "string"}},
                "priceCodeList": {"type": "array", "items": {"type": "integer"},
                    "description": "Códigos de tabela (consulte priceTypes em totvs_get_context)"},
                "branchCodeList": {"type": "array", "items": {"type": "integer"}},
                "change": {
                    "type": "object",
                    "description": "Filtro de alterações no período",
                    "properties": {
                        "startDate": {"type": "string"},
                        "endDate": {"type": "string"},
                        "inProduct": {"type": "boolean"},
                        "inPrice": {"type": "boolean"},
                        "inPromotionalPrice": {"type": "boolean"},
                        "inScheduledPrice": {"type": "boolean"},
                        "inDigitalPromotionPrice": {"type": "boolean"},
                        "branchPriceCodeList": {"type": "array", "items": {"type": "integer"}},
                        "priceCodeList": {"type": "array", "items": {"type": "integer"}}
                    }
                },
                "option": {
                    "type": "object",
                    "description": "Opções de retorno",
                    "properties": {
                        "prices": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "branchCode": {"type": "integer"},
                                    "priceCodeList": {"type": "array", "items": {"type": "integer"}},
                                    "isPromotionalPrice": {"type": "boolean"},
                                    "isScheduledPrice": {"type": "boolean"}
                                }
                            }
                        },
                        "digitalPromotionPrices": {
                            "type": "object",
                            "properties": {
                                "branchCodeList": {"type": "array", "items": {"type": "integer"}},
                                "isInformationOtherDigitalPromotions": {"type": "boolean"}
                            }
                        }
                    }
                },
                "page": {"type": "integer", "default": 1},
                "pageSize": {"type": "integer", "default": 100},
                "fields": {"type": "array", "items": {"type": "string"}}
            }
        }
    ),
    types.Tool(name="totvs_search_price_tables", description="Preços de produtos baseados em tabela de preço. branchCode e priceTableCode são obrigatórios.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial (usado como branchCodeList)"},
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de filiais (alternativa a branchCode)"},
            "priceTableCode":{"type":"integer","description":"Código da tabela de preço"},
            "productCodeList":{"type":"array","items":{"type":"integer"}},
            "referenceCodeList":{"type":"array","items":{"type":"string"}},
            "productName":{"type":"string"},
            "change":{"type":"object"},
            "branchInfo":{"type":"object"},
            "suppliers":{"type":"array","items":{"type":"object"}},
            "manufacturers":{"type":"array","items":{"type":"object"}},
            "classifications":{"type":"array","items":{"type":"object","properties":{"type":{"type":"integer"},"codeList":{"type":"array","items":{"type":"string"}}}},"description":"Filtro por classificação: [{type: 11, codeList: ['7']}]"},
            "option":{"type":"object","description":"PriceTableOptionModel completo"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":1000,"description":"Máximo 1000 no Swagger"},
            "order":{"type":"string","description":"productSku,referenceCode,colorCode,productSize,productCode"},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."},
        },"required":["priceTableCode"]}),
    types.Tool(name="totvs_search_product_references", description="Referências de produtos com grade, cor e composição. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"referenceCodeList":{"type":"array","items":{"type":"string"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
    types.Tool(name="totvs_get_product_grid", description="Grades (tamanhos) disponíveis no TOTVS.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"}}}),
    types.Tool(name="totvs_search_product_colors", description="Cores de produtos. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"colorCodeList":{"type":"array","items":{"type":"integer"}},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
    types.Tool(name="totvs_search_product_batch", description="Lotes de produto. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCodeList":{"type":"array","items":{"type":"integer"}},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
    types.Tool(name="totvs_get_kardex_movement", description="Movimentação kardex (entradas/saídas) de produto.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCode":{"type":"integer"},"startDate":{"type":"string"},"endDate":{"type":"string"}},"required":["branchCode","productCode"]}),
    types.Tool(name="totvs_search_product_compositions", description="Composições de produto por código/fibra. Use expand='fibers'.",
        inputSchema={"type":"object","properties":{"startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},"codeList":{"type":"array","items":{"type":"integer"}},"fibers":{"type":"array","items":{"type":"object"}},"description":{"type":"string"},"fiberDescription":{"type":"string"},"expand":{"type":"string","description":"fibers"},"order":{"type":"string","description":"code,maxChangeFilterDate"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar."}}}),
    types.Tool(name="totvs_get_product_additional_field_types", description="Tipos de campos adicionais de produto. Use para descobrir codigos antes de filtrar ou atualizar dados adicionais.",
        inputSchema={"type":"object","properties":{"startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},"codeList":{"type":"array","items":{"type":"integer"}},"description":{"type":"string"},"order":{"type":"string","description":"code,maxChangeFilterDate"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"}}}}),
    types.Tool(name="totvs_get_product_classification_types", description="Tipos de classificacao de produto disponiveis. Use antes de consultar ou gravar classificacoes.",
        inputSchema={"type":"object","properties":{"startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},"classificationTypeList":{"type":"array","items":{"type":"integer"}},"isGroup":{"type":"boolean"},"order":{"type":"string","description":"code,maxChangeFilterDate"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"}}}}),
    types.Tool(name="totvs_get_product_composition_group_product", description="Composicao por grupo/produto/referencia. Requer productCodeList, groupCodeList ou referenceCodeList.",
        inputSchema={"type":"object","properties":{"productCodeList":{"type":"array","items":{"type":"integer"}},"groupCodeList":{"type":"array","items":{"type":"integer"}},"referenceCodeList":{"type":"array","items":{"type":"string"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"}}}}),
    types.Tool(name="totvs_get_product_composition_product", description="Composicao especifica de produto por produto/grupo/referencia. Requer productCodeList, groupCodeList ou referenceCodeList.",
        inputSchema={"type":"object","properties":{"productCodeList":{"type":"array","items":{"type":"integer"}},"groupCodeList":{"type":"array","items":{"type":"integer"}},"referenceCodeList":{"type":"array","items":{"type":"string"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"}}}}),
    types.Tool(name="totvs_get_product_instruction_items", description="Itens de instrucao de conservacao/manuseio de produto. Suporta expand='image,globalImage'.",
        inputSchema={"type":"object","properties":{"startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},"codeList":{"type":"array","items":{"type":"integer"}},"grouperCodeList":{"type":"array","items":{"type":"integer"}},"description":{"type":"string"},"expand":{"type":"string","description":"image,globalImage"},"order":{"type":"string","description":"code,maxChangeFilterDate"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"}}}}),
    types.Tool(name="totvs_get_product_price_table_scales", description="Escalas de tabela de preco por codigo de escala/tabela.",
        inputSchema={"type":"object","properties":{"startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},"scaleCodeList":{"type":"array","items":{"type":"integer"}},"priceTableCodeList":{"type":"array","items":{"type":"integer"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":1000},"fields":{"type":"array","items":{"type":"string"}}}}),
    types.Tool(name="totvs_get_product_grouper_configurations", description="Configuracoes de agrupador de produto.",
        inputSchema={"type":"object","properties":{"startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},"grouperCodeList":{"type":"array","items":{"type":"integer"}},"order":{"type":"string","description":"grouperCode,maxChangeFilterDate"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"}}}}),
    types.Tool(name="totvs_search_consumption_sheet", description="Ficha de consumo de produto (matéria-prima + serviços). Retorna items[] com: productCode, productName, referenceCode, colorCode, size, rawMaterials[]={rawMaterialCode, rawMaterialDescription, consumptionQuantity, applicationCode, applicationDescription}, services[]={serviceCode, serviceDescription, serviceApplication, serviceAmount}. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{
            "productCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de códigos de produto"},
            "referenceCode":{"type":"string","description":"Código de referência do produto"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":1000},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens."}
        }}),
    types.Tool(name="totvs_search_engineering_services", description="Servicos de engenharia de produto. Requer ao menos um filtro; para consulta ampla use status=true. Use expand='dataProviders,dataLevelGroup' quando precisar de fornecedores/niveis.",
        inputSchema={"type":"object","properties":{
            "filter":{"type":"object","description":"ServiceFilterModel completo"},
            "change":{"type":"object","description":"{startDate,endDate}"},
            "startServiceCode":{"type":"integer"},
            "endServiceCode":{"type":"integer"},
            "serviceCodeList":{"type":"array","items":{"type":"integer"}},
            "serviceName":{"type":"string"},
            "codeTypeService":{"type":"integer"},
            "providerInfo":{"type":"object"},
            "status":{"type":"boolean"},
            "expand":{"type":"string","description":"dataProviders,dataLevelGroup"},
            "order":{"type":"string"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
            "fields":{"type":"array","items":{"type":"string"}}
        }}),
    types.Tool(name="totvs_get_engineering_operations", description="Operacoes de engenharia de produto.",
        inputSchema={"type":"object","properties":{
            "startChangeDate":{"type":"string"},
            "endChangeDate":{"type":"string"},
            "operationCodeList":{"type":"array","items":{"type":"integer"}},
            "operationTypeList":{"type":"array","items":{"type":"integer"}},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
            "order":{"type":"string"},
            "fields":{"type":"array","items":{"type":"string"}}
        }}),
    types.Tool(name="totvs_search_engineering_applications", description="Aplicacoes de engenharia de produto.",
        inputSchema={"type":"object","properties":{
            "startChangeDate":{"type":"string"},
            "endChangeDate":{"type":"string"},
            "applicationCodeList":{"type":"array","items":{"type":"integer"}},
            "applicationTypeList":{"type":"array","items":{"type":"integer"}},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
            "order":{"type":"string"},
            "fields":{"type":"array","items":{"type":"string"}}
        }}),
    types.Tool(name="totvs_search_engineering_default", description="Estrutura base de engenharia por produto/grupo/referencia.",
        inputSchema={"type":"object","properties":{
            "startChangeDate":{"type":"string"},
            "endChangeDate":{"type":"string"},
            "rawMaterialColorBranchCodes":{"type":"array","items":{"type":"integer"}},
            "productCodeList":{"type":"array","items":{"type":"integer"}},
            "groupCodeList":{"type":"array","items":{"type":"string"}},
            "referenceCodeList":{"type":"array","items":{"type":"string"}},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
            "fields":{"type":"array","items":{"type":"string"}}
        }}),
    types.Tool(name="totvs_get_engineering_configurations", description="Configuracoes de engenharia por classificacao de produto.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "purposeType":{"type":"integer"},
            "classificationCodeList":{"type":"array","items":{"type":"string"}},
            "classificationType":{"type":"integer"},
            "fields":{"type":"array","items":{"type":"string"}}
        }}),
    types.Tool(name="totvs_create_engineering_references", description="⚠️ ESCRITA — Cadastra produto a partir da engenharia padrão.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "references":{"type":"array","items":{"type":"object"}},
            "items":{"type":"array","items":{"type":"object"}}
        }}),
    types.Tool(name="totvs_search_material_requests", description="Consulta requisicoes/solicitacoes de material. Use expand='items,classifications,observations'. Status: 0=Pendente, 1=Liberada, 2=Nao liberada, 3=Aprovada, 4=Atendida, 5=Nao atendida, 6=Cancelada.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Filial unica; alternativa a branchCodeList"},
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Obrigatorio no Swagger; default vem do contexto quando omitido"},
            "change":{"type":"object","description":"{startDate,endDate}"},
            "startRequestDate":{"type":"string"},
            "endRequestDate":{"type":"string"},
            "requestCodeList":{"type":"array","items":{"type":"integer"}},
            "personList":{"type":"array","items":{"type":"integer"},"description":"Pessoa responsavel"},
            "costCenterList":{"type":"array","items":{"type":"integer"}},
            "productList":{"type":"array","items":{"type":"integer"},"description":"Produtos/materiais nos itens"},
            "buyerList":{"type":"array","items":{"type":"integer"}},
            "purposeCodeList":{"type":"array","items":{"type":"integer"}},
            "statusTypeList":{"type":"array","items":{"type":"integer"},"description":"0=Pendente,1=Liberada,2=Nao liberada,3=Aprovada,4=Atendida,5=Nao atendida,6=Cancelada"},
            "operationCodeList":{"type":"array","items":{"type":"integer"}},
            "classifications":{"type":"array","items":{"type":"object","properties":{"classificationTypeCode":{"type":"integer"},"classificationCode":{"type":"string"}}}},
            "expand":{"type":"string","description":"items,classifications,observations"},
            "order":{"type":"string","description":"branchCode,requestDate,requestCode,maxChangeFilterDate. Use - para desc."},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100,"description":"Maximo 500 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"}}
        }}),
    types.Tool(name="totvs_create_material_request", description="⚠️ ESCRITA — Cria uma solicitacao de material no TOTVS. Use somente quando o usuario confirmar filial, finalidade, solicitante e itens.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Empresa. Campo Empresa do CMCFM006."},
            "requestDate":{"type":"string","description":"Data de emissao da solicitacao, formato YYYY-MM-DD."},
            "purposeCode":{"type":"integer","description":"Finalidade da solicitacao."},
            "requester":{"type":"integer","description":"Solicitante."},
            "costCenter":{"type":"integer","description":"Centro de custo da capa."},
            "bridgeCode":{"type":"string","description":"Codigo de integracao externo."},
            "items":{"type":"array","items":{"type":"object","properties":{
                "sequence":{"type":"integer"},
                "productCode":{"type":"integer"},
                "requestQuantity":{"type":"number"},
                "costCenter":{"type":"integer"},
                "expense":{"type":"integer"},
                "cost":{"type":"number"}
            },"required":["sequence"]}},
            "observations":{"type":"array","items":{"type":"object","properties":{"observation":{"type":"string"}}}}
        },"required":["branchCode","purposeCode","requester"]}),
    types.Tool(name="totvs_add_material_request_items", description="⚠️ ESCRITA — Inclui itens em uma solicitacao de material existente.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"requestDate":{"type":"string"},"requestCode":{"type":"integer"},"integrationCode":{"type":"string"},
            "items":{"type":"array","items":{"type":"object","properties":{"sequence":{"type":"integer"},"productCode":{"type":"integer"},"requestQuantity":{"type":"number"},"costCenter":{"type":"integer"},"expense":{"type":"integer"},"cost":{"type":"number"}},"required":["sequence"]}}
        }}),
    types.Tool(name="totvs_modify_material_request_header", description="⚠️ ESCRITA — Altera a capa de uma solicitacao de material.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer"},"requestDate":{"type":"string"},"requestCode":{"type":"integer"},"integrationCode":{"type":"string"},"purposeCode":{"type":"integer"},"costCenter":{"type":"integer"}}}),
    types.Tool(name="totvs_modify_material_request_items", description="⚠️ ESCRITA — Altera itens de uma solicitacao de material existente.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"requestDate":{"type":"string"},"requestCode":{"type":"integer"},"integrationCode":{"type":"string"},
            "items":{"type":"array","items":{"type":"object","properties":{"sequence":{"type":"integer"},"productCode":{"type":"integer"},"requestQuantity":{"type":"number"},"costCenter":{"type":"integer"},"expense":{"type":"integer"},"cost":{"type":"number"}},"required":["sequence"]}}
        }}),
    types.Tool(name="totvs_remove_material_request_items", description="⚠️ ESCRITA/DESTRUTIVA — Remove itens de uma solicitacao de material existente.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"requestDate":{"type":"string"},"requestCode":{"type":"integer"},"integrationCode":{"type":"string"},
            "items":{"type":"array","items":{"type":"object","properties":{"sequence":{"type":"integer"}},"required":["sequence"]}}
        }}),
    types.Tool(name="totvs_cancel_material_request_items", description="⚠️ ESCRITA/DESTRUTIVA — Cancela quantidade de itens de uma solicitacao de material.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"requestDate":{"type":"string"},"requestCode":{"type":"integer"},"integrationCode":{"type":"string"},
            "items":{"type":"array","items":{"type":"object","properties":{"sequence":{"type":"integer"},"cancelQuantity":{"type":"number"},"reason":{"type":"integer"},"descriptions":{"type":"array","items":{"type":"object","properties":{"description":{"type":"string"}}}}},"required":["sequence"]}}
        }}),
    types.Tool(name="totvs_approve_material_request", description="⚠️ ESCRITA — Aprova ou reprova solicitacao de material.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer"},"requestDate":{"type":"string"},"requestCode":{"type":"integer"},"approverUser":{"type":"integer"},"approved":{"type":"boolean"},"reportDescription":{"type":"string"},"reasonCode":{"type":"integer"}}}),
    types.Tool(name="totvs_move_material_request_items", description="⚠️ ESCRITA/DESTRUTIVA — Movimenta/baixa itens de solicitacao de material. Pode afetar estoque.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"requestDate":{"type":"string"},"requestCode":{"type":"integer"},"integrationCode":{"type":"string"},"operationCode":{"type":"integer"},
            "items":{"type":"array","items":{"type":"object","properties":{"sequence":{"type":"integer"},"movementQuantity":{"type":"number"},"batchItems":{"type":"array","items":{"type":"object"}}},"required":["sequence","movementQuantity"]}},
            "descriptions":{"type":"array","items":{"type":"object","properties":{"description":{"type":"string"}}}}
        },"required":["operationCode","items"]}),
    types.Tool(name="totvs_search_product_prototypes", description="Consulta prototipos de produto por lista de codigos. A API exige prototypeCodeList. Use expand='Destiny' para dados de destino.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "prototypeCodeList":{"type":"array","items":{"type":"integer"},"description":"Obrigatorio na API TOTVS; maximo 100 itens."},
            "expand":{"type":"string","description":"Destiny"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100,"description":"Maximo 100 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"}}
        },"required":["prototypeCodeList"]}),
    types.Tool(name="totvs_create_product_prototype", description="⚠️ ESCRITA — Cria prototipo de produto. Aceita blocos ricos do Swagger como gridQuantities, services, rawMaterials, classifications, images e compositions.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "code":{"type":"integer","description":"Se omitido, a TOTVS pode gerar sequencia automatica."},
            "prototypeDescription":{"type":"string"},
            "customerCode":{"type":"integer"},
            "customerCpfCnpj":{"type":"string"},
            "estimatedStart":{"type":"string"},
            "estimatedDeliveryDate":{"type":"string"},
            "baseGroupCode":{"type":"integer"},
            "gridCode":{"type":["integer","string"]},
            "prototypeVersion":{"type":"integer"},
            "netWeight":{"type":"number"},
            "grossWeight":{"type":"number"},
            "instructions":{"type":"array","items":{"type":"object"}},
            "gridQuantities":{"type":"array","items":{"type":"object"}},
            "services":{"type":"array","items":{"type":"object"}},
            "measureTables":{"type":"array","items":{"type":"object"}},
            "operationalSequences":{"type":"array","items":{"type":"object"}},
            "images":{"type":"array","items":{"type":"object"}},
            "rawMaterials":{"type":"array","items":{"type":"object"}},
            "rawMaterialsGrid":{"type":"array","items":{"type":"object"}},
            "classifications":{"type":"array","items":{"type":"object"}},
            "additionalProductFields":{"type":"array","items":{"type":"object"}},
            "compositions":{"type":"array","items":{"type":"object"}}
        },"required":["branchCode"]}),
    types.Tool(name="totvs_update_product_prototype", description="⚠️ ESCRITA — Altera dados de prototipo de produto. Aceita o mesmo contrato rico da criacao.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "code":{"type":"integer"},
            "prototypeDescription":{"type":"string"},
            "customerCode":{"type":"integer"},
            "customerCpfCnpj":{"type":"string"},
            "estimatedStart":{"type":"string"},
            "estimatedDeliveryDate":{"type":"string"},
            "baseGroupCode":{"type":"integer"},
            "gridCode":{"type":["integer","string"]},
            "prototypeVersion":{"type":"integer"},
            "netWeight":{"type":"number"},
            "grossWeight":{"type":"number"},
            "instructions":{"type":"array","items":{"type":"object"}},
            "gridQuantities":{"type":"array","items":{"type":"object"}},
            "services":{"type":"array","items":{"type":"object"}},
            "measureTables":{"type":"array","items":{"type":"object"}},
            "operationalSequences":{"type":"array","items":{"type":"object"}},
            "images":{"type":"array","items":{"type":"object"}},
            "rawMaterials":{"type":"array","items":{"type":"object"}},
            "rawMaterialsGrid":{"type":"array","items":{"type":"object"}},
            "classifications":{"type":"array","items":{"type":"object"}},
            "additionalProductFields":{"type":"array","items":{"type":"object"}},
            "compositions":{"type":"array","items":{"type":"object"}}
        },"required":["branchCode"]}),
    types.Tool(name="totvs_search_product_storage", description="Consulta armazenagem fisica/localizacao logistica de produtos.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Filial unica; alternativa a branchCodeList"},
            "branchCodeList":{"type":"array","items":{"type":"integer"}},
            "productCodeList":{"type":"array","items":{"type":"integer"}},
            "referenceCodeList":{"type":"array","items":{"type":"string"}},
            "barCodeList":{"type":"array","items":{"type":"string"}},
            "addressCodeList":{"type":"array","items":{"type":"string"}},
            "order":{"type":"string"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100}
        }}),
    types.Tool(name="totvs_upsert_product_packaging", description="⚠️ ESCRITA — Manutencao de produto em embalagem logistica.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "packagingNumber":{"type":"integer"},
            "productCode":{"type":"integer"},
            "quantity":{"type":"number"}
        },"required":["branchCode","packagingNumber","productCode","quantity"]}),
    types.Tool(name="totvs_add_product_packaging_quantity", description="⚠️ ESCRITA — Adiciona quantidade de produto a uma embalagem logistica.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "packagingNumber":{"type":"integer"},
            "productCode":{"type":"integer"},
            "quantity":{"type":"number"}
        },"required":["branchCode","packagingNumber","productCode","quantity"]}),
    types.Tool(name="totvs_subtract_product_packaging_quantity", description="⚠️ ESCRITA — Subtrai quantidade de produto de uma embalagem logistica.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "packagingNumber":{"type":"integer"},
            "productCode":{"type":"integer"},
            "quantity":{"type":"number"}
        },"required":["branchCode","packagingNumber","productCode","quantity"]}),
    types.Tool(name="totvs_create_product_classification", description="⚠️ ESCRITA — Upsert de classificação de produto. Tenta incluir; se já existir, altera. Em lote misto separa itens novos e existentes quando a API informa ProductCode no erro.",
        inputSchema={"type":"object","properties":{
            "productCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de códigos de produto"},
            "typeCode":{"type":"integer","description":"Código do tipo de classificação (ex: 11 = web - tipo produto)"},
            "classificationCode":{"type":"string","description":"Código da classificação (ex: '7' = shopify)"},
            "referenceId":{"type":"integer","description":"ID da referência (padrão 0)","default":0},
        },"required":["productCodeList","typeCode","classificationCode"]}),
    types.Tool(name="totvs_create_product_value", description="⚠️ ESCRITA — Inclui preço ou custo de produto (quando ainda não existe). Use totvs_get_context para obter os códigos válidos.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "productCode":{"type":"integer","description":"Código do produto"},
            "valueCode":{"type":"integer","description":"Código do tipo de preço ou custo"},
            "valueType":{"type":"integer","description":"Tipo do valor conforme enum da API"},
            "value":{"type":"number","description":"Valor"},
        },"required":["branchCode","productCode","valueCode","value"]}),
    types.Tool(
        name="totvs_update_product_price",
        description=(
            "⚠️ ESCRITA — Altera preço OU custo de produto. "
            "DEPRECATED em v3.1: prefira totvs_update_product_price_only ou "
            "totvs_update_product_cost. Esta tool ainda funciona — sem valueType "
            "assume Price; passe valueType='Cost' (ou 'C') pra custo."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "productCode": {"type": "integer"},
                "branchCode": {"type": "integer", "description": "Padrão do .env se omitido"},
                "valueType": {
                    "type": "string",
                    "enum": ["Price", "Cost", "P", "C"],
                    "description": "Price/P = preço de venda; Cost/C = custo. Default: Price."
                },
                "valueCode": {"type": "integer", "description": "Código da tabela (1, 2, 3...)"},
                "value": {"type": "number"}
            },
            "required": ["productCode", "valueCode", "value"]
        },
        annotations=WRITE_TOOL_ANNOTATIONS,
    ),
    types.Tool(
        name="totvs_update_product_price_only",
        description=(
            "⚠️ ESCRITA — Atualiza PREÇO DE VENDA do produto. "
            "valueType='Price' é injetado automaticamente. "
            "Faz upsert: tenta UPDATE; se não existe, faz CREATE. "
            "Modo simples: passe productCode + valueCode + value. "
            "Modo lote: products[]={productCode, values:[{branchCode, valueCode, value}]}. "
            "Para custo use totvs_update_product_cost."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "productCode": {"type": "integer"},
                "branchCode": {"type": "integer", "description": "Padrão do .env se omitido"},
                "valueCode": {"type": "integer", "description": "Tabela de preço (consulte priceTypes em totvs_get_context)"},
                "value": {"type": "number"},
                "products": {
                    "type": "array",
                    "description": "Modo lote (alternativo)",
                    "items": {"type": "object"}
                }
            }
        }
    ),
    types.Tool(
        name="totvs_update_product_cost",
        description=(
            "⚠️ ESCRITA — Atualiza CUSTO do produto. "
            "valueType='Cost' é injetado automaticamente. "
            "Faz upsert: tenta UPDATE; se não existe, faz CREATE. "
            "Para preço use totvs_update_product_price_only."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "productCode": {"type": "integer"},
                "branchCode": {"type": "integer", "description": "Padrão do .env se omitido"},
                "valueCode": {"type": "integer"},
                "value": {"type": "number"},
                "products": {"type": "array", "items": {"type": "object"}}
            }
        }
    ),
    types.Tool(name="totvs_update_promotion_price", description="⚠️ ESCRITA — Altera preço de promoção de produto.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCode":{"type":"integer"},"promotionPrice":{"type":"number"},"startDate":{"type":"string"},"endDate":{"type":"string"}},"required":["branchCode","productCode","promotionPrice"]},
        annotations=WRITE_TOOL_ANNOTATIONS),
    types.Tool(name="totvs_search_product_codes", description="Lista de produtos com filtro — retorna apenas código e dados básicos. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{
            "productCodeList":{"type":"array","items":{"type":"integer"}},
            "referenceCodeList":{"type":"array","items":{"type":"string"}},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."},
        }}),
    types.Tool(name="totvs_search_product_costs", description="Custos de produtos por filtro. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"productCodeList":{"type":"array","items":{"type":"integer"}},
            "referenceCodeList":{"type":"array","items":{"type":"string"}},
            "costCodeList":{"type":"array","items":{"type":"integer"}},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."},
        }}),
    types.Tool(name="totvs_get_product_category", description="Categorias de produtos disponíveis.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer"}}}),
    types.Tool(name="totvs_get_product_classifications", description="Classificações de produtos e seus tipos.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer"}}}),
    types.Tool(name="totvs_get_measurement_units", description="Unidades de medida disponíveis.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_search_omni_changed_balances", description="Saldos de estoque alterados para sincronização omni-channel.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}
        }}),
    types.Tool(
        name="totvs_update_product_data",
        description=(
            "⚠️ ESCRITA — Atualiza dados gerais de produto (peso, NCM, CST, etc). "
            "Auto-roteamento: "
            "se passar productCode (1 produto) → PUT /products/{code}/{branchCode} (simples); "
            "se passar productCodeList ou groupCode → PUT /data (batch com filtros). "
            "Campos: weight, ncmCode, cstCode, cestCode, prefixEanGtin, measuredUnit, "
            "isInactive, isFinishedProduct, isRawMaterial, isBulkMaterial, isOwnProduction."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "productCode": {"type": "integer", "description": "Modo simples (1 produto)"},
                "productCodeList": {"type": "array", "items": {"type": "integer"}, "description": "Modo batch"},
                "branchCode": {"type": "integer"},
                "barCodeList": {"type": "array", "items": {"type": "string"}},
                "groupCode": {"type": "string"},
                "referenceCode": {"type": "string"},
                "weight": {"type": "number", "description": "Peso em kg"},
                "ncmCode": {"type": "string"},
                "measuredUnit": {"type": "string"},
                "cstCode": {"type": "string"},
                "cestCode": {"type": "string"},
                "prefixEanGtin": {"type": "string"},
                "isInactive": {"type": "boolean"},
                "isFinishedProduct": {"type": "boolean"},
                "isRawMaterial": {"type": "boolean"},
                "isBulkMaterial": {"type": "boolean"},
                "isOwnProduction": {"type": "boolean"}
            }
        }
    ),
    types.Tool(
        name="totvs_update_product_simple",
        description=(
            "⚠️ ESCRITA — Atualiza dados de UM produto específico. "
            "Endpoint validado em produção (MOOUI alterar_peso.py). "
            "Use pra: peso, NCM, CST, flags. Para múltiplos produtos use totvs_update_product_data."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "productCode": {"type": "integer"},
                "branchCode": {"type": "integer"},
                "weight": {"type": "number"},
                "ncmCode": {"type": "string"},
                "cstCode": {"type": "string"},
                "cestCode": {"type": "string"},
                "prefixEanGtin": {"type": "string"},
                "isInactive": {"type": "boolean"},
                "isFinishedProduct": {"type": "boolean"},
                "isRawMaterial": {"type": "boolean"},
                "isBulkMaterial": {"type": "boolean"},
                "isOwnProduction": {"type": "boolean"}
            },
            "required": ["productCode"]
        }
    ),
    types.Tool(
        name="totvs_update_product_branch_info_batch",
        description=(
            "⚠️ ESCRITA — Atualiza dados em LOTE de produtos numa filial. "
            "Endpoint PUT /branch-info/{branchCode}. "
            "Útil pra ativar/desativar muitos produtos."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {"type": "integer"},
                "productCodeList": {"type": "array", "items": {"type": "integer"}},
                "barCodeList": {"type": "array", "items": {"type": "string"}},
                "groupCode": {"type": "string"},
                "referenceCode": {"type": "string"},
                "isInactive": {"type": "boolean"},
                "isFinishedProduct": {"type": "boolean"},
                "isRawMaterial": {"type": "boolean"},
                "isBulkMaterial": {"type": "boolean"},
                "isOwnProduction": {"type": "boolean"}
            }
        }
    ),
    types.Tool(name="totvs_create_product_barcode", description="⚠️ Inclui código de barras para produto.",
        inputSchema={"type":"object","properties":{
            "productCode":{"type":"integer"},"barcode":{"type":"string"},"barcodeType":{"type":"string"}
        },"required":["productCode","barcode"]}),

    # ── PRODUCT v2.3 (new write endpoints) ────────────────────────────────────
    types.Tool(name="totvs_update_barcode", description="⚠️ ESCRITA — Altera código de barras existente.",
        inputSchema={"type":"object","properties":{
            "productCode":{"type":"integer"},
            "oldBarcode":{"type":"string"},
            "newBarcode":{"type":"string"}
        }}),
    types.Tool(name="totvs_create_reference", description="⚠️ ESCRITA — Cria nova referência de produto.",
        inputSchema={"type":"object","properties":{
            "referenceCode":{"type":"string"},
            "description":{"type":"string"},
            "categoryCode":{"type":"integer"},
            "colorCode":{"type":"integer"},
            "grid":{"type":"object"}
        }}),
    types.Tool(name="totvs_create_classification_type", description="⚠️ ESCRITA — Cria um novo tipo de classificação (agrupador). Diferente de GET /classifications (consulta).",
        inputSchema={"type":"object","properties":{
            "typeCode":{"type":"integer"},
            "description":{"type":"string"},
            "isInactive":{"type":"boolean"}
        }}),
    types.Tool(name="totvs_create_product_batch", description="⚠️ Inclui lote e item de lote de produto.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"productCode":{"type":"integer"},
            "batchCode":{"type":"string"},"quantity":{"type":"number"}
        },"required":["branchCode","productCode","batchCode"]}),

    # ── PERSON ───────────────────────────────────────────────────────────────
    types.Tool(name="totvs_update_product_batch_info", description="⚠️ ESCRITA — Altera dados de item de lote.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "batchCode":{"type":"integer"},
            "sequence":{"type":"integer"},
            "batchItemBarCode":{"type":"string"}
        }}),
    types.Tool(name="totvs_create_product_batch_preferential_sales_order", description="⚠️ ESCRITA — Cadastra relacionamento de item de lote com pedido de venda preferencial.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "batchCode":{"type":"integer"},
            "sequence":{"type":"integer"},
            "batchItemBarCode":{"type":"string"},
            "orderCode":{"type":"integer"}
        }}),
    types.Tool(name="totvs_upsert_product_color", description="⚠️ ESCRITA — Inclui ou altera dados de cor.",
        inputSchema={"type":"object","properties":{
            "code":{"type":"string"},
            "description":{"type":"string"},
            "isInactive":{"type":"boolean"}
        }}),
    types.Tool(name="totvs_create_product_grid", description="⚠️ ESCRITA — Inclui dados de grade.",
        inputSchema={"type":"object","properties":{
            "gridCode":{"type":"integer"},
            "description":{"type":"string"},
            "sizes":{"type":"array","items":{"type":"object"}}
        }}),

    types.Tool(name="totvs_search_individual_customers", description="Busca pessoas físicas/clientes PF por CPF, código, telefone, aniversário, classificações e flags funcionais. Use expand apenas quando precisar dados ricos.",
        inputSchema={"type":"object","properties":{
            "filter":{"type":"object","description":"IndividualFilterModel oficial; se informado, substitui os filtros soltos."},
            "change":{"type":"object","description":"PersonChangeFilterModel: startDate,endDate,inClassification,inAddress,inPhone,inObservation,inPerson,inCustomer,inSupplier,inRepresentative,inPurchasingGuide,inShippingCompany,inReference,inContact,inStatistic,inCustomerObservation,inEmployee,inPreference,classificationTypeCodeList"},
            "startPersonCode":{"type":"integer"},
            "endPersonCode":{"type":"integer"},
            "personCodeList":{"type":"array","items":{"type":"integer"}},
            "customerCodeList":{"type":"array","items":{"type":"integer"},"description":"Alias legado para personCodeList em alguns fluxos."},
            "cpfList":{"type":"array","items":{"type":"string"}},
            "name":{"type":"string"},
            "phoneNumber":{"type":"string"},
            "birthdayDayList":{"type":"array","items":{"type":"string"}},
            "birthdayMonth":{"type":"string"},
            "personIsInactive":{"type":"boolean"},
            "isCustomer":{"type":"boolean"},
            "isSupplier":{"type":"boolean"},
            "isRepresentative":{"type":"boolean"},
            "isPurchasingGuide":{"type":"boolean"},
            "isShippingCompany":{"type":"boolean"},
            "isEmployee":{"type":"boolean"},
            "classifications":{"type":"array","items":{"type":"object","properties":{"type":{"type":"integer"},"codeList":{"type":"array","items":{"type":"string"}}}}},
            "option":{"type":"object","description":"PersonOptionModel: classificationTypeCodeList, additionalFieldCodeList, branchStaticDataList, branchRepresentativeParameterList, QuantityOcurrenceCustomerObservation"},
            "expand":{"type":"string","description":"phones,addresses,emails,classifications,additionalFields,references,observations,relateds,shippingCompany,statistics,representatives,customerObservations,familiars"},
            "order":{"type":"string","description":"personCode,maxChangeFilterDate. Use - para desc."},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":500,"description":"Máximo 500 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}
        }}),
    types.Tool(name="totvs_search_legal_customers", description="Busca pessoas jurídicas/clientes PJ por CNPJ, código, classificações e flags funcionais. Use expand apenas quando precisar dados ricos.",
        inputSchema={"type":"object","properties":{
            "filter":{"type":"object","description":"LegalEntityFilterModel oficial; se informado, substitui os filtros soltos."},
            "change":{"type":"object","description":"PersonChangeFilterModel: startDate,endDate,inClassification,inAddress,inPhone,inObservation,inPerson,inCustomer,inSupplier,inRepresentative,inPurchasingGuide,inShippingCompany,inReference,inContact,inStatistic,inCustomerObservation,inEmployee,inPreference,classificationTypeCodeList"},
            "startPersonCode":{"type":"integer"},
            "endPersonCode":{"type":"integer"},
            "personCodeList":{"type":"array","items":{"type":"integer"}},
            "customerCodeList":{"type":"array","items":{"type":"integer"},"description":"Alias legado para personCodeList em alguns fluxos."},
            "cnpjList":{"type":"array","items":{"type":"string"}},
            "corporateName":{"type":"string"},
            "isCustomer":{"type":"boolean"},
            "isSupplier":{"type":"boolean"},
            "isRepresentative":{"type":"boolean"},
            "isPurchasingGuide":{"type":"boolean"},
            "isShippingCompany":{"type":"boolean"},
            "isEmployee":{"type":"boolean"},
            "classifications":{"type":"array","items":{"type":"object","properties":{"type":{"type":"integer"},"codeList":{"type":"array","items":{"type":"string"}}}}},
            "option":{"type":"object","description":"PersonOptionModel: classificationTypeCodeList, additionalFieldCodeList, branchStaticDataList, branchRepresentativeParameterList, QuantityOcurrenceCustomerObservation"},
            "expand":{"type":"string","description":"phones,addresses,emails,classifications,additionalFields,references,observations,relateds,partners,shippingCompany,contacts,statistics,paymentMethods,preferences,socialNetworks,representatives,customerObservations"},
            "order":{"type":"string","description":"personCode,maxChangeFilterDate. Use - para desc."},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":500,"description":"Máximo 500 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}
        }}),
    types.Tool(name="totvs_get_customer_bonus_balance", description="Saldo de bônus/desconto de um cliente.",
        inputSchema={"type":"object","properties":{"customerCode":{"type":"integer"},"cpfCnpj":{"type":"string"}}}),
    types.Tool(name="totvs_get_person_statistics", description="Estatísticas de UM cliente específico: total comprado, ticket médio, frequência. NÃO use para 'vendas de hoje', 'o que vendi', ranking, resumo geral ou clientes novos; nesses casos use totvs_sales_today_summary, totvs_daily_dashboard ou totvs_new_customers_today.",
        inputSchema={"type":"object","properties":{"customerCode":{"type":"integer"},"branchCode":{"type":"integer","description":"Código da filial"}},"required":["customerCode"]}),
    types.Tool(name="totvs_create_or_update_individual_customer", description="⚠️ ESCRITA — Cria ou atualiza cliente PF no TOTVS.",
        inputSchema={"type":"object","properties":{"cpf":{"type":"string"},"name":{"type":"string"},"email":{"type":"string"},"phone":{"type":"string"},"birthDate":{"type":"string"},"branchCode":{"type":"integer","description":"Código da filial"}},"required":["cpf","name"]},
        annotations=WRITE_TOOL_ANNOTATIONS),
    types.Tool(name="totvs_create_or_update_legal_customer", description="⚠️ Cria ou atualiza cliente PJ no TOTVS.",
        inputSchema={"type":"object","properties":{
            "cnpj":{"type":"string"},"corporateName":{"type":"string"},
            "fantasyName":{"type":"string"},"email":{"type":"string"},
            "branchCode":{"type":"integer"}
        },"required":["cnpj","corporateName"]}),
    types.Tool(name="totvs_get_branches_list", description="Lista todas as filiais/empresas cadastradas.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_search_representatives", description="Busca representantes comerciais. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{
            "representativeCodeList":{"type":"array","items":{"type":"integer"}},
            "cpfCnpjList":{"type":"array","items":{"type":"string"}},
            "name":{"type":"string"},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."},
        }}),
    types.Tool(name="totvs_get_person_classifications", description="Classificações de pessoa disponíveis.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_remove_person_classification_relationship", description="⚠️ DESTRUTIVO — Remove relacionamento de classificação com pessoa. Use somente após confirmação explícita.",
        inputSchema={"type":"object","properties":{
            "personCode":{"type":"integer"},
            "classifications":{"type":"array","items":{"type":"object"}}
        },"required":["personCode"]}),
    types.Tool(name="totvs_get_email_types", description="Tipos de e-mail disponíveis para cadastro de pessoa.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_get_phone_types", description="Tipos de telefone disponíveis para cadastro de pessoa.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_get_contact_types", description="Tipos de contato disponiveis para cadastro de pessoa.",
        inputSchema={"type":"object","properties":{
            "startChangeDate":{"type":"string"},
            "endChangeDate":{"type":"string"},
            "typeCodeList":{"type":"array","items":{"type":"integer"}},
            "order":{"type":"string","description":"code,maxChangeFilterDate. Use - para desc."},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":1000}
        }}),
    types.Tool(name="totvs_search_reception_sale", description="Consulta recepcao de venda por data de movimento/cadastro e tipo L=Loja, P=Pedido.",
        inputSchema={"type":"object","properties":{
            "startMovementDate":{"type":"string"},
            "endMovementDate":{"type":"string"},
            "startRegistrationDate":{"type":"string"},
            "endRegistrationDate":{"type":"string"},
            "receptionTypeList":{"type":"array","items":{"type":"string","enum":["L","P"]}},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":1000},
            "fields":{"type":"array","items":{"type":"string"}}
        }}),
    types.Tool(name="totvs_consume_bonus", description="⚠️ Consome bônus/desconto de cliente.",
        inputSchema={"type":"object","properties":{
            "customerCode":{"type":"integer"},"branchCode":{"type":"integer"},
            "value":{"type":"number"}
        },"required":["customerCode","branchCode","value"]}),
    types.Tool(name="totvs_create_person_message", description="⚠️ Inclui mensagem/observação para uma pessoa.",
        inputSchema={"type":"object","properties":{
            "personCode":{"type":"integer"},"message":{"type":"string"}
        },"required":["personCode","message"]}),
    types.Tool(name="totvs_relate_customer_representatives", description="⚠️ ESCRITA — Relaciona clientes a representante.",
        inputSchema={"type":"object","properties":{
            "representativeCode":{"type":"integer"},
            "representativeCpfCnpj":{"type":"string"},
            "customerCodeList":{"type":"array","items":{"type":"integer"}},
            "customerCpfCnpjList":{"type":"array","items":{"type":"string"}}
        }}),
    types.Tool(name="totvs_change_person_message", description="⚠️ ESCRITA — Altera descricao/status/prioridade de mensagem da pessoa. Status: Unread, Read, Canceled.",
        inputSchema={"type":"object","properties":{
            "filter":{"type":"object","properties":{
                "personCode":{"type":"integer"},
                "personCpfCnpj":{"type":"string"},
                "sequence":{"type":"integer"}
            },"required":["sequence"]},
            "description":{"type":"string"},
            "status":{"type":"string","enum":["Unread","Read","Canceled"]},
            "priority":{"type":"integer"}
        },"required":["filter"]}),

    # ── ACCOUNTS RECEIVABLE ───────────────────────────────────────────────────
    types.Tool(name="totvs_search_customer_financial_balance", description="Limite financeiro e saldo do cliente por filial. Retorna limite, faturas em aberto, crédito de devolução, adiantamento e outros.",
        inputSchema={"type":"object","properties":{
            "customerCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos dos clientes"},
            "customerCpfCnpjList":{"type":"array","items":{"type":"string"},"description":"CPF/CNPJ dos clientes"},
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Filiais para retorno dos saldos"},
            "isLimit":{"type":"boolean","description":"Retornar limite de crédito"},
            "isOpenInvoice":{"type":"boolean","description":"Retornar faturas em aberto"},
            "isRefundCredit":{"type":"boolean","description":"Retornar crédito de devolução"},
            "isAdvanceAmount":{"type":"boolean","description":"Retornar adiantamento"},
            "isDofni":{"type":"boolean","description":"Retornar DOFNI"},
            "isConsigned":{"type":"boolean","description":"Retornar consignado"},
            "isInvoiceBehindSchedule":{"type":"boolean","description":"Retornar faturas em atraso"},
            "isSalesOrderAdvance":{"type":"boolean","description":"Retornar adiantamento de pedido de venda"},
            "change":{"type":"object","description":"Filtro oficial por alteração: {startDate,endDate,branchCodeList,inLimit/inOpenInvoice/inRefundCredit/inAdvanceAmount/inDofni/inDofniCheck/inTransactionOut/inConsigned/inSalesOrderAdvance}. Se usar datas, informe branchCodeList e ao menos um in..."},
            "startChangeDate":{"type":"string","description":"Data de alteração inicial (ISO 8601)"},
            "endChangeDate":{"type":"string","description":"Data de alteração final"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":500,"description":"Máximo 500 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens."},
        }}),
    types.Tool(name="totvs_search_receivable_documents", description="Busca documentos a receber (faturas, duplicatas). Retorna items[] com: branchCode, customerCode, customerCpfCnpj, receivableCode, installmentCode, issueDate, expiredDate, paymentDate, installmentValue, paidValue, discountValue, interestValue, status (1=Normal, 2=Devolvido, 3=Cancelado, 4=Quebrado), chargeType, billingType, bearerCode, bearerName. Filtros úteis: startExpiredDate + endExpiredDate, statusList=[1], hasOpenInvoices=true. Para inadimplentes: statusList=[1] + endExpiredDate < hoje. Suporta expand: check, invoice, commissioneds, calculateValue.",
        inputSchema={"type":"object","properties":{
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos das filiais"},
            "customerCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos dos clientes"},
            "customerCpfCnpjList":{"type":"array","items":{"type":"string"},"description":"CPF/CNPJ dos clientes"},
            "startExpiredDate":{"type":"string","description":"Vencimento inicial (ISO 8601)"},
            "endExpiredDate":{"type":"string","description":"Vencimento final"},
            "startPaymentDate":{"type":"string","description":"Data pagamento inicial"},
            "endPaymentDate":{"type":"string","description":"Data pagamento final"},
            "startIssueDate":{"type":"string","description":"Data emissão inicial"},
            "endIssueDate":{"type":"string","description":"Data emissão final"},
            "change":{"type":"object","description":"Filtro oficial por alteração: {startDate,endDate,inCheck}"},
            "startChangeDate":{"type":"string","description":"Data alteração inicial"},
            "endChangeDate":{"type":"string","description":"Data alteração final"},
            "statusList":{"type":"array","items":{"type":"integer"},"description":"Status: 1=Normal, 2=Devolvido, 3=Cancelado, 4=Quebrado"},
            "documentTypeList":{"type":"array","items":{"type":"integer"},"description":"Tipo documento: 1=fatura, 2=cheque, 3=dinheiro, 4=cartão crédito, 5=cartão débito, 16=TED/DOC, 18=cheque presente"},
            "billingTypeList":{"type":"array","items":{"type":"integer"},"description":"Tipo faturamento: 1=Venda à vista, 2=Venda a prazo, 3=Recebimento à vista, 4=Recebimento a prazo, 12=Renegociação, 13=Cobrança cartão"},
            "dischargeTypeList":{"type":"array","items":{"type":"integer"},"description":"Tipo baixa: 0=Título não baixado, 1=Via recebimento, 7=Via banco, 9=Renegociação, 12=Conta bancária"},
            "chargeTypeList":{"type":"array","items":{"type":"integer"},"description":"Tipo cobrança: 0=Não está em cobrança, 1=Simples, 2=Descontada, 3=Caucionada, 5=Sem registro, 8=Protestado"},
            "hasOpenInvoices":{"type":"boolean","description":"Apenas faturas em aberto"},
            "receivableCodeList":{"type":"array","items":{"type":"number"},"description":"Códigos das faturas"},
            "ourNumberList":{"type":"array","items":{"type":"number"},"description":"Nosso número da parcela"},
            "commissionedCode":{"type":"integer","description":"Código do comissionado"},
            "commissionedCpfCnpj":{"type":"string","description":"CPF/CNPJ do comissionado"},
            "closingCodeCommission":{"type":"integer","description":"Código de fechamento da comissão. Use junto com os demais filtros de fechamento quando aplicável."},
            "closingCompanyCommission":{"type":"integer","description":"Empresa de fechamento da comissão. Não use isolado."},
            "closingDateCommission":{"type":"string","description":"Data de fechamento da comissão"},
            "closingCommissionedCode":{"type":"integer","description":"Código do comissionado no fechamento"},
            "closingCommissionedCpfCnpj":{"type":"string","description":"CPF/CNPJ do comissionado no fechamento"},
            "expand":{"type":"string","description":"Expansão: check, invoice, commissioneds, calculateValue"},
            "order":{"type":"string","description":"Ordenação: branchCode, customerCode, customerCpfCnpj, receivableCode, installmentCode, maxChangeFilterDate. Use - para desc."},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100,"description":"Máximo 100 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Ex: ['customerCode','installmentValue','expiredDate']."},
        }}),
    types.Tool(name="totvs_get_bank_slip", description="Base64 do boleto bancário de uma fatura. Requer código da fatura, parcela e cliente.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "customerCode":{"type":"integer","description":"Código do cliente"},
            "customerCpfCnpj":{"type":"string","description":"CPF/CNPJ do cliente (alternativa ao customerCode)"},
            "receivableCode":{"type":"integer","description":"Código da fatura (receivableCode)"},
            "installmentNumber":{"type":"integer","description":"Número da parcela da fatura"},
        },"required":["branchCode","customerCode","receivableCode","installmentNumber"]}),
    types.Tool(name="totvs_get_payment_link", description="Link de pagamento PIX de uma fatura.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "customerCode":{"type":"integer","description":"Código do cliente"},
            "customerCpfCnpj":{"type":"string","description":"CPF/CNPJ do cliente"},
            "receivableCode":{"type":"integer","description":"Código da fatura"},
            "installmentNumber":{"type":"integer","description":"Número da parcela"},
        },"required":["branchCode","receivableCode","installmentNumber"]}),
    types.Tool(name="totvs_get_gift_check_balances", description="Consulta saldo de cheque presente por cliente, número do cheque ou código de barras.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial (obrigatório se não informar barCode)"},
            "customerCode":{"type":"integer","description":"Código do cliente"},
            "customerCpfCnpj":{"type":"string","description":"CPF/CNPJ do cliente"},
            "checkNumber":{"type":"integer","description":"Número do cheque (obrigatório se não informar barCode)"},
            "barCode":{"type":"string","description":"Código de barras do cheque (quando informado, não passar branchCode/checkNumber)"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
        }}),
    types.Tool(name="totvs_change_charge_type", description="⚠️ ESCRITA — Altera tipo de cobrança de uma fatura a receber.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial da fatura"},
            "customerCode":{"type":"integer","description":"Código do cliente"},
            "customerCpfCnpj":{"type":"string","description":"CPF/CNPJ do cliente"},
            "receivableCode":{"type":"integer","description":"Código da fatura"},
            "installmentCode":{"type":"integer","description":"Código da parcela"},
            "chargeType":{"type":"integer","description":"Tipo de cobrança"},
            "observation":{"type":"string","description":"Observação a ser gravada no log"},
        },"required":["branchCode","customerCode","receivableCode","installmentCode","chargeType"]}),

    # ── ACCOUNTS RECEIVABLE v2.3 (completes module) ───────────────────────────
    types.Tool(name="totvs_create_receivable_invoice", description="⚠️ ESCRITA — Inclui fatura a receber. Use somente com dados validados pelo financeiro.",
        inputSchema={"type":"object","properties":{
            "branchCnpj":{"type":"string","description":"CNPJ da empresa que gravará a fatura, somente dígitos"},
            "customerCpfCnpj":{"type":"string","description":"CPF/CNPJ do cliente, somente dígitos"},
            "receivableCode":{"type":"integer","description":"Número da fatura"},
            "installments":{"type":"array","description":"Parcelas da fatura","items":{"type":"object","properties":{
                "installmentCode":{"type":"integer"},
                "documentType":{"type":"integer","description":"1=Fatura, 2=Cheque, 3=Dinheiro, 4=Cartão crédito, 5=Cartão débito, 16=TED/DOC, 18=Cheque presente, 20=CREDEV, 25=Voucher, 26=PIX, 50=Outro"},
                "billingType":{"type":"integer","description":"1=Venda à vista, 2=Venda a prazo, 3=Recebimento à vista, 4=Recebimento a prazo, 12=Renegociação, 18=Agrupamento de fatura"},
                "chargeType":{"type":"integer","description":"0=Não está em cobrança, 1=Simples, 2=Descontada, 3=Caucionada, 5=Sem registro, 18=Direto para boleto, 37=Carteira digital, 38=Bolepix"},
                "bearerCode":{"type":"integer"},
                "issueDate":{"type":"string"},
                "expiredDate":{"type":"string"},
                "originalExpirationDate":{"type":"string"},
                "installmentValue":{"type":"number"},
                "originalValue":{"type":"number"},
                "taxValue":{"type":"number"},
                "ourNumber":{"type":"integer"},
                "dacOurNumber":{"type":"string"},
                "observations":{"type":"array","items":{"type":"object"}},
                "checkInstallment":{"type":"object"},
                "cardInstallment":{"type":"object"},
                "classifications":{"type":"array","items":{"type":"object"}},
                "commissions":{"type":"array","items":{"type":"object"}},
                "revenues":{"type":"array","items":{"type":"object"}},
                "additionalFields":{"type":"array","items":{"type":"object"}},
                "taxes":{"type":"array","items":{"type":"object"}}
            },"required":["installmentCode","documentType","billingType","chargeType","bearerCode","issueDate","expiredDate","installmentValue"]}}
        },"required":["branchCnpj","customerCpfCnpj","receivableCode","installments"]}),
    types.Tool(name="totvs_settle_invoices", description="⚠️ ESCRITA — Baixa bancária de fatura a receber (somente para contas do tipo banco). Para pagamentos em dinheiro, cartão ou adiantamento use totvs_pay_invoices.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "customerCode":{"type":"integer","description":"Código do cliente"},
            "receivableCode":{"type":"integer","description":"Código da fatura"},
            "installmentCode":{"type":"integer","description":"Código da parcela"},
            "bankNumber":{"type":"integer","description":"Número do banco"},
            "agencyNumber":{"type":"integer","description":"Número da agência"},
            "account":{"type":"string","description":"Número da conta bancária"},
        },"required":["branchCode","customerCode","receivableCode","installmentCode","bankNumber","agencyNumber","account"]}),
    types.Tool(name="totvs_pay_invoices", description="⚠️ ESCRITA — Baixa/liquidação de faturas a receber com múltiplas formas de pagamento: cartão de crédito, débito, adiantamento (dinheiro/caixa), conta corrente ou CREDEV.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Filial da liquidação"},
            "settlementDate":{"type":"string","description":"Data da liquidação (ISO 8601, ex: 2026-04-27T00:00:00)"},
            "invoices":{"type":"array","description":"Lista de faturas a baixar","items":{
                "type":"object","properties":{
                    "branchCode":{"type":"integer","description":"Filial da fatura"},
                    "customerCode":{"type":"integer","description":"Código do cliente"},
                    "customerCpfCnpj":{"type":"string","description":"CPF/CNPJ do cliente (alternativa ao customerCode)"},
                    "receivableCode":{"type":"integer","description":"Código da fatura"},
                    "installmentCode":{"type":"integer","description":"Código da parcela"},
                    "paidValue":{"type":"number","description":"Valor pago"},
                    "interestValue":{"type":"number","description":"Valor de juros"},
                    "discountValue":{"type":"number","description":"Valor de desconto"},
                    "grossUpValue":{"type":"number","description":"Valor de acréscimo"},
                    "expensesValue":{"type":"number","description":"Valor de despesas financeiras"},
                },"required":["branchCode","customerCode","receivableCode","installmentCode","paidValue"],
            }},
            "payments":{"type":"array","description":"Lista de pagamentos","items":{
                "type":"object","properties":{
                    "value":{"type":"number","description":"Valor do pagamento"},
                    "paidType":{"type":"integer","description":"Tipo de pagamento: 1=CreditCard, 2=DebitCard, 3=Advance, 4=CurrentAccount, 5=CREDEV"},
                    "card":{"type":"object","description":"Dados do cartão, obrigatório para paidType 1 ou 2","properties":{
                        "nsu":{"type":"integer"},"autorization":{"type":"string"},"cardBrand":{"type":"string"},
                        "cardOperator":{"type":"string"},"installmentQuantity":{"type":"integer"},
                    }},
                    "bank":{"type":"object","description":"Dados bancários, obrigatório para paidType 4. Use accountCode OU bankNumber+agencyNumber+account.","properties":{
                        "bankNumber":{"type":"integer"},"agencyNumber":{"type":"integer"},
                        "account":{"type":"string"},"accountCode":{"type":"integer"},
                    }},
                    "credev":{"type":"object","description":"Dados de CREDEV para paidType 5","properties":{"branchCode":{"type":"integer"}}},
                    "movementDate":{"type":"string","description":"Data de movimento para conciliação (ISO 8601)"},
                },"required":["value","paidType"],
            }},
        },"required":["branchCode","settlementDate","invoices","payments"]}),
    types.Tool(name="totvs_move_gift_check", description="⚠️ ESCRITA — Movimenta cheque presente.",
        inputSchema={"type":"object","properties":{
            "value":{"type":"number","description":"Valor da movimentação"},
            "branchCode":{"type":"integer"},
            "customerCode":{"type":"integer"},
            "sequence":{"type":"integer"},
            "barCode":{"type":"string"}
        },"required":["value"]}),
    types.Tool(name="totvs_upsert_invoice_commission", description="⚠️ ESCRITA — Inclui ou altera comissão de fatura.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "customerCode":{"type":"integer"},
            "customerCpfCnpj":{"type":"string"},
            "receivableCode":{"type":"integer"},
            "installments":{"type":"array","description":"Lista UpsertCommissionInstallmentRequestModel (installmentCode, commissionedCode, commissionedPercentage)","items":{"type":"object"}}
        },"required":["receivableCode","installments"]}),

    types.Tool(name="totvs_create_gift_check", description="⚠️ ESCRITA — Inclui cheque presente para cliente.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "customerCode":{"type":"integer","description":"Código do cliente"},
            "customerCpfCnpj":{"type":"string","description":"CPF/CNPJ do cliente"},
            "value":{"type":"number","description":"Valor do cheque"},
            "nominated":{"type":"string","description":"Nominal (max 80 chars)"},
            "barCode":{"type":"string","description":"Código de barras (max 40, somente números)"},
            "issueDate":{"type":"string","description":"Data de emissão (ISO 8601)"},
            "expiredDate":{"type":"string","description":"Data de validade"},
        },"required":["branchCode","customerCode","value","nominated","barCode"]}),

    # ── FISCAL ───────────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_fiscal_invoices", description="Busca NF-e por período, cliente, status ou chave de acesso. Suporta expand para itens, pagamentos e observações.",
        inputSchema={"type":"object","properties":{
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de filiais (obrigatório)"},
            "invoiceSequenceList":{"type":"array","items":{"type":"integer"}},
            "invoiceCodeList":{"type":"array","items":{"type":"integer"}},
            "operationType":{"type":"string","enum":["All","Input","Output"],"description":"Tipo de operação: All, Input(Entrada), Output(Saída)"},
            "origin":{"type":"string","enum":["All","Own","ThirdParty"],"description":"Origem: All, Own(Emissão própria), ThirdParty(Emissão de terceiro)"},
            "invoiceStatusList":{"type":"array","items":{"type":"string","enum":["Canceled","Denied","Issued","Normal","Deleted"]}},
            "personCodeList":{"type":"array","items":{"type":"integer"}},
            "operationCodeList":{"type":"array","items":{"type":"integer"}},
            "documentTypeCodeList":{"type":"array","items":{"type":"integer"}},
            "personCpfCnpjList":{"type":"array","items":{"type":"string"}},
            "startIssueDate":{"type":"string","description":"ISO 8601"},
            "endIssueDate":{"type":"string"},
            "serialCodeList":{"type":"array","items":{"type":"string"}},
            "eletronicInvoiceStatusList":{"type":"array","items":{"type":"string","enum":["Authorized","Canceled","Denied","Sent","Generated","Rejected"]}},
            "startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},
            "amountLastDays":{"type":"integer"},
            "transactionBranchCode":{"type":"integer"},"transactionCode":{"type":"integer"},"transactionDate":{"type":"string"},
            "expand":{"type":"string","description":"shippingCompany,salesOrder,person,items,barCodes,taxes,payments,referencedInvoices,rateDifferential,relatedProductionOrder,observationNF,observationNFE,referencedTaxInvoices"},
            "order":{"type":"string","description":"Ordenação suportada: branchCode, invoiceSequence, invoiceDate, maxChangeFilterDate. Use - para desc."},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100,"description":"Máximo 100 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Ex: ['accessKey','invoiceCode','value']."},
        },"required":["branchCodeList"]}),
    types.Tool(name="totvs_get_nfe_xml", description="XML completo de uma NF-e pela chave de acesso (44 dígitos).",
        inputSchema={"type":"object","properties":{"accessKey":{"type":"string"}},"required":["accessKey"]}),
    types.Tool(name="totvs_get_invoice_item_detail", description="Detalhe de itens de NF-e. Informe accessKey OU branchCode + invoiceDate + invoiceSequence.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"invoiceDate":{"type":"string"},"invoiceSequence":{"type":"integer"},
            "accessKey":{"type":"string"},"expand":{"type":"string"},
            "BranchCode":{"type":"integer","description":"Alias oficial PascalCase"},"InvoiceDate":{"type":"string","description":"Alias oficial PascalCase"},
            "InvoiceSequence":{"type":"integer","description":"Alias oficial PascalCase"},"AccessKey":{"type":"string","description":"Alias oficial PascalCase"},"Expand":{"type":"string","description":"Alias oficial PascalCase"}
        }}),
    types.Tool(name="totvs_get_danfe", description="DANFE em base64 (PDF) de uma NF-e a partir do XML.",
        inputSchema={"type":"object","properties":{
            "mainInvoiceXml":{"type":"string","description":"Conteúdo XML da NF-e"},
            "nfeDocumentType":{"type":"string","description":"Tipo de documento NF-e"}
        },"required":["mainInvoiceXml"]}),
    types.Tool(name="totvs_search_invoice_products", description="Produtos de NF-e por período, produto, pessoa, chave ou operação.",
        inputSchema={"type":"object","properties":{
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de filiais (obrigatório)"},
            "productCodeList":{"type":"array","items":{"type":"integer"},"description":"Alias natural de ProductCodeList"},
            "ProductCodeList":{"type":"array","items":{"type":"integer"}},
            "batchBarCodeList":{"type":"array","items":{"type":"string"},"description":"Alias natural de BatchBarCodeList"},
            "BatchBarCodeList":{"type":"array","items":{"type":"string"}},
            "invoiceCodeList":{"type":"array","items":{"type":"integer"}},
            "operationType":{"type":"string","description":"E=Entrada, S=Saída"},
            "modality":{"type":"string"},
            "origin":{"type":"string"},
            "invoiceStatusList":{"type":"array","items":{"type":"string"}},
            "personCodeList":{"type":"array","items":{"type":"integer"}},
            "operationCodeList":{"type":"array","items":{"type":"integer"}},
            "personCpfCnpjList":{"type":"array","items":{"type":"string"}},
            "startIssueDate":{"type":"string"},"endIssueDate":{"type":"string"},
            "accessKeyList":{"type":"array","items":{"type":"string"},"description":"Alias natural de acessKeyList"},
            "acessKeyList":{"type":"array","items":{"type":"string"}},
            "option":{"type":"object"},
            "expand":{"type":"string","description":"batchItems"},
            "order":{"type":"string"},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."},
        },"required":["branchCodeList"]}),
    types.Tool(name="totvs_get_cost_center", description="Centros de custo por período de alteração.",
        inputSchema={"type":"object","properties":{
            "startChangeDate":{"type":"string","description":"Data inicial ISO 8601 (obrigatório)"},
            "endChangeDate":{"type":"string","description":"Data final ISO 8601 (obrigatório)"},
            "isInactive":{"type":"boolean"},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}
        },"required":["startChangeDate","endChangeDate"]}),
    types.Tool(name="totvs_get_digital_certificates", description="Dados de certificados digitais de uma filial.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial (obrigatório)"},
            "environmentType":{"type":"string","description":"P=Produção, H=Homologação (obrigatório)"}
        },"required":["branchCode","environmentType"]}),
    types.Tool(name="totvs_get_pending_conditional_products", description="Saldo de produtos em condicional (consignação) pendentes por pessoa.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial (obrigatório)"},
            "onlyPendingItem":{"type":"boolean","default":True,"description":"Apenas itens com saldo pendente"},
            "personCode":{"type":"integer"},"personCpfCnpj":{"type":"string"}
        },"required":["branchCode"]}),
    types.Tool(name="totvs_get_disabled_invoices", description="NF-e inutilizadas por período e filial.",
        inputSchema={"type":"object","properties":{
            "startDate":{"type":"string","description":"Data inicial ISO 8601 (obrigatório)"},
            "endDate":{"type":"string","description":"Data final ISO 8601 (obrigatório)"},
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de filiais (obrigatório)"},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},
            "order":{"type":"array","items":{"type":"object"}}
        },"required":["startDate","endDate","branchCodeList"]}),
    types.Tool(name="totvs_print_transaction", description="Impressão de transação fiscal em PDF (base64).",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"transactionCode":{"type":"integer"},
            "transactionDate":{"type":"string"}
        }}),
    types.Tool(name="totvs_create_nfe_manifestation", description="⚠️ Manifestação do destinatário de NF-e (ciência, confirmação, desconhecimento, não realização).",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"accessKey":{"type":"string"},
            "manifestationType":{"type":"string","description":"Tipo de manifestação"}
        },"required":["branchCode","accessKey","manifestationType"]}),

    # ── GENERAL ──────────────────────────────────────────────────────────────
    types.Tool(name="totvs_get_payment_conditions", description="Condições de pagamento disponíveis.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"}}}),
    types.Tool(name="totvs_get_operations", description="Operações disponíveis (entrada/saída). Requer ao menos um filtro.",
        inputSchema={"type":"object","properties":{"operationCodeList":{"type":"array","items":{"type":"integer"}},"operationTypeList":{"type":"array","items":{"type":"string"},"description":"E - Entrada, S - Saída"},"startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},"isInactive":{"type":"boolean","description":"true=inativas, false=ativas"},"pageSize":{"type":"integer","default":1000}}}),
    types.Tool(name="totvs_simulate_payment_plan", description="Simula cálculo de plano de pagamento.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"paymentPlanCode":{"type":"integer"},"totalAmount":{"type":"number"}},"required":["branchCode","paymentPlanCode","totalAmount"]}),
    types.Tool(name="totvs_search_devolutions", description="Consulta dados de devolução por código.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"devolutionCode":{"type":"integer"},"expand":{"type":"string","description":"classifications, items"}},"required":["branchCode","devolutionCode"]}),
    types.Tool(name="totvs_get_payment_plans", description="Planos de pagamento ativos disponíveis.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_get_transactions", description="Dados de uma transação por filial e código.",
        inputSchema={"type":"object","properties":{
            "BranchCode":{"type":"integer"},"TransactionCode":{"type":"integer"},
            "TransactionDate":{"type":"string"}
        }}),
    types.Tool(name="totvs_search_transactions", description="Lista transacoes por filial, cliente, data, alteracao e expansao. Use para consultar movimentos/transacoes sem saber o codigo exato.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Filial; usado para montar branchCodeList quando branchCodeList nao vier"},
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Obrigatorio no Swagger"},
            "transactionCodeList":{"type":"array","items":{"type":"integer"}},
            "transactionDate":{"type":"string"},
            "customerCodeList":{"type":"array","items":{"type":"integer"}},
            "customerCpfCnpjList":{"type":"array","items":{"type":"string"}},
            "startChangeDate":{"type":"string"},
            "endChangeDate":{"type":"string"},
            "expand":{"type":"string","description":"itemPromotionalEngines,originDestination,additionalInformation"},
            "order":{"type":"string","description":"branchCode,transactionCode,transactionDate,maxChangeFilterDate"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100,"description":"Maximo 500 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"}}
        }}),
    types.Tool(name="totvs_get_classifications", description="Classificações de produto disponíveis.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_create_devolution", description="⚠️ Grava dados de devolução.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"devolutionCode":{"type":"integer"},
            "stage":{"type":"string"}
        },"required":["branchCode","devolutionCode"]}),
    types.Tool(name="totvs_create_transaction", description="⚠️ Inclui uma transação.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"transactionCode":{"type":"integer"},
            "transactionDate":{"type":"string"}
        },"required":["branchCode","transactionCode"]}),
    types.Tool(name="totvs_create_product_count", description="⚠️ Cria contagem de produtos no estoque.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"products":{"type":"array","items":{"type":"object"}}
        },"required":["branchCode","products"]}),
    types.Tool(name="totvs_create_financial_compensation", description="⚠️ ESCRITA — Cria compensacao financeira conforme payload oficial do Swagger.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "items":{"type":"array","items":{"type":"object"}}
        }}),
    types.Tool(name="totvs_add_product_count_additional_count", description="⚠️ ESCRITA — Adiciona contagem complementar a uma contagem de produto.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "countNumber":{"type":"integer"},
            "items":{"type":"array","items":{"type":"object"}}
        }}),
    types.Tool(name="totvs_create_relationship_counts", description="⚠️ ESCRITA — Relaciona contagens a uma transacao.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "transactionCode":{"type":"integer"},
            "transactionDate":{"type":"string"},
            "counts":{"type":"array","items":{"type":"object"}}
        }}),
    types.Tool(name="totvs_create_transaction_classification_relationship", description="⚠️ ESCRITA — Vincula classificacoes a uma transacao.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "transactionCode":{"type":"integer"},
            "transactionDate":{"type":"string"},
            "classifications":{"type":"array","items":{"type":"object"}}
        }}),

    # ── ACCOUNT PAYABLE ───────────────────────────────────────────────────────
    types.Tool(name="totvs_search_payable_duplicates", description="Consulta duplicatas de contas a pagar com filtros flexíveis de vencimento, emissão, fornecedor e status.",
        inputSchema={"type":"object","properties":{
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos das filiais (obrigatório)"},
            "change":{"type":"object","description":"Filtro oficial por alteração: {startDate,endDate}. Quando informado, use branchCodeList."},
            "duplicateCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos das duplicatas"},
            "supplierCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos dos fornecedores"},
            "bearerCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos dos portadores"},
            "startIssueDate":{"type":"string","description":"Data emissão inicial (ISO 8601)"},
            "endIssueDate":{"type":"string","description":"Data emissão final"},
            "startExpiredDate":{"type":"string","description":"Data vencimento inicial"},
            "endExpiredDate":{"type":"string","description":"Data vencimento final"},
            "startSettlementDate":{"type":"string","description":"Data liquidação inicial"},
            "endSettlementDate":{"type":"string","description":"Data liquidação final"},
            "startArrivalDate":{"type":"string","description":"Data chegada inicial"},
            "endArrivalDate":{"type":"string","description":"Data chegada final"},
            "startChangeDate":{"type":"string","description":"Data alteração inicial"},
            "endChangeDate":{"type":"string","description":"Data alteração final"},
            "inclusionTypeList":{"type":"array","items":{"type":"integer"},"description":"Tipo de inclusão: 1=Manual, 2=Automatic, 3=ViaCashier, 4=Payroll, 5=OwnCheckExchange, 6=CostsApportionment, 7=RevenueApportionment, 9=Conversion, 11-14 entre empresas"},
            "status":{"type":"string","enum":["Grouped","Canceled","Retorned","CommissionSettled","Normal","Broken"],"description":"Status: Grouped, Canceled, Retorned, CommissionSettled, Normal, Broken"},
            "documentTypeList":{"type":"array","items":{"type":"integer"},"description":"Tipo de documento: 1=Duplicate, 2=InvoicePrint/Boleto, 3=Commission, 4=Guide, 6=Voucher, 7=Invoice, 12=BankDeposit, 16=TedDoc, 30=GiftCheck, 50=OutherTitle"},
            "order":{"type":"string","description":"Ordenação suportada: productCode, maxChangeFilterDate. Use - para desc."},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100,"description":"Máximo 100 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Ex: ['supplierName','balanceValue','expiredDate']."},
        },"required":["branchCodeList"]}),
    types.Tool(name="totvs_search_commissions_paid", description="Fechamento de comissão por período e representante/comissionado.",
        inputSchema={"type":"object","properties":{
            "closingCompanyCode":{"type":"integer","description":"Código da empresa de fechamento de comissão (obrigatório)"},
            "closingCode":{"type":"integer","description":"Número do fechamento de comissão"},
            "startClosingDate":{"type":"string","description":"Data inicial do fechamento (ISO 8601)"},
            "endClosingDate":{"type":"string","description":"Data final do fechamento"},
            "commissionedCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos dos comissionados"},
            "commissionedCpfCnpjList":{"type":"array","items":{"type":"string"},"description":"CPF/CNPJ dos comissionados"},
            "expand":{"type":"string","description":"Expansão: accountMovements"},
            "order":{"type":"string","description":"Ordenação: closingDate, commissionedCode"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."},
        },"required":["closingCompanyCode"]}),
    types.Tool(name="totvs_create_duplicate", description="⚠️ ESCRITA — Inclui duplicata a pagar. Requer CNPJ da empresa, CPF/CNPJ do fornecedor, código da duplicata e lista de parcelas.",
        inputSchema={"type":"object","properties":{
            "branchCnpj":{"type":"string","description":"CNPJ da empresa (max 14 chars)"},
            "supplierCpfCnpj":{"type":"string","description":"CPF ou CNPJ do fornecedor (max 14 chars)"},
            "duplicateCode":{"type":"integer","description":"Código da duplicata (max 10 chars)"},
            "installments":{"type":"array","description":"Lista de parcelas","items":{"type":"object","properties":{
                "installmentCode":{"type":"integer","description":"Número da parcela (max 3)"},
                "bearerCode":{"type":"integer","description":"Código do portador (max 4)"},
                "issueDate":{"type":"string","description":"Data de emissão (ISO 8601)"},
                "dueDate":{"type":"string","description":"Data de vencimento"},
                "arrivalDate":{"type":"string","description":"Data de chegada"},
                "document":{"type":"integer","description":"Tipo documento: 1=Duplicata, 2=NotaFiscal, 7=Fatura, 15=Recibo..."},
                "prevision":{"type":"integer","description":"Tipo previsão: 1=Previsto, 2=Real, 3=Consignação"},
                "stage":{"type":"integer","description":"Estágio: 1=NF não conferida, 2=Liberado pagamento, 5=NF aceita, 20=Pagto banco, 90=Encerrado"},
                "duplicateValue":{"type":"number","description":"Valor da parcela"},
                "expenses":{"type":"array","description":"Lista de despesas","items":{"type":"object","properties":{
                    "expenseCode":{"type":"integer"},"costCenterCode":{"type":"integer"},"proratedPercentage":{"type":"number"}
                },"required":["expenseCode","costCenterCode","proratedPercentage"]}},
            },"required":["installmentCode","bearerCode","issueDate","dueDate","arrivalDate","document","prevision","stage","duplicateValue","expenses"]}},
        },"required":["branchCnpj","supplierCpfCnpj","duplicateCode","installments"]}),
    types.Tool(name="totvs_group_duplicates", description="⚠️ ESCRITA — Agrupa duplicatas a pagar. Útil para logística/frete quando há uso recorrente de agrupamento.",
        inputSchema={"type":"object","properties":{
            "branchCnpj":{"type":"string","description":"CNPJ da empresa que gravará a duplicata agrupada, somente dígitos"},
            "supplierCpfCnpj":{"type":"string","description":"CPF/CNPJ do fornecedor, somente dígitos"},
            "duplicateCode":{"type":"integer","description":"Código da duplicata agrupadora"},
            "document":{"type":"integer","enum":[1,18],"description":"Tipo documento: 1=Duplicata, 18=Conhecimento de frete"},
            "dueDate":{"type":"string","description":"Data de vencimento ISO 8601"},
            "groupInstallments":{"type":"array","description":"Duplicatas que serão agrupadas","items":{"type":"object","properties":{
                "branchCnpj":{"type":"string"},
                "supplierCpfCnpj":{"type":"string"},
                "duplicateCode":{"type":"integer"},
                "installmentCode":{"type":"integer"}
            },"required":["branchCnpj","supplierCpfCnpj","duplicateCode","installmentCode"]}}
        },"required":["branchCnpj","supplierCpfCnpj","duplicateCode","dueDate","groupInstallments"]}),

    # ── PURCHASE ORDER ────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_purchase_orders", description="Pedidos de compra por filtro. Use expand='items' para carregar itens. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de códigos de empresa"},
            "change":{"type":"object","description":"Filtro oficial por alteração: {startDate,endDate}. Quando informado, use branchCodeList."},
            "orderCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos dos pedidos de compra"},
            "supplierOrderCodeList":{"type":"array","items":{"type":"string"},"description":"Números de pedido do fornecedor"},
            "supplierCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos dos fornecedores"},
            "supplierCpfCnpjList":{"type":"array","items":{"type":"string"},"description":"CPF/CNPJ dos fornecedores"},
            "orderStatusList":{"type":"array","items":{"type":"integer"},"description":"Situação do pedido: 1=Em andamento, 2=Liberado baixa, 3=Parcialmente recebido, 4=Atendido, 5=Bloqueado, 6=Cancelado, 7=Distribuído, 8=Pré-pedido"},
            "statusList":{"type":"array","items":{"type":"integer"},"description":"Alias legado de orderStatusList"},
            "operationCodeList":{"type":"array","items":{"type":"integer"}},
            "startBasePaymentDate":{"type":"string"},
            "endBasePaymentDate":{"type":"string"},
            "startDeliveryForecastDate":{"type":"string"},
            "endDeliveryForecastDate":{"type":"string"},
            "startDeliveryDeadlineDate":{"type":"string"},
            "endDeliveryDeadlineDate":{"type":"string"},
            "productCodeList":{"type":"array","items":{"type":"integer"}},
            "startDate":{"type":"string","description":"Alias legado para change.startDate"},
            "endDate":{"type":"string","description":"Alias legado para change.endDate"},
            "expand":{"type":"string","description":"Expansões suportadas pelo Swagger: items"},
            "order":{"type":"string","description":"Ordenação suportada: branchCode, orderCode, maxChangeFilterDate. Use - para desc."},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}
        }}),
    types.Tool(name="totvs_create_purchase_order", description="⚠️ Inclui pedido de compra.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"supplierCode":{"type":"integer"},
            "operationCode":{"type":"integer"},"items":{"type":"array","items":{"type":"object"}},
            "orderDate":{"type":"string"}
        },"required":["branchCode","supplierCode","operationCode","items"]}),
    types.Tool(name="totvs_cancel_purchase_order", description="⚠️ Cancela pedido de compra.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"orderCode":{"type":"integer"},
            "reasonCancellationCode":{"type":"integer"}
        },"required":["branchCode","orderCode"]}),
    types.Tool(name="totvs_change_purchase_order_status", description="⚠️ Altera situação do pedido de compra.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"orderCode":{"type":"integer"},
            "newStatus":{"type":"string"}
        },"required":["branchCode","orderCode","newStatus"]}),

    # ── SELLER ────────────────────────────────────────────────────────────────
    types.Tool(name="totvs_link_purchase_order_batch", description="⚠️ ESCRITA — Cria ou atualiza vinculo de item de lote com pedido de compra e nota fiscal.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "batchCode":{"type":"integer"},
            "sequence":{"type":"integer"},
            "batchItemBarCode":{"type":"string"},
            "orderCode":{"type":"integer"},
            "invoice":{"type":"object"}
        }}),
    types.Tool(name="totvs_update_purchase_order_item_quantities", description="⚠️ ESCRITA — Altera quantidade solicitada dos itens de um pedido de compra.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "items":{"type":"array","items":{"type":"object"}}
        }}),

    types.Tool(name="totvs_search_sellers", description="Lista vendedores e empresas vinculadas. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"sellerCodeList":{"type":"array","items":{"type":"integer"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
    types.Tool(name="totvs_get_seller_operational_area", description="Regiões de atuação de vendedores.",
        inputSchema={"type":"object","properties":{
            "sellerCode":{"type":"integer"},"branchCode":{"type":"integer"}
        }}),
    types.Tool(name="totvs_get_seller_operational_area_state", description="Regiões de atuação de vendedores por estado.",
        inputSchema={"type":"object","properties":{
            "startChangeDate":{"type":"string"},
            "endChangeDate":{"type":"string"},
            "operationalAreaCode":{"type":"integer"},
            "order":{"type":"string","description":"operationalAreaCode,maxChangeFilterDate"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":1000},
            "fields":{"type":"array","items":{"type":"string"}}
        }}),
    types.Tool(name="totvs_get_seller_area_by_cep", description="Vendedor responsável por um CEP.",
        inputSchema={"type":"object","properties":{
            "cep":{"type":"string","description":"CEP (somente dígitos)"},
            "branchCode":{"type":"integer"}
        },"required":["cep"]}),
    types.Tool(name="totvs_get_seller_area_by_city", description="Vendedor responsável por uma cidade.",
        inputSchema={"type":"object","properties":{
            "cityCode":{"type":"integer"},"branchCode":{"type":"integer"}
        },"required":["cityCode"]}),

    # ── VOUCHER ───────────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_voucher", description="Consulta vouchers/cupons. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{"voucherCode":{"type":"string"},"customerCode":{"type":"integer"},"branchCode":{"type":"integer","description":"Código da filial"},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
    types.Tool(name="totvs_create_voucher", description="⚠️ ESCRITA — Cria voucher/cupom.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"value":{"type":"number"},"expirationDate":{"type":"string"},"customerCode":{"type":"integer"}},"required":["branchCode","value"]},
        annotations=WRITE_TOOL_ANNOTATIONS),

    # ── MANAGEMENT ────────────────────────────────────────────────────────────
    types.Tool(name="totvs_get_users", description="Lista usuários do TOTVS Moda.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_get_global_parameters", description="Parâmetros corporativos do TOTVS por código.",
        inputSchema={"type":"object","properties":{
            "parameterCodeList":{"type":"array","items":{"type":"string"},"description":"Códigos dos parâmetros (obrigatório)"}
        },"required":["parameterCodeList"]}),
    types.Tool(name="totvs_get_branch_parameters", description="Parâmetros de filial por código.",
        inputSchema={"type":"object","properties":{
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos das filiais (obrigatório)"},
            "parameterCodeList":{"type":"array","items":{"type":"string"},"description":"Códigos dos parâmetros (obrigatório)"}
        },"required":["branchCodeList","parameterCodeList"]}),

    # ── GLOBAL / LOCATION ─────────────────────────────────────────────────────
    types.Tool(name="totvs_get_cep", description="Endereço completo pelo CEP.",
        inputSchema={"type":"object","properties":{"cep":{"type":"string","description":"Somente dígitos ex: 86020040"}},"required":["cep"]}),
    types.Tool(name="totvs_get_countries", description="Lista de países disponíveis.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_get_states", description="Lista de estados/UFs.",
        inputSchema={"type":"object","properties":{"countryCode":{"type":"string"}}}),
    types.Tool(name="totvs_get_cities", description="Lista de cidades.",
        inputSchema={"type":"object","properties":{"stateCode":{"type":"string"},"countryCode":{"type":"string"}}}),

    # ── PRODUCTION ORDER ──────────────────────────────────────────────────────
    types.Tool(name="totvs_search_production_orders", description="Ordens de produção por filtro. Use expand para carregar grupos como items, materials, locations e productionNotes. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de empresas"},
            "change":{"type":"object","description":"Filtro oficial por alteração: {startDate,endDate}. Quando informado, use branchCodeList."},
            "cycleCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de ciclos"},
            "orderCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de ordens de produção"},
            "statusList":{"type":"array","items":{"type":"integer"},"description":"Status: 5=Bloqueada, 10=Aguardando liberação, 20=Em andamento, 30=Finalizada, 40=Cancelada"},
            "placeCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de locais da OP"},
            "materialClassificationList":{"type":"array","items":{"type":"object"},"description":"Classificações de matéria-prima: [{typeCode, classificationCodeList}]"},
            "startDate":{"type":"string","description":"Alias legado para change.startDate"},
            "endDate":{"type":"string","description":"Alias legado para change.endDate"},
            "expand":{"type":"string","description":"Expansões suportadas: observations,classifications,references,locations,programmings,items,materials,relationships,relationshipItems,productionNotes,productFinishedQuantitiesTypes,orderFinishedQuantitiesTypes"},
            "order":{"type":"string","description":"Ordenação suportada: branchCode, cycleCode, orderCode, maxChangeFilterDate. Use - para desc."},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100,"description":"Máximo 500 no Swagger"},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}
        }}),
    types.Tool(name="totvs_get_pending_material_consumption", description="Fichas de consumo de matéria-prima pendentes em ordens de produção.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"orderCode":{"type":"integer"},
            "startDate":{"type":"string"},"endDate":{"type":"string"},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}
        }}),
    types.Tool(name="totvs_create_material_movement", description="⚠️ Movimentação de matéria-prima em ordem de produção.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"orderCode":{"type":"integer"},
            "movementDate":{"type":"string"},"items":{"type":"array","items":{"type":"object"}}
        },"required":["branchCode","orderCode","movementDate","items"]}),

    # ── IMAGE ─────────────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_product_images", description="Consulta imagens de produto por filtro.",
        inputSchema={"type":"object","properties":{
            "referenceCode":{"type":"string"},
            "productCodeList":{"type":"array","items":{"type":"integer"}},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
        }}),
    types.Tool(name="totvs_upload_product_image", description="⚠️ Importa imagem de produto (com vínculo). Imagem deve estar em base64.",
        inputSchema={"type":"object","properties":{
            "productCode":{"type":"integer"},
            "referenceCode":{"type":"string"},
            "imageBase64":{"type":"string","description":"Imagem em base64"},
            "branchCode":{"type":"integer"},
            "imageType":{"type":"string"},
            "order":{"type":"integer"},
            "colorCode":{"type":"string"},
        },"required":["imageBase64"]}),
    types.Tool(name="totvs_import_image_no_link", description="⚠️ Importa imagem sem realizar vínculo com produto (vínculo posterior).",
        inputSchema={"type":"object","properties":{
            "imageBase64":{"type":"string","description":"Imagem em base64"},
            "fileName":{"type":"string"},
        },"required":["imageBase64"]}),
    types.Tool(name="totvs_upload_person_image", description="⚠️ Insere imagem de uma pessoa.",
        inputSchema={"type":"object","properties":{
            "personCode":{"type":"integer"},
            "personCpfCnpj":{"type":"string"},
            "imageBase64":{"type":"string"},
        },"required":["imageBase64"]}),
    types.Tool(name="totvs_list_person_images", description="Lista imagens de uma pessoa.",
        inputSchema={"type":"object","properties":{
            "personCode":{"type":"integer"},
            "personCpfCnpj":{"type":"string"},
        }}),
    types.Tool(name="totvs_get_person_image_base64", description="Retorna imagem de pessoa em base64.",
        inputSchema={"type":"object","properties":{
            "personCode":{"type":"integer"},
            "imageId":{"type":"string"},
        }}),

    # ── VOUCHER (extras) ──────────────────────────────────────────────────────
    types.Tool(name="totvs_update_voucher", description="⚠️ Altera dados de um voucher existente.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"voucherCode":{"type":"integer"},
            "value":{"type":"number"},"expirationDate":{"type":"string"}
        },"required":["branchCode","voucherCode"]}),
    types.Tool(name="totvs_create_customer_vouchers", description="⚠️ Cria vouchers em lote para uma lista de clientes.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},"customerCodeList":{"type":"array","items":{"type":"integer"}},
            "value":{"type":"number"},"expirationDate":{"type":"string"}
        },"required":["branchCode","customerCodeList","value"]}),

    # ── DATA PACKAGE ─────────────────────────────────────────────────────────
    types.Tool(name="totvs_list_input_packages", description="Lista pacotes de importação de dados (data-package). Filtra por destinatário, status, modelo e período.",
        inputSchema={"type":"object","properties":{
            "Target":{"type":"string","description":"Identificador do destinatário"},
            "Status":{"type":"string","description":"Status: Active, Rejected, Finished, RestrictionFinished, Canceled"},
            "ModelCode":{"type":"integer","description":"Código do modelo de pacote"},
            "ModelCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de códigos de modelo"},
            "Source":{"type":"string","description":"Identificador da origem"},
            "InitialInsertDate":{"type":"string","description":"Data inicial de inclusão (ISO 8601)"},
            "FinalInsertDate":{"type":"string","description":"Data final de inclusão"},
            "InitialMovementDate":{"type":"string","description":"Data inicial de movimento"},
            "FinalMovementDate":{"type":"string","description":"Data final de movimento"},
            "Page":{"type":"integer","default":1},
            "PageSize":{"type":"integer","default":1000},
            "Order":{"type":"string"},
        }}),
    types.Tool(name="totvs_get_package", description="Retorna informações de um pacote de dados pelo ID.",
        inputSchema={"type":"object","properties":{"packageId":{"type":"string","description":"Identificador único do pacote"}},"required":["packageId"]}),
    types.Tool(name="totvs_get_package_content", description="Retorna o conteúdo (Base64) de um pacote de dados pelo ID.",
        inputSchema={"type":"object","properties":{"packageId":{"type":"string","description":"Identificador único do pacote"}},"required":["packageId"]}),
    types.Tool(name="totvs_list_output_packages", description="Lista pacotes de exportação de dados. Requer identificador do destinatário (target).",
        inputSchema={"type":"object","properties":{
            "target":{"type":"string","description":"Identificador do destinatário (obrigatório)"},
            "ModelCode":{"type":"integer","description":"Código do modelo de pacote"},
            "ModelCodeList":{"type":"array","items":{"type":"integer"}},
            "Source":{"type":"string","description":"Identificador da origem"},
            "InitialInsertDate":{"type":"string","description":"Data inicial de inclusão (ISO 8601)"},
            "FinalInsertDate":{"type":"string","description":"Data final de inclusão"},
            "InitialMovementDate":{"type":"string","description":"Data inicial de movimento"},
            "FinalMovementDate":{"type":"string","description":"Data final de movimento"},
            "Page":{"type":"integer","default":1},
            "PageSize":{"type":"integer","default":1000},
        },"required":["target"]}),
    types.Tool(name="totvs_create_input_package", description="⚠️ ESCRITA — Inclui pacote de dados para importação. O conteúdo deve estar em Base64.",
        inputSchema={"type":"object","properties":{
            "modelCode":{"type":"integer","description":"Código do modelo de pacote"},
            "source":{"type":"string","description":"Identificador da origem"},
            "target":{"type":"string","description":"Identificador do destinatário"},
            "movementDate":{"type":"string","description":"Data de movimento (ISO 8601)"},
            "content":{"type":"string","description":"Conteúdo do pacote em Base64"},
            "id":{"type":"string","description":"ID único do pacote (gerado automaticamente se omitido)"},
            "name":{"type":"string","description":"Descrição adicional"},
            "priority":{"type":"integer","description":"Prioridade (menor = mais prioritário)"},
        },"required":["modelCode","source","target","movementDate","content"]}),
    types.Tool(name="totvs_receive_output_package", description="⚠️ ESCRITA — Marca pacote de exportação como recebido.",
        inputSchema={"type":"object","properties":{"packageId":{"type":"string","description":"ID do pacote"}},"required":["packageId"]}),
    types.Tool(name="totvs_reactivate_package", description="⚠️ ESCRITA — Reativa pacote rejeitado, mudando situação para 'Em andamento'.",
        inputSchema={"type":"object","properties":{"packageId":{"type":"string","description":"ID do pacote rejeitado"}},"required":["packageId"]}),

    # ── INSTRUCTIONS ──────────────────────────────────────────────────────────
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

    # ── CONTEXT ───────────────────────────────────────────────────────────────
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

    # ── AGGREGATORS v2.4 ──────────────────────────────────────────────────────
    types.Tool(name="totvs_get_products_sold", description="Agrega vendas de produtos em um período. Retorna os TOP N produtos mais vendidos já agregados por quantidade ou valor — elimina a necessidade de buscar pedidos, expandir items, e agregar manualmente. Retorna: {period, totalOrders, topProducts: [{productCode, name, totalQuantity, totalValue, orderCount}]}.",
        inputSchema={"type":"object","properties":{
            "startDate":{"type":"string","description":"YYYY-MM-DD"},
            "endDate":{"type":"string","description":"YYYY-MM-DD"},
            "branchCodeList":{"type":"array","items":{"type":"integer"}},
            "categoryCode":{"type":"integer"},
            "topN":{"type":"integer","default":10},
            "orderBy":{"type":"string","enum":["quantity","value"],"default":"quantity"}
        },"required":["startDate","endDate"]}),

    types.Tool(name="totvs_sales_summary_by_period", description="Resumo de vendas agregado por filial, status ou dia. Retorna: {period, totalValue, totalOrders, groupBy, groups: [{key, label, orderCount, totalValue}]} ordenado por totalValue desc. Use para responder 'faturamento da semana por filial', 'pedidos por status este mês', etc.",
        inputSchema={"type":"object","properties":{
            "startDate":{"type":"string"},
            "endDate":{"type":"string"},
            "groupBy":{"type":"string","enum":["branch","status","day"],"default":"branch"},
            "branchCodeList":{"type":"array","items":{"type":"integer"}}
        },"required":["startDate","endDate"]}),

    types.Tool(name="totvs_top_customers", description="Top N clientes por faturamento em um período. Retorna: {period, customers: [{customerCode, customerName, customerCpfCnpj, orderCount, totalValue, averageOrderValue}]} ordenado por totalValue desc. Use para 'quem compra mais', análise de concentração de clientes.",
        inputSchema={"type":"object","properties":{
            "startDate":{"type":"string"},
            "endDate":{"type":"string"},
            "topN":{"type":"integer","default":10},
            "branchCodeList":{"type":"array","items":{"type":"integer"}}
        },"required":["startDate","endDate"]}),

    types.Tool(name="totvs_low_stock_alert", description="Produtos com saldo abaixo de um threshold em uma filial. Retorna: {threshold, branchCode, lowStockCount, products: [{productCode, name, productSku, balance}]} ordenado por balance asc. Use para alertas de reposição.",
        inputSchema={"type":"object","properties":{
            "threshold":{"type":"number","description":"Saldo mínimo"},
            "branchCode":{"type":"integer"},
            "productCodeList":{"type":"array","items":{"type":"integer"}},
            "topN":{"type":"integer","default":50}
        },"required":["threshold","branchCode"]}),

    types.Tool(name="totvs_orders_by_status_summary", description="Distribuição de pedidos por status em um período. Retorna: {period, totalOrders, totalValue, byStatus: [{status, orderCount, totalValue, percentage}]} ordenado por totalValue desc. Use para ver gargalos (muitos Blocked?) e health do funil.",
        inputSchema={"type":"object","properties":{
            "startDate":{"type":"string"},
            "endDate":{"type":"string"},
            "branchCodeList":{"type":"array","items":{"type":"integer"}}
        },"required":["startDate","endDate"]}),

    # ── Aggregators v3.3 — speed tools ────────────────────────────────
    types.Tool(name="totvs_daily_dashboard", description="Painel completo do dia em 1 chamada: vendas (lista + total + por status) + contas a receber + contas a pagar (aberto vs pago). Use para 'como foi o dia', 'resumo de hoje', 'vendas + financeiro do dia'. Para somente vendas de hoje prefira totvs_sales_today_summary. Retorna: {date, sales: {totalOrders, totalValue, orders[], byStatus[]}, receivable: {count, totalValue, items[]}, payable: {count, totalOpen, totalPaid, open[], paid[]}}.",
        inputSchema={"type":"object","properties":{
            "date":{"type":"string","description":"YYYY-MM-DD (default=hoje)"},
            "branchCodeList":{"type":"array","items":{"type":"integer"}}
        }}),

    types.Tool(name="totvs_customer_360", description="Visão 360 de UM cliente em 1 chamada: dados cadastrais + histórico completo de pedidos + flag recompra + ticket médio. Use para 'dados do cliente X', 'histórico de compras do cliente X', 'é recompra?'. NÃO use para vendas gerais/de hoje. Retorna: {customer: {code, name, cpfCnpj}, orders: {count, totalValue, firstOrder, lastOrder, items[]}, isRepeatBuyer, averageTicket}.",
        inputSchema={"type":"object","properties":{
            "customerCode":{"type":"integer","description":"Código do cliente"},
            "customerCpfCnpj":{"type":"string","description":"CPF ou CNPJ do cliente"}
        }}),

    types.Tool(name="totvs_stock_available", description="Produtos com estoque disponível (saldo > 0), já filtrado. Pagina internamente e retorna apenas SKUs em estoque. Para pronta entrega comercial use productKind='finished'. Retorna: {branchCode, productKind, totalSkus, totalUnits, products: [{productCode, productName, colorName, sizeName, stock, salesOrder}]}.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Filial (default 1)"},
            "referenceCodeList":{"type":"array","items":{"type":"string"},"description":"Filtrar por referências"},
            "productCodeList":{"type":"array","items":{"type":"integer"},"description":"Filtrar por códigos"},
            "productKind":{"type":"string","enum":["all","finished","raw_material","bulk"],"description":"Tipo de produto: all=tudo, finished=produto acabado, raw_material=matéria-prima, bulk=material de consumo. Default all; para pronta entrega use finished."},
            "onlyActive":{"type":"boolean","description":"Filtrar produtos ativos no branchInfo. Default true quando productKind != all."},
            "minStock":{"type":"number","description":"Saldo mínimo (default 1)"},
            "pageSize":{"type":"integer","description":"Itens por página interna (default 1000)"},
            "concurrency":{"type":"integer","description":"Páginas paralelas (default 10, max 20)"},
            "maxPages":{"type":"integer","description":"Limite de segurança de páginas (default 100)"}
        }}),

    types.Tool(name="totvs_product_360", description="Visão 360 do produto em 1 chamada: cadastro, saldos, preços, custos, composição e ficha de consumo em paralelo. Use para 'dados do produto X'.",
        inputSchema={"type":"object","properties":{
            "productCode":{"type":"integer","description":"Código do produto"},
            "code":{"type":"integer","description":"Alias de productCode"},
            "branchCode":{"type":"integer","description":"Filial (default 1)"},
            "priceCodeList":{"type":"array","items":{"type":"integer"},"description":"Tabelas de preço (default do contexto inicial)"},
            "costCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos de custo (default do contexto inicial)"},
            "stockCodeList":{"type":"array","items":{"type":"integer"},"description":"Estoques (default do contexto inicial)"},
            "pageSize":{"type":"integer","description":"Itens por seção (default 100)"}
        }}),

    types.Tool(name="totvs_raw_material_360", description="Visão 360 de matéria-prima em 1 chamada: dados de produto, estoque, custos e usos em ficha de consumo. Use para 'sobre a matéria-prima X'.",
        inputSchema={"type":"object","properties":{
            "rawMaterialCode":{"type":"integer","description":"Código da matéria-prima"},
            "productCode":{"type":"integer","description":"Alias de rawMaterialCode"},
            "code":{"type":"integer","description":"Alias de rawMaterialCode"},
            "branchCode":{"type":"integer","description":"Filial (default 1)"},
            "costCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos de custo (default do contexto inicial)"},
            "stockCodeList":{"type":"array","items":{"type":"integer"},"description":"Estoques (default do contexto inicial)"},
            "pageSize":{"type":"integer","description":"Itens por seção (default 100)"}
        }}),

    types.Tool(name="totvs_order_360", description="Visão 360 do pedido em 1 chamada: cabeçalho/itens, notas vinculadas e itens pendentes. Use para 'dados do pedido X'.",
        inputSchema={"type":"object","properties":{
            "orderCode":{"type":"integer","description":"Código do pedido"},
            "branchCode":{"type":"integer","description":"Filial, se souber"},
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Filiais para localizar o pedido"},
            "expand":{"type":"string","description":"Expand do pedido (default items)"}
        },"required":["orderCode"]}),

    types.Tool(name="totvs_invoice_360", description="Visão 360 da NF em 1 chamada: cabeçalho fiscal e produtos da nota em paralelo. Use para 'dados da nf X'.",
        inputSchema={"type":"object","properties":{
            "invoiceCode":{"type":"integer","description":"Número/código da NF"},
            "invoiceSequence":{"type":"integer","description":"Sequencial interno da NF"},
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Filiais (default do contexto)"},
            "pageSize":{"type":"integer","description":"Itens no cabeçalho (default 20)"},
            "productPageSize":{"type":"integer","description":"Produtos da NF (default 100)"}
        }}),

    types.Tool(name="totvs_sales_today_summary", description="Resumo rápido de vendas de uma data em 1 chamada: total de pedidos, valor total, status e ranking/lista de pedidos. PRIMEIRA OPÇÃO para 'vendas de hoje', 'vendas de hj', 'o que vendi hoje', 'traga as vendas de hoje', 'quanto vendi' e resumo de vendas.",
        inputSchema={"type":"object","properties":{
            "date":{"type":"string","description":"YYYY-MM-DD (default=hoje)"},
            "branchCodeList":{"type":"array","items":{"type":"integer"}},
            "topN":{"type":"integer","description":"Pedidos no ranking (default 50)"},
            "pageSize":{"type":"integer","description":"Itens lidos (default 500)"}
        }}),

    types.Tool(name="totvs_new_customers_today", description="Clientes novos em uma data por primeira compra no histórico. Use para 'algum cliente novo?'.",
        inputSchema={"type":"object","properties":{
            "date":{"type":"string","description":"YYYY-MM-DD (default=hoje)"},
            "branchCodeList":{"type":"array","items":{"type":"integer"}},
            "lookbackStartDate":{"type":"string","description":"Início do histórico (default 2020-01-01)"},
            "concurrency":{"type":"integer","description":"Clientes verificados em paralelo (default 10, max 20)"},
            "pageSize":{"type":"integer","description":"Pedidos do dia lidos (default 500)"}
        }}),

    types.Tool(name="totvs_sales_by_representative", description="Resumo executivo de vendas por representante/vendedor em um periodo. Use para diretoria comercial e ranking de representantes. Retorna representatives[] com representativeCode, representativeName, orderCount, totalValue, blockedValue e averageTicket.",
        inputSchema={"type":"object","properties":{
            "startDate":{"type":"string","description":"YYYY-MM-DD"},
            "endDate":{"type":"string","description":"YYYY-MM-DD"},
            "branchCodeList":{"type":"array","items":{"type":"integer"}},
            "topN":{"type":"integer","description":"Quantidade no ranking (default 20)"},
            "pageSize":{"type":"integer","description":"Pedidos lidos (default 500)"}
        },"required":["startDate","endDate"]}),

    types.Tool(name="totvs_sales_by_channel", description="Resumo executivo de vendas por canal em um periodo. Agrupa automaticamente por integrationCode/operacao, ou pelo campo informado em channelField. Use para comparar canais, ecommerce, loja, operacoes e origem de venda.",
        inputSchema={"type":"object","properties":{
            "startDate":{"type":"string","description":"YYYY-MM-DD"},
            "endDate":{"type":"string","description":"YYYY-MM-DD"},
            "branchCodeList":{"type":"array","items":{"type":"integer"}},
            "channelField":{"type":"string","description":"Campo do pedido usado para agrupar. Default auto; exemplos: integrationCode, operationCode, operationName."},
            "topN":{"type":"integer","description":"Quantidade no ranking (default 20)"},
            "pageSize":{"type":"integer","description":"Pedidos lidos (default 500)"}
        },"required":["startDate","endDate"]}),

    types.Tool(name="totvs_overdue_financial_summary", description="Titulos em atraso no contas a receber e contas a pagar. Use para gerente financeiro/diretoria: inadimplencia, maiores clientes em atraso, fornecedores vencidos e posicao liquida vencida.",
        inputSchema={"type":"object","properties":{
            "asOfDate":{"type":"string","description":"Data limite YYYY-MM-DD (default=hoje)"},
            "startDate":{"type":"string","description":"Inicio da busca de vencimentos (default 2000-01-01)"},
            "branchCodeList":{"type":"array","items":{"type":"integer"}},
            "topN":{"type":"integer","description":"Quantidade nos rankings (default 20)"},
            "pageSize":{"type":"integer","description":"Titulos lidos por lado (default 500)"}
        }}),

    types.Tool(name="totvs_cash_flow_forecast", description="Fluxo de caixa previsto por vencimento: contas a receber, contas a pagar e saldo liquido por dia. Use para 'quanto tenho para receber/pagar nos proximos dias'.",
        inputSchema={"type":"object","properties":{
            "startDate":{"type":"string","description":"Data inicial YYYY-MM-DD (default=hoje)"},
            "endDate":{"type":"string","description":"Data final YYYY-MM-DD; se omitida usa days"},
            "days":{"type":"integer","description":"Quantidade de dias se endDate omitida (default 7)"},
            "branchCodeList":{"type":"array","items":{"type":"integer"}},
            "pageSize":{"type":"integer","description":"Titulos lidos por lado (default 500)"}
        }}),

    types.Tool(name="totvs_product_stock_by_kind_summary", description="Resumo de estoque por tipo: produto acabado, materia-prima e material a granel. Use para diretor, gerente de producao e PCP. Retorna total de SKUs/unidades e topProducts por tipo. Usa cache curto de saldo.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Filial (default do contexto)"},
            "productKindList":{"type":"array","items":{"type":"string","enum":["finished","raw_material","bulk"]},"description":"Tipos a consultar (default finished, raw_material, bulk)"},
            "minStock":{"type":"number","description":"Saldo minimo (default 1)"},
            "topN":{"type":"integer","description":"Produtos por tipo (default 10)"},
            "pageSize":{"type":"integer","description":"Itens por pagina interna (default 1000)"},
            "concurrency":{"type":"integer","description":"Paginas paralelas (default 10, max 20)"},
            "maxPages":{"type":"integer","description":"Limite de seguranca de paginas (default 100)"}
        }}),

    types.Tool(name="totvs_open_purchase_orders", description="Pedidos de compra em aberto em 1 chamada rápida. Pagina em paralelo, filtra status abertos e retorna totais, resumo por status, mais recentes e maiores valores. Use para 'pedidos de compra em aberto'.",
        inputSchema={"type":"object","properties":{
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Filiais (default do contexto)"},
            "openStatusList":{"type":"array","items":{"type":"integer"},"description":"Status TOTVS considerados abertos (default padrão [1,3,5])"},
            "topN":{"type":"integer","description":"Quantidade nos rankings (default 20)"},
            "concurrency":{"type":"integer","description":"Paginas paralelas (default 10, max 20)"},
            "pageSize":{"type":"integer","description":"Itens por pagina (default 100)"},
            "maxPages":{"type":"integer","description":"Limite de seguranca de paginas (default 100)"}
        }}),

    types.Tool(name="totvs_open_production_orders", description="Ordens de produção em aberto em 1 chamada rápida. Pagina em paralelo, considera aberta quando pendingQuantity > 0 e endDate vazio, e retorna totais, status, atrasadas, recentes e maiores pendências. Use para 'ordens de produção em aberto'.",
        inputSchema={"type":"object","properties":{
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Filiais (default do contexto)"},
            "topN":{"type":"integer","description":"Quantidade nos rankings (default 20)"},
            "concurrency":{"type":"integer","description":"Paginas paralelas (default 10, max 20)"},
            "pageSize":{"type":"integer","description":"Itens por pagina (default 100)"},
            "maxPages":{"type":"integer","description":"Limite de seguranca de paginas (default 100)"},
            "asOfDate":{"type":"string","description":"YYYY-MM-DD para calcular atrasos (default=hoje)"}
        }}),

    # ── Usage Intelligence ────────────────────────────────────────────
    types.Tool(name="totvs_get_usage_insights", description="Análise de padrões de uso do MCP server. Retorna: tools mais usadas, sequências frequentes, horários de pico, padrões de parâmetros e sugestões de otimização. Use para entender como o sistema está sendo utilizado e onde otimizar. Dados locais, sem chamada externa.",
        inputSchema={"type":"object","properties":{
            "days":{"type":"integer","description":"Dias para análise (default 30)","default":30}
        }}),
]

if ANALYTICS_ENABLED:
    TOOLS.append(
        types.Tool(
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
    )


# ---------------------------------------------------------------------------
# Routing table
# ---------------------------------------------------------------------------

ROUTING: dict[str, tuple[str, str]] = {
    "totvs_search_orders":                       ("sales_order", "search_orders"),
    "totvs_get_order_invoices":                  ("sales_order", "get_order_invoices"),
    "totvs_get_pending_items":                   ("sales_order", "get_pending_items"),
    "totvs_get_billing_suggestions":             ("sales_order", "get_billing_suggestions"),
    "totvs_cancel_order":                        ("sales_order", "cancel_order"),
    "totvs_change_order_status":                 ("sales_order", "change_order_status"),
    "totvs_update_order_items_price":            ("sales_order", "update_order_items_price"),
    "totvs_create_order":                        ("sales_order", "create_order"),
    "totvs_update_order_header":                 ("sales_order", "update_order_header"),
    "totvs_get_order_classifications":           ("sales_order", "get_classifications"),
    "totvs_get_discount_types":                  ("sales_order", "get_discount_types"),
    "totvs_create_pdv_transaction":              ("sales_order", "create_pdv_transaction"),
    "totvs_create_order_relationship_batch_items": ("sales_order", "create_relationship_batch_items"),
    "totvs_suggest_order_batch_items_by_nuance": ("sales_order", "suggest_batch_items_by_nuance"),
    "totvs_search_products":                     ("product", "search_products"),
    "totvs_get_product":                         ("product", "get_product"),
    "totvs_search_product_balances":             ("product", "search_balances"),
    "totvs_search_product_prices":               ("product", "search_prices"),
    "totvs_search_price_tables":                 ("product", "search_price_tables"),
    "totvs_search_product_references":           ("product", "search_references"),
    "totvs_get_product_grid":                    ("product", "get_grid"),
    "totvs_search_product_colors":               ("product", "search_colors"),
    "totvs_search_product_batch":                ("product", "search_batch"),
    "totvs_get_kardex_movement":                 ("product", "get_kardex_movement"),
    "totvs_search_product_compositions":         ("product", "search_compositions"),
    "totvs_get_product_additional_field_types":  ("product", "get_additional_field_types"),
    "totvs_get_product_classification_types":    ("product", "get_classification_types"),
    "totvs_get_product_composition_group_product": ("product", "get_composition_group_product"),
    "totvs_get_product_composition_product":     ("product", "get_composition_product"),
    "totvs_get_product_instruction_items":       ("product", "get_instruction_items"),
    "totvs_get_product_price_table_scales":      ("product", "get_price_table_scales"),
    "totvs_get_product_grouper_configurations":  ("product", "get_product_grouper_configurations"),
    "totvs_search_consumption_sheet":            ("product_engineering", "search_consumption_sheet"),
    "totvs_search_engineering_services":         ("product_engineering", "search_services"),
    "totvs_get_engineering_operations":          ("product_engineering", "get_operations"),
    "totvs_search_engineering_applications":     ("product_engineering", "search_applications"),
    "totvs_search_engineering_default":          ("product_engineering", "search_engineering_default"),
    "totvs_get_engineering_configurations":      ("product_engineering", "get_engineering_configurations"),
    "totvs_create_engineering_references":       ("product_engineering", "create_references_from_engineering"),
    "totvs_search_material_requests":            ("material_request", "search_material_requests"),
    "totvs_create_material_request":             ("material_request", "create_material_request"),
    "totvs_add_material_request_items":          ("material_request", "add_items"),
    "totvs_modify_material_request_header":      ("material_request", "modify_header"),
    "totvs_modify_material_request_items":       ("material_request", "modify_items"),
    "totvs_remove_material_request_items":       ("material_request", "remove_items"),
    "totvs_cancel_material_request_items":       ("material_request", "cancel_items"),
    "totvs_approve_material_request":            ("material_request", "approve"),
    "totvs_move_material_request_items":         ("material_request", "move_items"),
    "totvs_search_product_prototypes":           ("product_prototype", "search_prototypes"),
    "totvs_create_product_prototype":            ("product_prototype", "create_prototype"),
    "totvs_update_product_prototype":            ("product_prototype", "update_prototype"),
    "totvs_search_product_storage":              ("logistics", "search_product_storage"),
    "totvs_upsert_product_packaging":            ("logistics", "upsert_product_packaging"),
    "totvs_add_product_packaging_quantity":      ("logistics", "add_product_packaging"),
    "totvs_subtract_product_packaging_quantity": ("logistics", "subtract_product_packaging"),
    "totvs_create_product_classification":        ("product", "create_classification_relationship"),
    "totvs_create_product_value":                 ("product", "create_product_value"),
    "totvs_update_product_price":                ("product", "update_product_price"),
    "totvs_update_product_price_only":           ("product", "update_product_price_only"),
    "totvs_update_product_cost":                 ("product", "update_product_cost"),
    "totvs_update_promotion_price":              ("product", "update_promotion_price"),
    "totvs_search_product_codes":                ("product", "search_product_codes"),
    "totvs_search_product_costs":                ("product", "search_costs"),
    "totvs_get_product_category":                ("product", "get_category"),
    "totvs_get_product_classifications":         ("product", "get_classifications"),
    "totvs_get_measurement_units":               ("product", "get_measurement_units"),
    "totvs_search_omni_changed_balances":        ("product", "search_omni_changed_balances"),
    "totvs_update_product_data":                 ("product", "update_product_data"),
    "totvs_update_product_simple":               ("product", "update_product_simple"),
    "totvs_update_product_branch_info_batch":    ("product", "update_product_branch_info_batch"),
    "totvs_create_product_barcode":              ("product", "create_barcode"),
    "totvs_create_product_batch":                ("product", "create_batch"),
    "totvs_update_product_batch_info":           ("product", "update_batch_info"),
    "totvs_create_product_batch_preferential_sales_order": ("product", "create_batch_preferential_sales_order"),
    "totvs_upsert_product_color":                ("product", "upsert_color"),
    "totvs_create_product_grid":                 ("product", "create_grid"),
    "totvs_search_individual_customers":         ("person", "search_individuals"),
    "totvs_search_legal_customers":              ("person", "search_legal_entities"),
    "totvs_get_customer_bonus_balance":          ("person", "list_bonus_balance"),
    "totvs_get_person_statistics":               ("person", "get_person_statistics"),
    "totvs_create_or_update_individual_customer":("person", "create_or_update_individual_customer"),
    "totvs_create_or_update_legal_customer":     ("person", "create_or_update_legal_customer"),
    "totvs_get_branches_list":                   ("person", "get_branches_list"),
    "totvs_search_representatives":              ("person", "search_representatives"),
    "totvs_get_person_classifications":          ("person", "get_classifications"),
    "totvs_remove_person_classification_relationship": ("person", "remove_classification_relationship"),
    "totvs_get_email_types":                     ("person", "get_email_types"),
    "totvs_get_phone_types":                     ("person", "get_phone_types"),
    "totvs_get_contact_types":                   ("person", "get_contact_types"),
    "totvs_search_reception_sale":               ("person", "search_reception_sale"),
    "totvs_consume_bonus":                       ("person", "consume_bonus"),
    "totvs_create_person_message":               ("person", "create_message"),
    "totvs_relate_customer_representatives":     ("person", "relate_customer_representatives"),
    "totvs_change_person_message":               ("person", "change_message"),
    "totvs_search_customer_financial_balance":   ("accounts_receivable", "search_customer_financial_balance"),
    "totvs_search_receivable_documents":         ("accounts_receivable", "search_documents"),
    "totvs_get_bank_slip":                       ("accounts_receivable", "get_bank_slip"),
    "totvs_get_payment_link":                    ("accounts_receivable", "get_payment_link"),
    "totvs_get_gift_check_balances":             ("accounts_receivable", "get_gift_check_balances"),
    "totvs_change_charge_type":                  ("accounts_receivable", "change_charge_type"),
    "totvs_create_receivable_invoice":           ("accounts_receivable", "create_invoice"),
    "totvs_settle_invoices":                     ("accounts_receivable", "settle_invoices"),
    "totvs_pay_invoices":                        ("accounts_receivable", "pay_invoices"),
    "totvs_create_gift_check":                   ("accounts_receivable", "create_gift_check"),
    "totvs_search_fiscal_invoices":              ("fiscal", "search_invoices"),
    "totvs_get_nfe_xml":                         ("fiscal", "get_xml_content"),
    "totvs_get_invoice_item_detail":             ("fiscal", "get_invoice_item_detail"),
    "totvs_get_danfe":                           ("fiscal", "get_danfe"),
    "totvs_search_invoice_products":             ("fiscal", "search_invoice_products"),
    "totvs_get_cost_center":                     ("fiscal", "get_cost_center"),
    "totvs_get_digital_certificates":            ("fiscal", "get_digital_certificates"),
    "totvs_get_pending_conditional_products":    ("fiscal", "get_pending_conditional_products"),
    "totvs_get_disabled_invoices":               ("fiscal", "get_disabled_invoices"),
    "totvs_print_transaction":                   ("fiscal", "print_transaction"),
    "totvs_create_nfe_manifestation":            ("fiscal", "create_manifestation"),
    "totvs_get_payment_conditions":              ("general", "get_payment_conditions"),
    "totvs_get_operations":                      ("general", "get_operations"),
    "totvs_simulate_payment_plan":               ("general", "simulate_payment_plan"),
    "totvs_search_devolutions":                  ("general", "search_devolutions"),
    "totvs_get_payment_plans":                   ("general", "get_payment_plans"),
    "totvs_get_transactions":                    ("general", "get_transactions"),
    "totvs_search_transactions":                 ("general", "search_transactions"),
    "totvs_get_classifications":                 ("general", "get_classifications"),
    "totvs_create_devolution":                   ("general", "create_devolution"),
    "totvs_create_transaction":                  ("general", "create_transaction"),
    "totvs_create_product_count":                ("general", "create_product_count"),
    "totvs_create_financial_compensation":       ("general", "create_financial_compensation"),
    "totvs_add_product_count_additional_count":  ("general", "add_product_count_additional_count"),
    "totvs_create_relationship_counts":          ("general", "create_relationship_counts"),
    "totvs_create_transaction_classification_relationship": ("general", "create_transaction_classification_relationship"),
    "totvs_search_payable_duplicates":           ("account_payable", "search_duplicates"),
    "totvs_search_commissions_paid":             ("account_payable", "search_commissions_paid"),
    "totvs_create_duplicate":                    ("account_payable", "create_duplicate"),
    "totvs_group_duplicates":                    ("account_payable", "group_duplicates"),
    "totvs_search_purchase_orders":              ("purchase_order", "search_purchase_orders"),
    "totvs_create_purchase_order":               ("purchase_order", "create_purchase_order"),
    "totvs_cancel_purchase_order":               ("purchase_order", "cancel_purchase_order"),
    "totvs_change_purchase_order_status":        ("purchase_order", "change_purchase_order_status"),
    "totvs_link_purchase_order_batch":           ("purchase_order", "link_purchase_order_batch"),
    "totvs_update_purchase_order_item_quantities": ("purchase_order", "update_purchase_order_item_quantities"),
    "totvs_search_sellers":                      ("seller", "search_sellers"),
    "totvs_get_seller_operational_area":         ("seller", "get_operational_area"),
    "totvs_get_seller_operational_area_state":   ("seller", "get_operational_area_state"),
    "totvs_get_seller_area_by_cep":              ("seller", "get_operational_area_by_cep"),
    "totvs_get_seller_area_by_city":             ("seller", "get_operational_area_by_city"),
    "totvs_search_voucher":                      ("voucher", "search_voucher"),
    "totvs_create_voucher":                      ("voucher", "create_voucher"),
    "totvs_get_users":                           ("management", "get_users"),
    "totvs_get_global_parameters":               ("management", "get_global_parameters"),
    "totvs_get_branch_parameters":               ("management", "get_branch_parameters"),
    "totvs_get_cep":                             ("global", "get_cep"),
    "totvs_get_countries":                       ("global", "get_countries"),
    "totvs_get_states":                          ("global", "get_states"),
    "totvs_get_cities":                          ("global", "get_cities"),
    "totvs_search_production_orders":            ("production_order", "search_production_orders"),
    "totvs_get_pending_material_consumption":    ("production_order", "get_pending_material_consumption"),
    "totvs_create_material_movement":            ("production_order", "create_material_movement"),
    "totvs_search_product_images":               ("image", "search_product_images"),
    "totvs_upload_product_image":                ("image", "upload_product_image"),
    "totvs_import_image_no_link":                ("image", "import_image_no_link"),
    "totvs_upload_person_image":                 ("image", "upload_person_image"),
    "totvs_list_person_images":                  ("image", "list_person_images"),
    "totvs_get_person_image_base64":             ("image", "get_person_image_base64"),
    "totvs_update_voucher":                      ("voucher", "update_voucher"),
    "totvs_create_customer_vouchers":            ("voucher", "create_customer_vouchers"),
    "totvs_list_input_packages":                 ("data_package", "list_input_packages"),
    "totvs_get_package":                         ("data_package", "get_package"),
    "totvs_get_package_content":                 ("data_package", "get_package_content"),
    "totvs_list_output_packages":                ("data_package", "list_output_packages"),
    "totvs_create_input_package":                ("data_package", "create_input_package"),
    "totvs_receive_output_package":              ("data_package", "receive_output_package"),
    "totvs_reactivate_package":                  ("data_package", "reactivate_package"),

    # Sales Order v2.3
    "totvs_add_order_items":                    ("sales_order", "add_order_items"),
    "totvs_remove_order_item":                  ("sales_order", "remove_order_item"),
    "totvs_cancel_order_items":                 ("sales_order", "cancel_order_items"),
    "totvs_change_order_item_quantity":         ("sales_order", "change_order_item_quantity"),
    "totvs_update_order_items_additional":      ("sales_order", "update_order_items_additional"),
    "totvs_add_order_observation":              ("sales_order", "add_order_observation"),
    "totvs_update_order_shipping":              ("sales_order", "update_order_shipping"),
    "totvs_update_order_additional":            ("sales_order", "update_order_additional"),
    "totvs_search_batch_items":                 ("sales_order", "search_batch_items"),
    "totvs_get_changed_batch_items":            ("sales_order", "get_changed_batch_items"),
    "totvs_create_order_relationship_counts":   ("sales_order", "create_order_relationship_counts"),

    # Product v2.3
    "totvs_update_barcode":                     ("product", "update_barcode"),
    "totvs_create_reference":                   ("product", "create_reference"),
    "totvs_create_classification_type":         ("product", "create_classification_type"),

    # Accounts Receivable v2.3
    "totvs_move_gift_check":                    ("accounts_receivable", "move_gift_check"),
    "totvs_upsert_invoice_commission":          ("accounts_receivable", "upsert_invoice_commission"),

    # Aggregators v2.4
    "totvs_get_products_sold":                  ("aggregators", "get_products_sold"),
    "totvs_sales_summary_by_period":            ("aggregators", "sales_summary_by_period"),
    "totvs_top_customers":                      ("aggregators", "top_customers"),
    "totvs_low_stock_alert":                    ("aggregators", "low_stock_alert"),
    "totvs_orders_by_status_summary":           ("aggregators", "orders_by_status_summary"),

    # Aggregators v3.3 — speed tools
    "totvs_daily_dashboard":                    ("aggregators", "daily_dashboard"),
    "totvs_customer_360":                       ("aggregators", "customer_360"),
    "totvs_stock_available":                    ("aggregators", "stock_available"),
    "totvs_product_360":                        ("aggregators", "product_360"),
    "totvs_raw_material_360":                   ("aggregators", "raw_material_360"),
    "totvs_order_360":                          ("aggregators", "order_360"),
    "totvs_invoice_360":                        ("aggregators", "invoice_360"),
    "totvs_sales_today_summary":                ("aggregators", "sales_today_summary"),
    "totvs_new_customers_today":                ("aggregators", "new_customers_today"),
    "totvs_sales_by_representative":            ("aggregators", "sales_by_representative"),
    "totvs_sales_by_channel":                   ("aggregators", "sales_by_channel"),
    "totvs_overdue_financial_summary":          ("aggregators", "overdue_financial_summary"),
    "totvs_cash_flow_forecast":                 ("aggregators", "cash_flow_forecast"),
    "totvs_product_stock_by_kind_summary":      ("aggregators", "product_stock_by_kind_summary"),
    "totvs_open_purchase_orders":               ("aggregators", "open_purchase_orders"),
    "totvs_open_production_orders":             ("aggregators", "open_production_orders"),
    "totvs_analytics_call":                     ("analytics", "call_endpoint"),
}


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return TOOLS


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
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    route = ROUTING.get(name)
    if not route:
        return [types.TextContent(type="text", text=json.dumps({"error": f"Tool '{name}' não encontrada."}))]

    module_key, method_name = route
    module = get_modules().get(module_key)

    try:
        result = await getattr(module, method_name)(arguments)
        duration = (time.time() - t0) * 1000
        usage_tracker.track(name, arguments, duration_ms=duration)
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    except Exception as exc:
        duration = (time.time() - t0) * 1000
        usage_tracker.track(name, arguments, duration_ms=duration)
        logger.exception(f"Erro: {name}")
        return [types.TextContent(type="text", text=json.dumps({"error": str(exc), "tool": name}, ensure_ascii=False))]


async def main() -> None:
    logger.info(f"TOTVS Moda MCP Server v3.8.0 — {len(TOOLS)} tools | {len(get_modules())} módulos")
    try:
        await context_cache.load_context(get_client())
    except Exception as e:
        logger.warning(f"Falha ao carregar contexto na inicialização: {e}")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            InitializationOptions(
                server_name="totvs-moda-mcp",
                server_version="3.8.0",
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
