# TOTVS Moda MCP Server

[![PyPI version](https://img.shields.io/pypi/v/totvs-moda-mcp)](https://pypi.org/project/totvs-moda-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/totvs-moda-mcp)](https://pypi.org/project/totvs-moda-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Servidor MCP (Model Context Protocol) para a **API V2 do TOTVS Moda**.

> **Projeto inicial e não oficial.** Não tem vínculo com a TOTVS S.A.
> Construído de forma independente, evolui conforme necessidades reais de uso.
> Se encontrar problema, abra uma issue. PRs são bem-vindos.

---

## O que é

O MCP (Model Context Protocol) é o protocolo aberto da Anthropic que permite que LLMs (Claude, Copilot, Cursor etc.) usem ferramentas externas de forma padronizada. Este projeto expõe a API V2 do TOTVS Moda como um conjunto de tools MCP, permitindo que você consulte e opere o ERP via linguagem natural.

---

## O que você pode fazer

Exemplos reais do que funciona hoje:

```
"Quais pedidos foram criados hoje na filial 1?"
"Qual o faturamento da semana passada por filial?"
"Me mostra os 10 clientes que mais compraram este mês"
"Quais produtos estão com saldo abaixo de 10 unidades?"
"Qual o preço de venda e custo do produto 10000?"
"Atualiza o preço do produto 10000 para R$ 357,00"
"Atualiza o peso do produto 10000 para 1.5kg"
"Quais títulos vencem até sexta no contas a receber?"
"Cria ou atualiza o cadastro do cliente CPF 123.456.789-00"
"Qual o saldo em estoque da referência X por tamanho e cor?"
"Me mostra as últimas NFes emitidas e gera o XML da NF 1234"
"Quais pedidos estão bloqueados e por qual motivo?"
```

---

## Cobertura

**+150 tools** organizadas em 18 módulos da API V2:

| Módulo | Principais operações |
|---|---|
| **Pedidos de venda** | Buscar, criar, alterar status, cancelar, adicionar/remover itens, alterar preços |
| **Produtos** | Consultar, atualizar dados, preços, custos, peso, NCM, saldos, grades, imagens |
| **Clientes** | Cadastrar, atualizar PF/PJ, consultar histórico, saldo financeiro |
| **Financeiro (CR)** | Títulos, boletos, link de pagamento, cheques-presente, vouchers |
| **Fiscal** | NFes, XMLs, DANFEs, manifestação, faturas |
| **Compras** | Pedidos de compra, pacotes de entrada/saída |
| **Logística** | Movimentações de material, produção, lotes |
| **Geral** | Operações, condições de pagamento, classificações, CEP, cidades |
| **Analytics** | Agregadores prontos: top clientes, produtos mais vendidos, resumo de faturamento, alerta de estoque |

---

## Requisitos

- Python 3.11+
- API V2 do TOTVS Moda ativa na sua instância
- Credenciais de integração OAuth2 (client_id / client_secret)
- Um cliente MCP: Claude Desktop, VS Code (GitHub Copilot Agent), Cursor, ou qualquer cliente compatível

---

## Instalação

```bash
pip install totvs-moda-mcp
```

---

## Configuração

### mcp.json (Claude Desktop / VS Code)

```json
{
  "servers": {
    "totvs-moda": {
      "command": "python",
      "args": ["-m", "totvs_moda_mcp"],
      "env": {
        "TOTVS_BASE_URL": "https://seu-servidor:9443",
        "TOTVS_CLIENT_ID": "seu_client_id",
        "TOTVS_CLIENT_SECRET": "seu_client_secret",
        "TOTVS_USERNAME": "usuario",
        "TOTVS_PASSWORD": "senha",
        "TOTVS_BRANCH_CODES": "1"
      }
    }
  }
}
```

### Variáveis de ambiente

| Variável | Obrigatório | Descrição |
|---|---|---|
| `TOTVS_BASE_URL` | ✅ | URL base da API (ex: `https://totvs.empresa.com:9443`) |
| `TOTVS_CLIENT_ID` | ✅ | Client ID OAuth2 |
| `TOTVS_CLIENT_SECRET` | ✅ | Client Secret OAuth2 |
| `TOTVS_USERNAME` | ✅ | Usuário TOTVS |
| `TOTVS_PASSWORD` | ✅ | Senha TOTVS |
| `TOTVS_BRANCH_CODES` | — | Filiais separadas por vírgula (default: `1`) |

### Segurança

Evite expor credenciais diretamente no `mcp.json`. Use referências ao ambiente do sistema:

```json
"TOTVS_PASSWORD": "${env:TOTVS_PASSWORD}"
```

---

## Como funciona internamente

- **Autenticação OAuth2** com refresh automático de token
- **Retry com backoff exponencial** em falhas de rede
- **Context cache** carregado no startup: filiais, operações, condições de pagamento, tipos de preço e custo descobertos automaticamente via produtos vendidos recentes
- **Slim mode** no `get_context`: retorna ~5KB por padrão em vez de centenas de KB. Use `verbose=true` para o cache completo
- **Auto-routing** em `update_product_data`: detecta se é um produto único (PUT `/products/{code}/{branch}`) ou lote (PUT `/data`)
- **Upsert automático** em `update_product_price_only` e `update_product_cost`: tenta UPDATE, cai para CREATE se não existir
- **Preenchimento automático** de `branchCode` via `TOTVS_BRANCH_CODES`
- Tools organizadas por módulo em `tools/`

---

## Tools principais

### Produtos

| Tool | Descrição |
|---|---|
| `totvs_search_products` | Busca produtos por filtro |
| `totvs_get_product` | Dados completos de um produto |
| `totvs_search_product_prices` | Preços por tipo de tabela |
| `totvs_search_product_costs` | Custos (reposição, última compra etc.) |
| `totvs_search_product_balances` | Saldos de estoque |
| `totvs_update_product_price_only` | Atualiza preço de venda (valueType injetado) |
| `totvs_update_product_cost` | Atualiza custo (valueType injetado) |
| `totvs_update_product_simple` | Atualiza peso, NCM, CST e flags de um produto |
| `totvs_update_product_data` | Atualiza dados (simples ou batch com auto-routing) |
| `totvs_search_product_images` | Imagens do produto |
| `totvs_upload_product_image` | Sobe imagem para o produto |

### Pedidos de venda

| Tool | Descrição |
|---|---|
| `totvs_search_orders` | Busca pedidos com filtros flexíveis |
| `totvs_create_order` | Cria pedido de venda |
| `totvs_change_order_status` | Altera status do pedido |
| `totvs_cancel_order` | Cancela pedido |
| `totvs_add_order_items` | Adiciona itens |
| `totvs_update_order_items_price` | Altera preços dos itens |
| `totvs_get_order_invoices` | NFes vinculadas ao pedido |

### Clientes

| Tool | Descrição |
|---|---|
| `totvs_search_individual_customers` | Busca clientes PF |
| `totvs_search_legal_customers` | Busca clientes PJ |
| `totvs_create_or_update_individual_customer` | Cadastra/atualiza PF |
| `totvs_create_or_update_legal_customer` | Cadastra/atualiza PJ |
| `totvs_get_person_statistics` | Histórico e estatísticas do cliente |

### Analytics (aggregators)

| Tool | Descrição |
|---|---|
| `totvs_get_products_sold` | Top N produtos mais vendidos no período |
| `totvs_sales_summary_by_period` | Resumo de vendas por filial, status ou dia |
| `totvs_top_customers` | Top N clientes por faturamento |
| `totvs_low_stock_alert` | Produtos abaixo de um saldo mínimo |
| `totvs_orders_by_status_summary` | Distribuição de pedidos por status |

### Contexto

| Tool | Descrição |
|---|---|
| `totvs_get_context` | Filiais, operações, condições de pagamento, priceTypes, costTypes. Use `verbose=true` para o cache completo |

---

## Desenvolvimento e testes

```bash
git clone https://github.com/fabianoomura/MCP-Server-Totvs-Moda.git
cd MCP-Server-Totvs-Moda
pip install -e ".[dev]"

# Rodar testes
PYTHONPATH=. pytest tests/ -v
```

117 testes cobrindo os módulos principais.

---

## Estrutura do projeto

```
totvs-moda-mcp/
├── server.py              # Entry point MCP, registro de tools e routing
├── totvs_client.py        # Cliente HTTP com OAuth2, retry e upsert
├── context_cache.py       # Cache de referência carregado no startup
├── tools/
│   ├── product.py         # Produtos, preços, custos, saldos
│   ├── sales_order.py     # Pedidos de venda
│   ├── person.py          # Clientes PF/PJ
│   ├── accounts_receivable.py
│   ├── fiscal.py
│   ├── logistics.py
│   ├── general.py
│   ├── convenience.py     # Aggregators e helpers
│   ├── _value_types.py    # Normalização de Price/Cost com aliases
│   ├── _defaults.py       # Injeção de branchCode via env
│   └── _fields.py         # Filtro de campos na resposta
└── tests/                 # 117 testes
```

---

## Limitações

- Limitado ao que a **API V2 do TOTVS Moda** expõe publicamente
- Não cobre todas as funcionalidades do ERP — apenas o que a API disponibiliza
- Projeto em evolução — novos módulos adicionados conforme necessidade

---

## Contribuição

1. Abra uma issue descrevendo o problema ou feature
2. Fork + branch + PR com testes
3. Padrão: cada tool nova deve ter ao menos 1 teste

---

## Licença

MIT

---

## Contato

LinkedIn: [Fabiano Omura](https://www.linkedin.com/in/fabiano-o-50619734/)
