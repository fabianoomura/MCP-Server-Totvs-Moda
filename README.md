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
| Tool | Tipo | Descrição |
|------|------|-----------|
| `totvs_search_orders` | Leitura | Busca pedidos com filtros flexíveis (data, status, cliente, integração Shopify...) |
| `totvs_get_order_invoices` | Leitura | Notas fiscais vinculadas a um pedido |
| `totvs_get_pending_items` | Leitura | Itens pendentes de faturamento |
| `totvs_get_billing_suggestions` | Leitura | Sugestões de faturamento |
| `totvs_cancel_order` | ⚠️ Escrita | Cancela um pedido |
| `totvs_change_order_status` | ⚠️ Escrita | Altera situação do pedido |
| `totvs_update_order_items_price` | ⚠️ Escrita | Atualiza preços de itens do pedido |

### Produtos
| Tool | Tipo | Descrição |
|------|------|-----------|
| `totvs_search_products` | Leitura | Busca produtos por filtro (referência, categoria, código) |
| `totvs_get_product` | Leitura | Dados completos de um produto pelo código |
| `totvs_get_product_grid` | Leitura | Grade completa (cores e tamanhos) |
| `totvs_search_product_references` | Leitura | Referências de produtos |
| `totvs_search_product_colors` | Leitura | Cores disponíveis |
| `totvs_search_product_balances` | Leitura | Saldo em estoque por filial |
| `totvs_search_product_prices` | Leitura | Preços nas tabelas |
| `totvs_search_product_compositions` | Leitura | Composição dos produtos |
| `totvs_search_product_batch` | Leitura | Lotes de produtos |
| `totvs_search_product_fiscal_movement` | Leitura | Movimentação fiscal de produtos |
| `totvs_search_price_tables` | Leitura | Tabelas de preço disponíveis |
| `totvs_update_product_price` | ⚠️ Escrita | Atualiza preço de produto |
| `totvs_update_promotion_price` | ⚠️ Escrita | Atualiza preço de promoção |

### Clientes
| Tool | Tipo | Descrição |
|------|------|-----------|
| `totvs_search_individual_customers` | Leitura | Busca clientes pessoa física |
| `totvs_search_legal_customers` | Leitura | Busca clientes pessoa jurídica |
| `totvs_get_person_statistics` | Leitura | Estatísticas de um cliente |
| `totvs_search_top_customers` | Leitura | Melhores clientes por período |
| `totvs_search_top_debtors` | Leitura | Maiores devedores |
| `totvs_get_customer_bonus_balance` | Leitura | Saldo de bônus do cliente |
| `totvs_create_or_update_individual_customer` | ⚠️ Escrita | Cria ou atualiza cliente PF |

### Fiscal
| Tool | Tipo | Descrição |
|------|------|-----------|
| `totvs_search_fiscal_invoices` | Leitura | Notas fiscais emitidas |
| `totvs_search_fiscal_movement` | Leitura | Movimentação fiscal |
| `totvs_search_invoice_products` | Leitura | Produtos de uma nota fiscal |
| `totvs_get_danfe` | Leitura | DANFE em PDF |
| `totvs_get_nfe_xml` | Leitura | XML da NF-e |

### Financeiro
| Tool | Tipo | Descrição |
|------|------|-----------|
| `totvs_search_receivable_documents` | Leitura | Títulos a receber |
| `totvs_search_payable_duplicates` | Leitura | Duplicatas a pagar |
| `totvs_search_total_receivable` | Leitura | Total a receber |
| `totvs_search_total_payable` | Leitura | Total a pagar |
| `totvs_search_customer_financial_balance` | Leitura | Posição financeira do cliente |
| `totvs_search_financial_income_statement` | Leitura | DRE financeiro |
| `totvs_get_bank_slip` | Leitura | Boleto bancário |
| `totvs_get_payment_link` | Leitura | Link de pagamento |
| `totvs_simulate_payment_plan` | Leitura | Simula plano de pagamento |
| `totvs_get_payment_conditions` | Leitura | Condições de pagamento disponíveis |
| `totvs_create_voucher` | ⚠️ Escrita | Cria voucher |
| `totvs_search_voucher` | Leitura | Busca vouchers |

### Analytics
| Tool | Tipo | Descrição |
|------|------|-----------|
| `totvs_search_best_selling_products` | Leitura | Produtos mais vendidos |
| `totvs_search_sales_by_hour` | Leitura | Vendas por hora |
| `totvs_search_sales_by_weekday` | Leitura | Vendas por dia da semana |
| `totvs_search_commissions_paid` | Leitura | Comissões pagas |
| `totvs_search_devolutions` | Leitura | Devoluções |

### Compras & Produção
| Tool | Tipo | Descrição |
|------|------|-----------|
| `totvs_search_purchase_orders` | Leitura | Pedidos de compra |
| `totvs_search_production_orders` | Leitura | Ordens de produção |
| `totvs_get_kardex_movement` | Leitura | Movimentação kardex |

### Geral
| Tool | Tipo | Descrição |
|------|------|-----------|
| `totvs_get_operations` | Leitura | Operações disponíveis |
| `totvs_get_branch_parameters` | Leitura | Parâmetros da filial |
| `totvs_get_global_parameters` | Leitura | Parâmetros globais |
| `totvs_get_users` | Leitura | Usuários do sistema |
| `totvs_get_cep` | Leitura | Consulta endereço por CEP |
| `totvs_search_sellers` | Leitura | Vendedores |

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

## Autenticação TOTVS

O servidor usa o fluxo **OAuth2 Resource Owner Password Credentials (ROPC)**, padrão do TOTVS Moda API V2. O token é obtido automaticamente e renovado antes de expirar.

---

## Operações de escrita

Tools marcadas com ⚠️ **modificam dados no TOTVS**. Use com atenção.

---

## Estrutura do projeto

```
MCP-Server-Totvs-Moda/
├── server.py                        # Entry point MCP (stdio)
├── totvs_client.py                  # HTTP client com OAuth2 auto-refresh
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
