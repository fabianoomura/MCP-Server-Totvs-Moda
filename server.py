"""
TOTVS Moda MCP Server v3.0.0
=============================
MCP server para API V2 do TOTVS Moda.
15 módulos | ~111 tools | OAuth2 ROPC

Author: ATL4S
"""

import asyncio
import json
import logging
import os
import sys
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
from tools.aggregators import AggregatorTools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("totvs-moda-mcp")

server = Server("totvs-moda-mcp")

_client: TotvsClient | None = None
_modules: dict[str, Any] = {}


def get_client() -> TotvsClient:
    global _client
    if _client is None:
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
            "aggregators":         AggregatorTools(c),
        }
    return _modules


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
            "orderStatusList":{"type":"array","items":{"type":"string"},"description":"Digitado,Confirmado,Cancelado,Bloqueado,Faturado,EmFaturamento,Pendente,Encerrado"},
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos das filiais"},
            "operationCodeList":{"type":"array","items":{"type":"integer"}},
            "startBillingForecastDate":{"type":"string"},"endBillingForecastDate":{"type":"string"},
            "expand":{"type":"string","description":"items,invoices,shippingAddress,observations,classifications,discounts,commissioneds,counts"},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},
            "order":{"type":"string","description":"Ex: -orderCode"},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Ex: ['orderCode','customerName','totalValue']. Suporta notação aninhada: 'items.productCode'."},
        }}),
    types.Tool(name="totvs_get_order_invoices", description="NF-e vinculadas a um pedido de venda.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"}},"required":["branchCode","orderCode"]}),
    types.Tool(name="totvs_get_pending_items", description="Itens pendentes de faturamento em um pedido.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"}},"required":["branchCode","orderCode"]}),
    types.Tool(name="totvs_get_billing_suggestions", description="Sugestões de faturamento do TOTVS.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"}},"required":["branchCode"]}),
    types.Tool(name="totvs_cancel_order", description="⚠️ ESCRITA — Cancela pedido de venda (irreversível). Somente pedidos não aceitos na retaguarda podem ser cancelados.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "orderCode":{"type":"integer"},
            "reasonCancellationCode":{"type":"integer","description":"Código do motivo de cancelamento (obrigatório)"},
            "ReasonCancellationDescription":{"type":"string","description":"Descrição do cancelamento (max 80 chars)"}
        },"required":["branchCode","orderCode","reasonCancellationCode"]}),
    types.Tool(name="totvs_change_order_status", description="⚠️ ESCRITA — Altera situação do pedido. Aceita apenas valores do enum: InProgress (Em andamento), BillingReleased (Liberado p/ faturamento), Blocked (Bloqueado), InComposition (Em composição), InAnalysis (Em análise).",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial"},
            "orderCode":{"type":"integer"},
            "statusOrder":{"type":"string","enum":["InProgress","BillingReleased","Blocked","InComposition","InAnalysis"],"description":"Nova situação do pedido"},
            "reasonBlockingCode":{"type":"integer","description":"Código do motivo de bloqueio (apenas para statusOrder=Blocked)"},
            "reasonBlockingDescription":{"type":"string","description":"Descrição do motivo de bloqueio"}
        },"required":["branchCode","orderCode","statusOrder"]}),
    types.Tool(name="totvs_update_order_items_price", description="⚠️ ESCRITA — Altera preço de itens do pedido.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"},"items":{"type":"array","items":{"type":"object","properties":{"itemSequential":{"type":"integer"},"price":{"type":"number"}},"required":["itemSequential","price"]}}},"required":["branchCode","orderCode","items"]}),

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
    types.Tool(name="totvs_create_order_relationship_counts", description="⚠️ ESCRITA — Vincula contagens ao pedido.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer"},
            "orderCode":{"type":"integer"},
            "orderId":{"type":"string"},
            "counts":{"type":"array","description":"Lista de contagens (countCode, etc)","items":{"type":"object"}}
        },"required":["counts"]}),

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
    types.Tool(name="totvs_get_order_classifications", description="Classificações de pedido disponíveis para uma filial.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial (obrigatório)"}
        },"required":["branchCode"]}),
    types.Tool(name="totvs_get_discount_types", description="Tipos de desconto disponíveis para pedido de venda.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial (obrigatório)"}
        },"required":["branchCode"]}),

    # ── PRODUCT ──────────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_products", description="Busca produtos por filtro. Retorna items[] com: productCode, name, productSku, referenceCode, colorCode, size, categoryCode, isActive, barcode. Filtros comuns: productCodeList, referenceCodeList, categoryCodeList, productName (busca parcial), isActive. NÃO retorna preço — use totvs_search_product_prices. NÃO retorna saldo — use totvs_search_product_balances. Use fields=['productCode','name','referenceCode'] para respostas enxutas.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCodeList":{"type":"array","items":{"type":"integer"}},"referenceCodeList":{"type":"array","items":{"type":"string"}},"categoryCodeList":{"type":"array","items":{"type":"integer"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
    types.Tool(name="totvs_get_product", description="Dados completos de um produto/pack pelo código.",
        inputSchema={"type":"object","properties":{"code":{"type":"integer"},"branchCode":{"type":"integer","description":"Código da filial"}},"required":["code"]}),
    types.Tool(name="totvs_search_product_balances", description="Consulta saldos de estoque. Retorna items[] com: productCode, name, productSku, branchCode, balance (quantidade disponível), reservedBalance. Aceita filter.branchCodeList, filter.productCodeList, filter.referenceCodeList. Para alertas de estoque baixo (< threshold) use totvs_low_stock_alert. Use fields=['productCode','balance'] se quiser apenas quantidades.",
        inputSchema={"type":"object","properties":{
            "branchCode":{"type":"integer","description":"Código da filial (padrão 1)"},
            "stockCodeList":{"type":"array","items":{"type":"integer"},"description":"Tipos de saldo (padrão [1])"},
            "isSalesOrder":{"type":"boolean","description":"Incluir saldo reservado em pedidos de venda"},
            "productCodeList":{"type":"array","items":{"type":"integer"}},
            "referenceCodeList":{"type":"array","items":{"type":"string"}},
            "expand":{"type":"string","description":"locations"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":1000},
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
            "classifications":{"type":"array","items":{"type":"object","properties":{"type":{"type":"integer"},"codeList":{"type":"array","items":{"type":"string"}}}},"description":"Filtro por classificação: [{type: 11, codeList: ['7']}]"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
            "order":{"type":"string"},
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
    types.Tool(name="totvs_search_product_compositions", description="Composições de produto (ficha técnica). Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCodeList":{"type":"array","items":{"type":"integer"}},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
    types.Tool(name="totvs_create_product_classification", description="⚠️ ESCRITA — Vincula classificações a uma lista de produtos em lote.",
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
        }
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
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCode":{"type":"integer"},"promotionPrice":{"type":"number"},"startDate":{"type":"string"},"endDate":{"type":"string"}},"required":["branchCode","productCode","promotionPrice"]}),
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
    types.Tool(name="totvs_search_individual_customers", description="Busca clientes pessoa física por CPF, nome ou código. Para buscar cliente por CPF ou CNPJ sem saber se é PF ou PJ, use totvs_search_customer_by_document (detecta automaticamente pelo tamanho do documento). Use fields=['code','name','cpfCnpj'] para respostas pequenas.",
        inputSchema={"type":"object","properties":{"cpfList":{"type":"array","items":{"type":"string"}},"customerCodeList":{"type":"array","items":{"type":"integer"}},"name":{"type":"string"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
    types.Tool(name="totvs_search_legal_customers", description="Busca clientes pessoa jurídica por CNPJ ou razão social. Para buscar cliente por CPF ou CNPJ sem saber se é PF ou PJ, use totvs_search_customer_by_document (detecta automaticamente pelo tamanho do documento). Use fields=['code','name','cpfCnpj'] para respostas pequenas.",
        inputSchema={"type":"object","properties":{"cnpjList":{"type":"array","items":{"type":"string"}},"customerCodeList":{"type":"array","items":{"type":"integer"}},"corporateName":{"type":"string"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
    types.Tool(name="totvs_get_customer_bonus_balance", description="Saldo de bônus/desconto de um cliente.",
        inputSchema={"type":"object","properties":{"customerCode":{"type":"integer"},"cpfCnpj":{"type":"string"}}}),
    types.Tool(name="totvs_get_person_statistics", description="Estatísticas do cliente: total comprado, ticket médio, frequência.",
        inputSchema={"type":"object","properties":{"customerCode":{"type":"integer"},"branchCode":{"type":"integer","description":"Código da filial"}},"required":["customerCode"]}),
    types.Tool(name="totvs_create_or_update_individual_customer", description="⚠️ ESCRITA — Cria ou atualiza cliente PF no TOTVS.",
        inputSchema={"type":"object","properties":{"cpf":{"type":"string"},"name":{"type":"string"},"email":{"type":"string"},"phone":{"type":"string"},"birthDate":{"type":"string"},"branchCode":{"type":"integer","description":"Código da filial"}},"required":["cpf","name"]}),
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
    types.Tool(name="totvs_get_email_types", description="Tipos de e-mail disponíveis para cadastro de pessoa.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_get_phone_types", description="Tipos de telefone disponíveis para cadastro de pessoa.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_consume_bonus", description="⚠️ Consome bônus/desconto de cliente.",
        inputSchema={"type":"object","properties":{
            "customerCode":{"type":"integer"},"branchCode":{"type":"integer"},
            "value":{"type":"number"}
        },"required":["customerCode","branchCode","value"]}),
    types.Tool(name="totvs_create_person_message", description="⚠️ Inclui mensagem/observação para uma pessoa.",
        inputSchema={"type":"object","properties":{
            "personCode":{"type":"integer"},"message":{"type":"string"}
        },"required":["personCode","message"]}),

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
            "startChangeDate":{"type":"string","description":"Data de alteração inicial (ISO 8601)"},
            "endChangeDate":{"type":"string","description":"Data de alteração final"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":500},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens."},
        }}),
    types.Tool(name="totvs_search_receivable_documents", description="Busca documentos a receber (faturas, duplicatas). Retorna items[] com: branchCode, customerCode, customerName, receivableCode, installmentCode, issueDate, expiredDate, paymentDate, value, balanceValue, status (Open/Paid/Overdue), chargeType, billingType. Filtros úteis: startExpiredDate + endExpiredDate, statusList, customerCodeList, hasOpenInvoices=true. Para detectar clientes inadimplentes filtre por statusList=['Open'] + endExpiredDate < hoje. Suporta expand para cheque, fatura, comissionados e valores calculados.",
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
            "startChangeDate":{"type":"string","description":"Data alteração inicial"},
            "endChangeDate":{"type":"string","description":"Data alteração final"},
            "statusList":{"type":"array","items":{"type":"integer"},"description":"Status: 1=Normal, 2=Devolvido, 3=Cancelado, 4=Quebrado"},
            "documentTypeList":{"type":"array","items":{"type":"integer"},"description":"Tipos de documento"},
            "hasOpenInvoices":{"type":"boolean","description":"Apenas faturas em aberto"},
            "receivableCodeList":{"type":"array","items":{"type":"number"},"description":"Códigos das faturas"},
            "commissionedCode":{"type":"integer","description":"Código do comissionado"},
            "commissionedCpfCnpj":{"type":"string","description":"CPF/CNPJ do comissionado"},
            "expand":{"type":"string","description":"Expansão: check, invoice, commissioneds, calculateValue"},
            "order":{"type":"string","description":"Ordenação: branchCode, customerCode, receivableCode, installmentCode, maxChangeFilterDate"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Ex: ['customerName','balanceValue','expiredDate']."},
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
            "operationType":{"type":"string","description":"E=Entrada, S=Saída"},
            "origin":{"type":"string"},
            "invoiceStatusList":{"type":"array","items":{"type":"string"}},
            "personCodeList":{"type":"array","items":{"type":"integer"}},
            "operationCodeList":{"type":"array","items":{"type":"integer"}},
            "documentTypeCodeList":{"type":"array","items":{"type":"integer"}},
            "personCpfCnpjList":{"type":"array","items":{"type":"string"}},
            "startIssueDate":{"type":"string","description":"ISO 8601"},
            "endIssueDate":{"type":"string"},
            "serialCodeList":{"type":"array","items":{"type":"string"}},
            "eletronicInvoiceStatusList":{"type":"array","items":{"type":"string"}},
            "startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},
            "amountLastDays":{"type":"integer"},
            "transactionBranchCode":{"type":"integer"},"transactionCode":{"type":"integer"},"transactionDate":{"type":"string"},
            "expand":{"type":"array","items":{"type":"string"},"description":"invoiceItems, payments, observations"},
            "order":{"type":"array","items":{"type":"object"}},
            "page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},
            "fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Ex: ['accessKey','invoiceCode','value']."},
        },"required":["branchCodeList"]}),
    types.Tool(name="totvs_get_nfe_xml", description="XML completo de uma NF-e pela chave de acesso (44 dígitos).",
        inputSchema={"type":"object","properties":{"accessKey":{"type":"string"}},"required":["accessKey"]}),
    types.Tool(name="totvs_get_invoice_item_detail", description="Detalhe de itens de NF-e (preço, desconto, impostos).",
        inputSchema={"type":"object","properties":{
            "BranchCode":{"type":"integer"},"InvoiceCode":{"type":"integer"},
            "SerialCode":{"type":"string"},"InvoiceSequence":{"type":"integer"},
            "OperationType":{"type":"string","description":"E=Entrada, S=Saída"}
        }}),
    types.Tool(name="totvs_get_danfe", description="DANFE em base64 (PDF) de uma NF-e a partir do XML.",
        inputSchema={"type":"object","properties":{
            "mainInvoiceXml":{"type":"string","description":"Conteúdo XML da NF-e"},
            "nfeDocumentType":{"type":"string","description":"Tipo de documento NF-e"}
        },"required":["mainInvoiceXml"]}),
    types.Tool(name="totvs_search_invoice_products", description="Produtos de NF-e por período, referência ou operação.",
        inputSchema={"type":"object","properties":{
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Lista de filiais (obrigatório)"},
            "ProductCodeList":{"type":"array","items":{"type":"integer"}},
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
            "acessKeyList":{"type":"array","items":{"type":"string"}},
            "order":{"type":"array","items":{"type":"object"}},
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

    # ── ACCOUNT PAYABLE ───────────────────────────────────────────────────────
    types.Tool(name="totvs_search_payable_duplicates", description="Consulta duplicatas de contas a pagar com filtros flexíveis de vencimento, emissão, fornecedor e status.",
        inputSchema={"type":"object","properties":{
            "branchCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos das filiais (obrigatório)"},
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
            "status":{"type":"string","description":"Status: Grouped, Canceled, Retorned, CommissionSettled, Normal, Broken"},
            "documentTypeList":{"type":"array","items":{"type":"integer"},"description":"Tipos de documento (1=Duplicata, 2=NotaFiscal, 7=Fatura...)"},
            "order":{"type":"string","description":"Ordenação: productCode, maxChangeFilterDate"},
            "page":{"type":"integer","default":1},
            "pageSize":{"type":"integer","default":100},
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

    # ── PURCHASE ORDER ────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_purchase_orders", description="Pedidos de compra por filtro. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos dos pedidos de compra"},"supplierCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos dos fornecedores"},"operationCodeList":{"type":"array","items":{"type":"integer"}},"startDate":{"type":"string"},"endDate":{"type":"string"},"statusList":{"type":"array","items":{"type":"string"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
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
    types.Tool(name="totvs_search_sellers", description="Lista vendedores e empresas vinculadas. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"sellerCodeList":{"type":"array","items":{"type":"integer"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
    types.Tool(name="totvs_get_seller_operational_area", description="Regiões de atuação de vendedores.",
        inputSchema={"type":"object","properties":{
            "sellerCode":{"type":"integer"},"branchCode":{"type":"integer"}
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
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"value":{"type":"number"},"expirationDate":{"type":"string"},"customerCode":{"type":"integer"}},"required":["branchCode","value"]}),

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
    types.Tool(name="totvs_search_production_orders", description="Ordens de produção por filtro. Use fields para reduzir tokens.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"},"statusList":{"type":"array","items":{"type":"string"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100},"fields":{"type":"array","items":{"type":"string"},"description":"Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."}}}),
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

    # ── CONTEXT ───────────────────────────────────────────────────────────────
    types.Tool(
        name="totvs_get_context",
        description=(
            "Retorna dados de referência da empresa: filiais, tabelas de preço/custo "
            "EXISTENTES, operações, condições de pagamento. "
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
]


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
    "totvs_search_individual_customers":         ("person", "search_individuals"),
    "totvs_search_legal_customers":              ("person", "search_legal_entities"),
    "totvs_get_customer_bonus_balance":          ("person", "list_bonus_balance"),
    "totvs_get_person_statistics":               ("person", "get_person_statistics"),
    "totvs_create_or_update_individual_customer":("person", "create_or_update_individual_customer"),
    "totvs_create_or_update_legal_customer":     ("person", "create_or_update_legal_customer"),
    "totvs_get_branches_list":                   ("person", "get_branches_list"),
    "totvs_search_representatives":              ("person", "search_representatives"),
    "totvs_get_person_classifications":          ("person", "get_classifications"),
    "totvs_get_email_types":                     ("person", "get_email_types"),
    "totvs_get_phone_types":                     ("person", "get_phone_types"),
    "totvs_consume_bonus":                       ("person", "consume_bonus"),
    "totvs_create_person_message":               ("person", "create_message"),
    "totvs_search_customer_financial_balance":   ("accounts_receivable", "search_customer_financial_balance"),
    "totvs_search_receivable_documents":         ("accounts_receivable", "search_documents"),
    "totvs_get_bank_slip":                       ("accounts_receivable", "get_bank_slip"),
    "totvs_get_payment_link":                    ("accounts_receivable", "get_payment_link"),
    "totvs_get_gift_check_balances":             ("accounts_receivable", "get_gift_check_balances"),
    "totvs_change_charge_type":                  ("accounts_receivable", "change_charge_type"),
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
    "totvs_get_classifications":                 ("general", "get_classifications"),
    "totvs_create_devolution":                   ("general", "create_devolution"),
    "totvs_create_transaction":                  ("general", "create_transaction"),
    "totvs_create_product_count":                ("general", "create_product_count"),
    "totvs_search_payable_duplicates":           ("account_payable", "search_duplicates"),
    "totvs_search_commissions_paid":             ("account_payable", "search_commissions_paid"),
    "totvs_create_duplicate":                    ("account_payable", "create_duplicate"),
    "totvs_search_purchase_orders":              ("purchase_order", "search_purchase_orders"),
    "totvs_create_purchase_order":               ("purchase_order", "create_purchase_order"),
    "totvs_cancel_purchase_order":               ("purchase_order", "cancel_purchase_order"),
    "totvs_change_purchase_order_status":        ("purchase_order", "change_purchase_order_status"),
    "totvs_search_sellers":                      ("seller", "search_sellers"),
    "totvs_get_seller_operational_area":         ("seller", "get_operational_area"),
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
}


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return TOOLS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    logger.info(f"Tool: {name}")

    # ── context tool ──────────────────────────────────────────────────────────
    if name == "totvs_get_context":
        if arguments.get("verbose"):
            result = context_cache.get_full_context()
        else:
            result = context_cache.get_slim_context()
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

    route = ROUTING.get(name)
    if not route:
        return [types.TextContent(type="text", text=json.dumps({"error": f"Tool '{name}' não encontrada."}))]

    module_key, method_name = route
    module = get_modules().get(module_key)

    try:
        result = await getattr(module, method_name)(arguments)
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    except Exception as exc:
        logger.exception(f"Erro: {name}")
        return [types.TextContent(type="text", text=json.dumps({"error": str(exc), "tool": name}, ensure_ascii=False))]


async def main() -> None:
    logger.info(f"TOTVS Moda MCP Server v3.1 — {len(TOOLS)} tools | {len(get_modules())} módulos")
    try:
        await context_cache.load_context(get_client())
    except Exception as e:
        logger.warning(f"Falha ao carregar contexto na inicialização: {e}")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            InitializationOptions(
                server_name="totvs-moda-mcp",
                server_version="3.1.0",
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
