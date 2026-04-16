"""
TOTVS Moda MCP Server v2.0
===========================
MCP server completo para API V2 do TOTVS Moda.
16 módulos | 60+ tools | OAuth2 ROPC

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
from tools.analytics import AnalyticsTools
from tools.general import GeneralTools
from tools.account_payable import AccountPayableTools
from tools.purchase_order import PurchaseOrderTools
from tools.seller import SellerTools
from tools.voucher import VoucherTools
from tools.other_modules import ManagementTools, GlobalTools, ProductionOrderTools

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
            "analytics":           AnalyticsTools(c),
            "general":             GeneralTools(c),
            "account_payable":     AccountPayableTools(c),
            "purchase_order":      PurchaseOrderTools(c),
            "seller":              SellerTools(c),
            "voucher":             VoucherTools(c),
            "management":          ManagementTools(c),
            "global":              GlobalTools(c),
            "production_order":    ProductionOrderTools(c),
        }
    return _modules


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

TOOLS: list[types.Tool] = [

    # ── SALES ORDER ──────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_orders", description="Busca pedidos de venda com filtros flexíveis. Suporta filtro por data, status, cliente, CPF, código de integração Shopify (SHP-XXXX), e expand para itens/NF-e/endereço/observações.",
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
        }}),
    types.Tool(name="totvs_get_order_invoices", description="NF-e vinculadas a um pedido de venda.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"}},"required":["branchCode","orderCode"]}),
    types.Tool(name="totvs_get_pending_items", description="Itens pendentes de faturamento em um pedido.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"}},"required":["branchCode","orderCode"]}),
    types.Tool(name="totvs_get_billing_suggestions", description="Sugestões de faturamento do TOTVS.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"}},"required":["branchCode"]}),
    types.Tool(name="totvs_cancel_order", description="⚠️ ESCRITA — Cancela pedido de venda (irreversível).",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"},"cancellationReason":{"type":"string"}},"required":["branchCode","orderCode"]}),
    types.Tool(name="totvs_change_order_status", description="⚠️ ESCRITA — Altera situação do pedido.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"},"status":{"type":"string","enum":["Digitado","Confirmado","Cancelado","Bloqueado","Faturado","EmFaturamento","Pendente","Encerrado"]}},"required":["branchCode","orderCode","status"]}),
    types.Tool(name="totvs_update_order_items_price", description="⚠️ ESCRITA — Altera preço de itens do pedido.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"orderCode":{"type":"integer"},"items":{"type":"array","items":{"type":"object","properties":{"itemSequential":{"type":"integer"},"price":{"type":"number"}},"required":["itemSequential","price"]}}},"required":["branchCode","orderCode","items"]}),

    # ── PRODUCT ──────────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_products", description="Busca produtos por filtro. Retorna referência, grade, cor, coleção, estampa.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCodeList":{"type":"array","items":{"type":"integer"}},"referenceCodeList":{"type":"array","items":{"type":"string"}},"categoryCodeList":{"type":"array","items":{"type":"integer"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}}}),
    types.Tool(name="totvs_get_product", description="Dados completos de um produto/pack pelo código.",
        inputSchema={"type":"object","properties":{"code":{"type":"integer"},"branchCode":{"type":"integer","description":"Código da filial"}},"required":["code"]}),
    types.Tool(name="totvs_search_product_balances", description="Saldos de estoque por produto. Retorna disponível, reservado, total por filial/depósito.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCodeList":{"type":"array","items":{"type":"integer"}},"referenceCodeList":{"type":"array","items":{"type":"string"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}}}),
    types.Tool(name="totvs_search_product_prices", description="Preços de produtos por filtro, opcionalmente por tabela de preço.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCodeList":{"type":"array","items":{"type":"integer"}},"referenceCodeList":{"type":"array","items":{"type":"string"}},"priceTableCodeList":{"type":"array","items":{"type":"integer"}},"priceCodeList":{"type":"array","items":{"type":"integer"},"description":"Códigos numéricos de tipo de preço (ex: [1])"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}}}),
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
        },"required":["priceTableCode"]}),
    types.Tool(name="totvs_search_product_references", description="Referências de produtos com grade, cor e composição.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"referenceCodeList":{"type":"array","items":{"type":"string"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}}}),
    types.Tool(name="totvs_get_product_grid", description="Grades (tamanhos) disponíveis no TOTVS.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"}}}),
    types.Tool(name="totvs_search_product_colors", description="Cores de produtos.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"colorCodeList":{"type":"array","items":{"type":"integer"}}}}),
    types.Tool(name="totvs_search_product_batch", description="Lotes de produto.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCodeList":{"type":"array","items":{"type":"integer"}}}}),
    types.Tool(name="totvs_get_kardex_movement", description="Movimentação kardex (entradas/saídas) de produto.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCode":{"type":"integer"},"startDate":{"type":"string"},"endDate":{"type":"string"}},"required":["branchCode","productCode"]}),
    types.Tool(name="totvs_search_product_compositions", description="Composições de produto (ficha técnica).",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCodeList":{"type":"array","items":{"type":"integer"}}}}),
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
    types.Tool(name="totvs_update_product_price", description="⚠️ ESCRITA — Altera preço ou custo de produto. Use totvs_get_context para obter priceTypes/costTypes com os códigos válidos. valueCode = priceCode; valueType = tipo numérico do preço/custo.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCode":{"type":"integer","description":"Código do produto"},"valueCode":{"type":"integer","description":"Código do tipo de preço ou custo (priceCode/costCode do contexto)"},"valueType":{"type":"integer","description":"Tipo do valor conforme enum da API (obtido via priceTypes/costTypes no contexto)"},"value":{"type":"number","description":"Novo valor"}},"required":["branchCode","productCode","valueCode","value"]}),
    types.Tool(name="totvs_update_promotion_price", description="⚠️ ESCRITA — Altera preço de promoção de produto.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"productCode":{"type":"integer"},"promotionPrice":{"type":"number"},"startDate":{"type":"string"},"endDate":{"type":"string"}},"required":["branchCode","productCode","promotionPrice"]}),

    # ── PERSON ───────────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_individual_customers", description="Busca clientes pessoa física por CPF, nome ou código.",
        inputSchema={"type":"object","properties":{"cpfList":{"type":"array","items":{"type":"string"}},"customerCodeList":{"type":"array","items":{"type":"integer"}},"name":{"type":"string"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}}}),
    types.Tool(name="totvs_search_legal_customers", description="Busca clientes pessoa jurídica por CNPJ ou razão social.",
        inputSchema={"type":"object","properties":{"cnpjList":{"type":"array","items":{"type":"string"}},"customerCodeList":{"type":"array","items":{"type":"integer"}},"corporateName":{"type":"string"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}}}),
    types.Tool(name="totvs_get_customer_bonus_balance", description="Saldo de bônus/desconto de um cliente.",
        inputSchema={"type":"object","properties":{"customerCode":{"type":"integer"},"cpfCnpj":{"type":"string"}}}),
    types.Tool(name="totvs_get_person_statistics", description="Estatísticas do cliente: total comprado, ticket médio, frequência.",
        inputSchema={"type":"object","properties":{"customerCode":{"type":"integer"},"branchCode":{"type":"integer","description":"Código da filial"}},"required":["customerCode"]}),
    types.Tool(name="totvs_create_or_update_individual_customer", description="⚠️ ESCRITA — Cria ou atualiza cliente PF no TOTVS.",
        inputSchema={"type":"object","properties":{"cpf":{"type":"string"},"name":{"type":"string"},"email":{"type":"string"},"phone":{"type":"string"},"birthDate":{"type":"string"},"branchCode":{"type":"integer","description":"Código da filial"}},"required":["cpf","name"]}),

    # ── ACCOUNTS RECEIVABLE ───────────────────────────────────────────────────
    types.Tool(name="totvs_search_customer_financial_balance", description="Limite financeiro e saldo do cliente.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"customerCode":{"type":"integer"},"cpfCnpj":{"type":"string"}},"required":["branchCode"]}),
    types.Tool(name="totvs_search_receivable_documents", description="Documentos de contas a receber (faturas, duplicatas) com filtros de vencimento e status.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"customerCode":{"type":"integer"},"cpfCnpj":{"type":"string"},"startDueDate":{"type":"string"},"endDueDate":{"type":"string"},"status":{"type":"string"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}},"required":["branchCode"]}),
    types.Tool(name="totvs_get_bank_slip", description="Base64 do boleto bancário de uma fatura.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"invoiceCode":{"type":"integer"}},"required":["branchCode","invoiceCode"]}),
    types.Tool(name="totvs_get_payment_link", description="Link de pagamento PIX de uma fatura.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"invoiceCode":{"type":"integer"}},"required":["branchCode","invoiceCode"]}),

    # ── FISCAL ───────────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_fiscal_invoices", description="Busca NF-e por período, cliente ou chave de acesso.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startIssueDate":{"type":"string"},"endIssueDate":{"type":"string"},"customerCpfCnpj":{"type":"string"},"accessKeyList":{"type":"array","items":{"type":"string"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}},"required":["branchCode"]}),
    types.Tool(name="totvs_get_nfe_xml", description="XML completo de uma NF-e pela chave de acesso (44 dígitos).",
        inputSchema={"type":"object","properties":{"accessKey":{"type":"string"}},"required":["accessKey"]}),
    types.Tool(name="totvs_get_danfe", description="DANFE em base64 (PDF) de uma NF-e.",
        inputSchema={"type":"object","properties":{"xmlContent":{"type":"string"},"accessKey":{"type":"string"}}}),
    types.Tool(name="totvs_search_invoice_products", description="Produtos de NF-e por período.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startIssueDate":{"type":"string"},"endIssueDate":{"type":"string"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}},"required":["branchCode"]}),
    types.Tool(name="totvs_get_cost_center", description="Centros de custo disponíveis.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"}}}),

    # ── ANALYTICS ────────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_fiscal_movement", description="Movimentação fiscal geral (vendas, devoluções, NF-e) por período.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}}}),
    types.Tool(name="totvs_search_product_fiscal_movement", description="Produtos na movimentação fiscal. Análise de vendas por produto/período.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}}}),
    types.Tool(name="totvs_search_best_selling_products", description="Ranking dos produtos mais vendidos no e-commerce.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"},"limit":{"type":"integer"}}}),
    types.Tool(name="totvs_search_sales_by_hour", description="Vendas por hora do dia. Identifica pico de vendas.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"}}}),
    types.Tool(name="totvs_search_sales_by_weekday", description="Vendas por dia da semana no período.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"}}}),
    types.Tool(name="totvs_search_total_receivable", description="Totais de contas a receber do painel financeiro.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"}}}),
    types.Tool(name="totvs_search_total_payable", description="Totais de contas a pagar do painel financeiro.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"}}}),
    types.Tool(name="totvs_search_top_customers", description="Top 5 clientes que mais compraram no período.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"}}}),
    types.Tool(name="totvs_search_top_debtors", description="Top 5 clientes com maior atraso.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"}},"required":["branchCode"]}),
    types.Tool(name="totvs_search_financial_income_statement", description="DRF — Demonstrativo de Resultado Financeiro.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"}}}),

    # ── GENERAL ──────────────────────────────────────────────────────────────
    types.Tool(name="totvs_get_payment_conditions", description="Condições de pagamento disponíveis.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"}}}),
    types.Tool(name="totvs_get_operations", description="Operações disponíveis (entrada/saída). Requer ao menos um filtro.",
        inputSchema={"type":"object","properties":{"operationCodeList":{"type":"array","items":{"type":"integer"}},"operationTypeList":{"type":"array","items":{"type":"string"},"description":"E - Entrada, S - Saída"},"startChangeDate":{"type":"string"},"endChangeDate":{"type":"string"},"isInactive":{"type":"boolean","description":"true=inativas, false=ativas"},"pageSize":{"type":"integer","default":1000}}}),
    types.Tool(name="totvs_simulate_payment_plan", description="Simula cálculo de plano de pagamento.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"paymentPlanCode":{"type":"integer"},"totalAmount":{"type":"number"}},"required":["branchCode","paymentPlanCode","totalAmount"]}),
    types.Tool(name="totvs_search_devolutions", description="Consulta dados de devolução por código.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"devolutionCode":{"type":"integer"},"expand":{"type":"string","description":"classifications, items"}},"required":["branchCode","devolutionCode"]}),

    # ── ACCOUNT PAYABLE ───────────────────────────────────────────────────────
    types.Tool(name="totvs_search_payable_duplicates", description="Duplicatas de contas a pagar.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"supplierCode":{"type":"integer"},"startDueDate":{"type":"string"},"endDueDate":{"type":"string"},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}},"required":["branchCode"]}),
    types.Tool(name="totvs_search_commissions_paid", description="Fechamento de comissão por período e representante.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"},"representativeCode":{"type":"integer"}},"required":["branchCode"]}),

    # ── PURCHASE ORDER ────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_purchase_orders", description="Pedidos de compra por filtro.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"},"statusList":{"type":"array","items":{"type":"string"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}}}),

    # ── SELLER ────────────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_sellers", description="Lista vendedores e empresas vinculadas.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"sellerCodeList":{"type":"array","items":{"type":"integer"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}}}),

    # ── VOUCHER ───────────────────────────────────────────────────────────────
    types.Tool(name="totvs_search_voucher", description="Consulta vouchers/cupons.",
        inputSchema={"type":"object","properties":{"voucherCode":{"type":"string"},"customerCode":{"type":"integer"},"branchCode":{"type":"integer","description":"Código da filial"}}}),
    types.Tool(name="totvs_create_voucher", description="⚠️ ESCRITA — Cria voucher/cupom.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"value":{"type":"number"},"expirationDate":{"type":"string"},"customerCode":{"type":"integer"}},"required":["branchCode","value"]}),

    # ── MANAGEMENT ────────────────────────────────────────────────────────────
    types.Tool(name="totvs_get_users", description="Lista usuários do TOTVS Moda.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_get_global_parameters", description="Parâmetros corporativos do TOTVS.",
        inputSchema={"type":"object","properties":{}}),
    types.Tool(name="totvs_get_branch_parameters", description="Parâmetros por empresa/filial.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"}}}),

    # ── GLOBAL / LOCATION ─────────────────────────────────────────────────────
    types.Tool(name="totvs_get_cep", description="Endereço completo pelo CEP.",
        inputSchema={"type":"object","properties":{"cep":{"type":"string","description":"Somente dígitos ex: 86020040"}},"required":["cep"]}),

    # ── PRODUCTION ORDER ──────────────────────────────────────────────────────
    types.Tool(name="totvs_search_production_orders", description="Ordens de produção por filtro.",
        inputSchema={"type":"object","properties":{"branchCode":{"type":"integer","description":"Código da filial"},"startDate":{"type":"string"},"endDate":{"type":"string"},"statusList":{"type":"array","items":{"type":"string"}},"page":{"type":"integer","default":1},"pageSize":{"type":"integer","default":100}}}),

    # ── CONTEXT ───────────────────────────────────────────────────────────────
    types.Tool(name="totvs_get_context", description="Retorna dados de referência carregados na inicialização: filiais, operações, condições de pagamento, tabelas de preço, classificações, categorias, grades e unidades de medida. Use antes de criar/alterar registros para obter os códigos corretos.",
        inputSchema={"type":"object","properties":{}}),
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
    "totvs_search_products":                     ("product", "search_products"),
    "totvs_get_product":                         ("product", "get_product"),
    "totvs_search_product_balances":             ("product", "search_balances"),
    "totvs_search_product_prices":               ("product", "search_prices"),
    "totvs_search_price_tables":                 ("product", "search_price_tables"),
    "totvs_get_price_tables_headers":            ("product", "get_price_tables_headers"),
    "totvs_search_product_references":           ("product", "search_references"),
    "totvs_get_product_grid":                    ("product", "get_grid"),
    "totvs_search_product_colors":               ("product", "search_colors"),
    "totvs_search_product_batch":                ("product", "search_batch"),
    "totvs_get_kardex_movement":                 ("product", "get_kardex_movement"),
    "totvs_search_product_compositions":         ("product", "search_compositions"),
    "totvs_create_product_classification":        ("product", "create_classification_relationship"),
    "totvs_create_product_value":                 ("product", "create_product_value"),
    "totvs_update_product_price":                ("product", "update_product_price"),
    "totvs_update_promotion_price":              ("product", "update_promotion_price"),
    "totvs_search_individual_customers":         ("person", "search_individuals"),
    "totvs_search_legal_customers":              ("person", "search_legal_entities"),
    "totvs_get_customer_bonus_balance":          ("person", "list_bonus_balance"),
    "totvs_get_person_statistics":               ("person", "get_person_statistics"),
    "totvs_create_or_update_individual_customer":("person", "create_or_update_individual_customer"),
    "totvs_search_customer_financial_balance":   ("accounts_receivable", "search_customer_financial_balance"),
    "totvs_search_receivable_documents":         ("accounts_receivable", "search_documents"),
    "totvs_get_bank_slip":                       ("accounts_receivable", "get_bank_slip"),
    "totvs_get_payment_link":                    ("accounts_receivable", "get_payment_link"),
    "totvs_search_fiscal_invoices":              ("fiscal", "search_invoices"),
    "totvs_get_nfe_xml":                         ("fiscal", "get_xml_content"),
    "totvs_get_danfe":                           ("fiscal", "get_danfe"),
    "totvs_search_invoice_products":             ("fiscal", "search_invoice_products"),
    "totvs_get_cost_center":                     ("fiscal", "get_cost_center"),
    "totvs_search_fiscal_movement":              ("analytics", "search_fiscal_movement"),
    "totvs_search_product_fiscal_movement":      ("analytics", "search_product_fiscal_movement"),
    "totvs_search_best_selling_products":        ("analytics", "search_best_selling_products"),
    "totvs_search_sales_by_hour":                ("analytics", "search_sales_quantity_hour"),
    "totvs_search_sales_by_weekday":             ("analytics", "search_sales_quantity_weekday"),
    "totvs_search_total_receivable":             ("analytics", "search_total_receivable"),
    "totvs_search_total_payable":                ("analytics", "search_total_payable"),
    "totvs_search_top_customers":                ("analytics", "search_ranking_customer_biggers"),
    "totvs_search_top_debtors":                  ("analytics", "search_ranking_customer_debtors"),
    "totvs_search_financial_income_statement":   ("analytics", "search_financial_income_statement"),
    "totvs_get_payment_conditions":              ("general", "get_payment_conditions"),
    "totvs_get_operations":                      ("general", "get_operations"),
    "totvs_simulate_payment_plan":               ("general", "simulate_payment_plan"),
    "totvs_search_devolutions":                  ("general", "search_devolutions"),
    "totvs_search_payable_duplicates":           ("account_payable", "search_duplicates"),
    "totvs_search_commissions_paid":             ("account_payable", "search_commissions_paid"),
    "totvs_search_purchase_orders":              ("purchase_order", "search_purchase_orders"),
    "totvs_search_sellers":                      ("seller", "search_sellers"),
    "totvs_search_voucher":                      ("voucher", "search_voucher"),
    "totvs_create_voucher":                      ("voucher", "create_voucher"),
    "totvs_get_users":                           ("management", "get_users"),
    "totvs_get_global_parameters":               ("management", "get_global_parameters"),
    "totvs_get_branch_parameters":               ("management", "get_branch_parameters"),
    "totvs_get_cep":                             ("global", "get_cep"),
    "totvs_search_production_orders":            ("production_order", "search_production_orders"),
    "totvs_get_context":                         None,  # handled inline
}


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return TOOLS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    logger.info(f"Tool: {name}")

    # ── context tool ──────────────────────────────────────────────────────────
    if name == "totvs_get_context":
        if not context_cache.is_loaded():
            await context_cache.load(get_client())
        return [types.TextContent(type="text", text=json.dumps(context_cache.get(), ensure_ascii=False, indent=2))]

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
    logger.info(f"TOTVS Moda MCP Server v2.0 — {len(TOOLS)} tools | {len(get_modules())} módulos")
    try:
        await context_cache.load(get_client())
    except Exception as e:
        logger.warning(f"Falha ao carregar contexto na inicialização: {e}")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            InitializationOptions(
                server_name="totvs-moda-mcp",
                server_version="2.0.0",
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
