# TOTVS Moda MCP Server

> MCP (Model Context Protocol) server para integração com a **API V2 do TOTVS Moda**.  
> Permite que Claude e outros clientes MCP consultem e operem pedidos, produtos, clientes, fiscal e financeiro do TOTVS Moda por linguagem natural.

---

## Por que isso existe?

O TOTVS Moda é amplamente usado no varejo de moda brasileiro, mas não possui um MCP server oficial.  
Este projeto preenche essa lacuna, permitindo que times usem IA diretamente sobre os dados operacionais do TOTVS — consultas, alertas, automações — sem precisar acessar o sistema manualmente.

---

## Tools disponíveis

### Pedidos de Venda
| Tool | Método | Endpoint | Descrição |
|------|--------|----------|-----------|
| `totvs_search_orders` | POST | `/sales-order/v2/orders/search` | Busca pedidos com filtros flexíveis (data, status, cliente, integração Shopify...) |
| `totvs_get_order_invoices` | GET | `/sales-order/v2/invoices` | Notas fiscais vinculadas a um pedido |
| `totvs_get_pending_items` | GET | `/sales-order/v2/pending-items` | Itens pendentes de faturamento |
| `totvs_get_billing_suggestions` | GET | `/sales-order/v2/billing-suggestions` | Sugestões de faturamento |
| `totvs_cancel_order` | POST | `/sales-order/v2/orders/cancel` | ⚠️ Cancela um pedido |
| `totvs_change_order_status` | POST | `/sales-order/v2/orders/change-status` | ⚠️ Altera situação do pedido |
| `totvs_update_order_items_price` | POST | `/sales-order/v2/price-items` | ⚠️ Atualiza preços de itens do pedido |

### Produtos
| Tool | Método | Endpoint | Descrição |
|------|--------|----------|-----------|
| `totvs_search_products` | POST | `/product/v2/products/search` | Busca produtos por filtro (referência, categoria, código) |
| `totvs_get_product` | GET | `/product/v2/products/{code}/{branch}` | Dados completos de um produto pelo código |
| `totvs_get_product_grid` | GET | `/product/v2/grid` | Grade completa (cores e tamanhos) |
| `totvs_search_product_references` | POST | `/product/v2/references/search` | Referências de produtos |
| `totvs_search_product_colors` | POST | `/product/v2/colors/search` | Cores disponíveis |
| `totvs_search_product_balances` | POST | `/product/v2/balances/search` | Saldo em estoque por filial |
| `totvs_search_product_prices` | POST | `/product/v2/prices/search` | Preços nas tabelas |
| `totvs_search_product_compositions` | POST | `/product/v2/compositions` | Composição dos produtos |
| `totvs_search_product_batch` | POST | `/product/v2/batch/search` | Lotes de produtos |
| `totvs_search_product_fiscal_movement` | POST | `/analytics/v2/product-fiscal-movement/search` | Movimentação fiscal de produtos |
| `totvs_search_price_tables` | POST | `/product/v2/price-tables/search` | Tabelas de preço disponíveis |
| `totvs_get_kardex_movement` | GET | `/product/v2/kardex-movement` | Movimentação kardex |
| `totvs_update_product_price` | POST | `/product/v2/values/update` | ⚠️ Atualiza preço de produto |
| `totvs_update_promotion_price` | POST | `/product/v2/promotion-values/update` | ⚠️ Atualiza preço de promoção |

### Clientes
| Tool | Método | Endpoint | Descrição |
|------|--------|----------|-----------|
| `totvs_search_individual_customers` | POST | `/person/v2/individuals/search` | Busca clientes pessoa física |
| `totvs_search_legal_customers` | POST | `/person/v2/legal-entities/search` | Busca clientes pessoa jurídica |
| `totvs_get_person_statistics` | GET | `/person/v2/person-statistics` | Estatísticas de um cliente |
| `totvs_search_top_customers` | POST | `/financial/v2/ranking-customer-biggers/search` | Melhores clientes por período |
| `totvs_search_top_debtors` | POST | `/financial/v2/ranking-customer-debtors/search` | Maiores devedores |
| `totvs_get_customer_bonus_balance` | POST | `/person/v2/list-balance-bonus` | Saldo de bônus do cliente |
| `totvs_create_or_update_individual_customer` | POST | `/person/v2/individual-customers` | ⚠️ Cria ou atualiza cliente PF |

### Fiscal
| Tool | Método | Endpoint | Descrição |
|------|--------|----------|-----------|
| `totvs_search_fiscal_invoices` | POST | `/fiscal/v2/invoices/search` | Notas fiscais emitidas |
| `totvs_search_fiscal_movement` | POST | `/analytics/v2/fiscal-movement/search` | Movimentação fiscal |
| `totvs_search_invoice_products` | POST | `/fiscal/v2/invoice-products/search` | Produtos de uma nota fiscal |
| `totvs_get_danfe` | POST | `/fiscal/v2/danfe-search` | DANFE em PDF |
| `totvs_get_nfe_xml` | GET | `/fiscal/v2/xml-contents/{access_key}` | XML da NF-e |
| `totvs_get_cost_center` | GET | `/fiscal/v2/cost-center` | Centros de custo |

### Financeiro
| Tool | Método | Endpoint | Descrição |
|------|--------|----------|-----------|
| `totvs_search_receivable_documents` | POST | `/accounts-receivable/v2/documents/search` | Títulos a receber |
| `totvs_search_payable_duplicates` | POST | `/accounts-payable/v2/duplicates/search` | Duplicatas a pagar |
| `totvs_search_total_receivable` | POST | `/financial/v2/total-receivable/search` | Total a receber |
| `totvs_search_total_payable` | POST | `/financial/v2/total-payable/search` | Total a pagar |
| `totvs_search_customer_financial_balance` | POST | `/accounts-receivable/v2/customer-financial-balance/search` | Posição financeira do cliente |
| `totvs_search_financial_income_statement` | POST | `/financial/v2/financial-income-statement/search` | DRE financeiro |
| `totvs_get_bank_slip` | POST | `/accounts-receivable/v2/bank-slip` | Boleto bancário |
| `totvs_get_payment_link` | POST | `/accounts-receivable/v2/payment-link` | Link de pagamento |
| `totvs_simulate_payment_plan` | POST | `/general/v2/payment-plan-simulate` | Simula plano de pagamento |
| `totvs_get_payment_conditions` | GET | `/general/v2/payment-conditions` | Condições de pagamento disponíveis |
| `totvs_create_voucher` | POST | `/voucher/v2/create` | ⚠️ Cria voucher |
| `totvs_search_voucher` | GET | `/voucher/v2/search` | Busca vouchers |

### Analytics
| Tool | Método | Endpoint | Descrição |
|------|--------|----------|-----------|
| `totvs_search_best_selling_products` | POST | `/ecommerce/v2/best-selling-products/search` | Produtos mais vendidos |
| `totvs_search_sales_by_hour` | POST | `/ecommerce/v2/sales-quantity-hour/search` | Vendas por hora |
| `totvs_search_sales_by_weekday` | POST | `/ecommerce/v2/sales-quantity-weekday/search` | Vendas por dia da semana |
| `totvs_search_commissions_paid` | POST | `/accounts-payable/v2/comissions-paid/search` | Comissões pagas |
| `totvs_search_devolutions` | GET | `/general/v2/devolutions/search` | Devoluções |

### Compras & Produção
| Tool | Método | Endpoint | Descrição |
|------|--------|----------|-----------|
| `totvs_search_purchase_orders` | POST | `/purchase-order/v2/search` | Pedidos de compra |
| `totvs_search_production_orders` | POST | `/production-order/v2/orders/search` | Ordens de produção |

### Geral
| Tool | Método | Endpoint | Descrição |
|------|--------|----------|-----------|
| `totvs_get_operations` | GET | `/general/v2/operations` | Operações disponíveis |
| `totvs_get_branch_parameters` | GET | `/general/v2/branch-parameter` | Parâmetros da filial |
| `totvs_get_global_parameters` | GET | `/general/v2/global-parameter` | Parâmetros globais |
| `totvs_get_users` | GET | `/general/v2/users` | Usuários do sistema |
| `totvs_get_cep` | GET | `/general/v2/ceps/{cep}` | Consulta endereço por CEP |
| `totvs_search_sellers` | POST | `/seller/v2/search` | Vendedores |

### Contexto
| Tool | Descrição |
|------|-----------|
| `totvs_get_context` | Retorna todos os dados de referência carregados na inicialização (ver seção abaixo) |

---

## Pré-requisitos

- Python 3.11+
- Acesso à API V2 do TOTVS Moda (client_id, client_secret, usuário e senha)
- Claude Desktop, Claude Code ou qualquer cliente MCP compatível

---

## Instalação

```bash
git clone https://github.com/fabianoomura/MCP-Server-Totvs-Moda.git
cd MCP-Server-Totvs-Moda

pip install -r requirements.txt
```

---

## Configuração

```bash
cp .env.example .env
```

Edite o `.env` com as credenciais do seu ambiente TOTVS:

```env
TOTVS_BASE_URL=https://seu-servidor-totvs:9443
TOTVS_CLIENT_ID=seu_client_id
TOTVS_CLIENT_SECRET=sua_client_secret
TOTVS_USERNAME=seu_usuario
TOTVS_PASSWORD=sua_senha
```

---

## Uso com Claude Code (VS Code Extension)

Abra a paleta de comandos (`Ctrl+Shift+P`), busque **"MCP: Open User Configuration"** e adicione:

```json
{
  "servers": {
    "totvs-moda": {
      "command": "python",
      "args": ["/caminho/absoluto/para/MCP-Server-Totvs-Moda/server.py"],
      "env": {
        "TOTVS_BASE_URL": "https://seu-servidor-totvs:9443",
        "TOTVS_CLIENT_ID": "seu_client_id",
        "TOTVS_CLIENT_SECRET": "sua_client_secret",
        "TOTVS_USERNAME": "seu_usuario",
        "TOTVS_PASSWORD": "sua_senha"
      }
    }
  }
}
```

## Uso com Claude Code (CLI)

```bash
claude mcp add --transport stdio --scope user totvs-moda \
  -e TOTVS_BASE_URL=https://seu-servidor-totvs:9443 \
  -e TOTVS_CLIENT_ID=seu_client_id \
  -e TOTVS_CLIENT_SECRET=sua_client_secret \
  -e TOTVS_USERNAME=seu_usuario \
  -e TOTVS_PASSWORD=sua_senha \
  -- python /caminho/para/server.py
```

## Uso com Claude Desktop

Adicione ao seu `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "totvs-moda": {
      "command": "python",
      "args": ["/caminho/absoluto/para/MCP-Server-Totvs-Moda/server.py"],
      "env": {
        "TOTVS_BASE_URL": "https://seu-servidor-totvs:9443",
        "TOTVS_CLIENT_ID": "seu_client_id",
        "TOTVS_CLIENT_SECRET": "sua_client_secret",
        "TOTVS_USERNAME": "seu_usuario",
        "TOTVS_PASSWORD": "sua_senha"
      }
    }
  }
}
```

---

## Exemplos de uso no Claude

```
"Quais pedidos foram criados hoje?"

"Mostre as notas fiscais do pedido 12345."

"Qual o estoque do produto 10000?"

"Liste os 10 produtos mais vendidos este mês."

"Qual a posição financeira do cliente CPF 123.456.789-00?"

"Qual o status do pedido SHP-13518?"
```

---

## Cache de contexto

Ao iniciar, o servidor executa automaticamente uma carga de dados de referência do TOTVS e os mantém em memória. Isso evita chamadas repetitivas de lookup durante consultas, criações e alterações.

### O que é carregado

| Chave | Origem | Conteúdo |
|-------|--------|----------|
| `branches` | extraído de `management/v2/users` | Filiais únicas com `branchCode` e `branchName` |
| `operations` | `general/v2/operations` | Todas as operações (entrada/saída) ativas e inativas |
| `paymentConditions` | `general/v2/payment-conditions` | Condições de pagamento disponíveis |
| `paymentPlans` | `general/v2/payment-plans` | Planos de pagamento |
| `priceTables` | `product/v2/price-tables-headers` | Cabeçalhos das tabelas de preço |
| `classifications` | `product/v2/classifications` | Classificações de produto |
| `categories` | `product/v2/category` | Categorias de produto |
| `grids` | `product/v2/grid` | Grades disponíveis (tamanhos) |
| `measurementUnits` | `product/v2/measurement-unit` | Unidades de medida |
| `users` | `management/v2/users` | Usuários cadastrados (e seus `branchCode`) |
| `priceTypes` | `product/v2/prices/search` | Tipos de preço ativos (código + nome) |
| `costTypes` | `product/v2/costs/search` | Tipos de custo ativos (código + nome) |

### Como `branches` é construído

O TOTVS Moda não possui um endpoint de listagem de filiais sem parâmetros. O servidor extrai os `branchCode` únicos da lista de usuários (`management/v2/users`), que retornam com o campo `branchCode` associado. Os valores são deduplicados e ordenados, formando a lista `branches`.

### Como `priceTypes` e `costTypes` são descobertos

O TOTVS Moda não expõe um endpoint dedicado para listar tipos de preço e custo. Na inicialização, o servidor adota a seguinte estratégia:

1. Busca o **produto mais vendido nos últimos 30 dias** via `ecommerce-sales-order/v2/best-selling-products/search`.
2. Se não houver vendas no período, faz um fallback para **qualquer produto** via `product/v2/products/search`.
3. Com o `productCode` obtido, consulta preços passando `priceCodeList: [1..20]` — o TOTVS retorna apenas os tipos que existem, ignorando os inválidos.
4. Os pares `{priceCode, priceName}` e `{costCode, costName}` extraídos são armazenados em `priceTypes` e `costTypes`.

### Como usar o contexto

Chame `totvs_get_context` antes de qualquer operação de escrita para obter os códigos corretos:

```
"Quais tipos de preço estão disponíveis?"
→ totvs_get_context  →  priceTypes: [{priceCode: 1, priceName: "Preço de Venda"}, ...]
```

O resultado de `totvs_get_context` é o mesmo objeto em memória — não gera chamadas adicionais ao TOTVS enquanto o servidor estiver rodando.

### Atualização do cache

O cache é carregado uma vez na inicialização. Para recarregar sem reiniciar o servidor, basta chamar `totvs_get_context` — se ainda não estiver carregado, ele dispara o `load()` automaticamente.

---

## Autenticação TOTVS

O servidor usa o fluxo **OAuth2 Resource Owner Password Credentials (ROPC)**, padrão do TOTVS Moda API V2. O token é obtido automaticamente e renovado antes de expirar — nenhuma ação manual é necessária.

---

## Operações de escrita

Tools marcadas com ⚠️ **modificam dados no TOTVS**. Use com atenção.

---

## Estrutura do projeto

```
MCP-Server-Totvs-Moda/
├── server.py                        # Entry point MCP (stdio)
├── totvs_client.py                  # HTTP client com OAuth2 auto-refresh
├── context_cache.py                 # Cache de dados de referência (carregado na inicialização)
├── tools/
│   ├── __init__.py
│   ├── sales_order.py               # Pedidos de venda
│   ├── product.py                   # Produtos
│   ├── person.py                    # Clientes
│   ├── fiscal.py                    # Fiscal / NF-e
│   ├── accounts_receivable.py       # Contas a receber
│   ├── account_payable.py           # Contas a pagar
│   ├── analytics.py                 # Analytics e relatórios
│   ├── purchase_order.py            # Pedidos de compra
│   ├── seller.py                    # Vendedores
│   ├── voucher.py                   # Vouchers
│   ├── general.py                   # Parâmetros e utilitários
│   └── other_modules.py             # Módulos adicionais
├── requirements.txt
├── .env.example
└── README.md
```

---

## Licença

MIT — use livremente, inclusive em projetos comerciais.
