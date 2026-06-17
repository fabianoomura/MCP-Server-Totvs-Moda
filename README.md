# TOTVS Moda MCP Server

[![PyPI version](https://img.shields.io/pypi/v/totvs-moda-mcp)](https://pypi.org/project/totvs-moda-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/totvs-moda-mcp)](https://pypi.org/project/totvs-moda-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Servidor MCP (Model Context Protocol) para a **API V2 do TOTVS Moda**.

> **Projeto inicial e não oficial.** Não tem vínculo com a TOTVS S.A.
> Construído de forma independente, com foco em uso real da API.
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
"Resumo do dia: vendas, contas a receber e a pagar"
"Dados completos do produto 13180"
"Dados da NF 143218"
"Dados do pedido 120040"
"Quais produtos estão com pronta entrega?"
"Visão 360 do cliente CPF 123.456.789-00"
"Qual o preço de venda e custo do produto 10000?"
"Ficha de consumo do produto 13020"
"Quais títulos vencem até sexta no contas a receber?"
"O que tenho pra pagar essa semana?"
"Me mostra os padrões de uso do sistema nos últimos 30 dias"
```

---

## Cobertura

**200+ tools** organizadas por módulos da API V2:

- Harness de endpoints: `251/251` caminhos mapeados na matriz derivada
- Núcleo não-Analytics: `190/190`
- Analytics/painéis: `61/61` via gateway opcional, desabilitado por padrão
- Suite local: `252` testes

| Módulo | Principais operações |
|---|---|
| **Pedidos de venda** | Buscar, criar, alterar status, cancelar, adicionar/remover itens, alterar preços |
| **Produtos** | Consultar, atualizar dados, preços, custos, peso, NCM, saldos, grades, imagens |
| **Engenharia de produto** | Ficha de consumo (matéria-prima + serviços) |
| **Clientes** | Cadastrar, atualizar PF/PJ, consultar histórico, saldo financeiro |
| **Financeiro (CR)** | Títulos, boletos, link de pagamento, cheques-presente, vouchers |
| **Financeiro (CP)** | Duplicatas a pagar, comissões |
| **Fiscal** | NFes, XMLs, DANFEs, manifestação, faturas |
| **Compras** | Pedidos de compra, pacotes de entrada/saída |
| **Produção** | Ordens de produção, consumo de matéria-prima |
| **Logística** | Movimentações de material, lotes |
| **Geral** | Operações, condições de pagamento, classificações, CEP, cidades |
| **Painéis rápidos** | Dashboard do dia, visões 360, estoque disponível, vendas por canal/representante, fluxo de caixa, pedidos/OPs em aberto |
| **Analytics / painéis** | Gateway opcional para endpoints de Analytics, habilitado apenas por ambiente |
| **Inteligência de uso** | Análise de padrões, sequências, horários de pico, sugestões de otimização |

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

Recomendado: mantenha as credenciais em um `.env` local e aponte o MCP para
esse arquivo. Assim o projeto não fica amarrado a uma empresa ou máquina
específica, e o cliente MCP não herda credenciais antigas do sistema.

```json
{
  "servers": {
    "totvs-moda": {
      "command": "totvs-moda-mcp",
      "env": {
        "TOTVS_ENV_FILE": "C:\\\\caminho\\\\para\\\\totvs-moda-mcp\\\\.env",
        "TOTVS_DOTENV_OVERRIDE": "true",
        "TOTVS_BRANCH_CODES": "1"
      }
    }
  }
}
```

Exemplo de `.env`:

```env
TOTVS_BASE_URL=https://seu-servidor:9443
TOTVS_CLIENT_ID=seu_client_id
TOTVS_CLIENT_SECRET=seu_client_secret
TOTVS_USERNAME=usuario
TOTVS_PASSWORD=senha
TOTVS_BRANCH_CODES=1
```

### Variáveis de ambiente

| Variável | Obrigatório | Descrição |
|---|---|---|
| `TOTVS_BASE_URL` | sim | URL base da API (ex: `https://totvs.empresa.com:9443`) |
| `TOTVS_CLIENT_ID` | sim | Client ID OAuth2 |
| `TOTVS_CLIENT_SECRET` | sim | Client Secret OAuth2 |
| `TOTVS_USERNAME` | sim | Usuário TOTVS |
| `TOTVS_PASSWORD` | sim | Senha TOTVS |
| `TOTVS_BRANCH_CODES` | — | Filiais separadas por vírgula (default: `1`) |
| `TOTVS_PROFILE` | — | Perfil de exposição de tools: `completo`, `leitura`, `vendedor`, `financeiro`, `gestor` |
| `TOTVS_TOOLS_EXTRA` | — | Tools extras adicionadas ao perfil, separadas por vírgula |
| `TOTVS_TOOLS_EXCLUDE` | — | Tools removidas do perfil, separadas por vírgula |
| `TOTVS_CACHE_TTL` | — | Override global de TTL do cache em segundos |
| `TOTVS_CACHE_ENABLED` | — | `false` para desativar o cache de respostas |
| `TOTVS_USAGE_ENABLED` | — | `false` para desativar o rastreamento de uso |
| `TOTVS_USAGE_FILE` | — | Caminho customizado para o arquivo de uso |
| `TOTVS_OPERATION_CONTEXT` | — | Texto descrevendo o significado dos status de pedido na sua empresa |
| `TOTVS_TLS_VERIFY` | — | `false` para desativar verificação TLS (self-signed certs) |
| `TOTVS_ENABLE_ANALYTICS` | — | `true` para habilitar o gateway opcional `totvs_analytics_call` |
| `TOTVS_ENV_FILE` | — | Caminho absoluto para um `.env` a carregar quando o cliente MCP inicia em outro diretório |
| `TOTVS_DOTENV_OVERRIDE` | — | `true` para o `.env` sobrescrever variáveis antigas herdadas pelo processo MCP |
| `TOTVS_DEFAULT_PRICE_CODES` | — | Tabelas de preço padrão, ex: `1` |
| `TOTVS_DEFAULT_COST_CODES` | — | Tipos de custo padrão, ex: `1,2,3` |
| `TOTVS_DEFAULT_STOCK_CODES` | — | Tipos de saldo padrão, ex: `1` |

### Perfis de tools

Use `TOTVS_PROFILE` para reduzir as tools expostas ao cliente MCP:

| Perfil | Uso |
|---|---|
| `completo` | Expõe todas as tools disponíveis |
| `leitura` | Oculta as tools anotadas como escrita |
| `vendedor` | Consultas de produto, estoque, preço, pedido, cliente e aggregators comerciais |
| `financeiro` | Contas a receber/pagar, fiscal, voucher e aggregators financeiros |
| `gestor` | Leituras e aggregators completos, sem writes anotadas |

Exemplo:

```env
TOTVS_PROFILE=vendedor
TOTVS_TOOLS_EXTRA=totvs_create_voucher
TOTVS_TOOLS_EXCLUDE=totvs_search_fiscal_invoices
```

### Segurança

Evite expor credenciais diretamente no `mcp.json`. Use referências ao ambiente do sistema:

```json
"TOTVS_PASSWORD": "${env:TOTVS_PASSWORD}"
```

### Política de validação

Consultas de leitura podem ser executadas diretamente, sem confirmação adicional.

Operações que criam, alteram, cancelam, baixam, estornam, removem ou excluem dados devem pedir confirmação explícita antes da execução. Isso vale especialmente para pedidos, clientes, produtos, títulos financeiros, notas fiscais, vouchers, preços, custos e movimentações.

---

## Como funciona internamente

### Infraestrutura

- **Autenticação OAuth2** com refresh automático de token
- **Retry com backoff exponencial** em falhas de rede e 5xx
- **Context cache** no startup: descobre automaticamente filiais, operações, tipos de preço/custo
- **Response cache** com TTL por tier: evita chamadas repetidas à API durante uma sessão

### Response Cache

Cache em memória com TTL diferenciado por tipo de dado:

| Tier | TTL | Tipo de dado |
|------|-----|-------------|
| REFERENCE | 24h | Filiais, operações, composições |
| CATALOG | 1h | Produtos, clientes |
| FINANCIAL | 15min | Contas a receber/pagar |
| STOCK | 5min | Saldos de estoque |
| SALES | 2min | Pedidos de venda |

A primeira consulta busca da API normalmente. Consultas subsequentes dentro do TTL retornam instantaneamente do cache. Nenhum dado é hardcoded — cada empresa tem seus próprios dados cacheados.

### Context Cache e defaults operacionais

No startup, o servidor carrega um contexto curto da empresa para reduzir erros de parametrizacao:

- filiais configuradas em `TOTVS_BRANCH_CODES`;
- operacoes e condicoes de pagamento;
- tabelas de preco (`priceTypes`);
- tipos de custo (`costTypes`);
- defaults operacionais para preco, custo e saldo.

Os codigos de preco e custo variam por empresa. Por isso, o projeto tenta descobri-los automaticamente:

1. Busca pedidos vendidos nos ultimos 30 dias.
2. Extrai ate 20 produtos vendidos.
3. Consulta preco e custo desses produtos sondando codigos validos.
4. Publica o resultado em `totvs_get_context`.

Se a empresa nao tiver vendas recentes ou a descoberta nao retornar dados, configure explicitamente:

```env
TOTVS_DEFAULT_PRICE_CODES=1
TOTVS_DEFAULT_COST_CODES=1,2,3
TOTVS_DEFAULT_STOCK_CODES=1
```

### Consultas historicas

Algumas tools compostas precisam olhar historico para responder corretamente. Por exemplo:

- `totvs_customer_360` busca pedidos do cliente desde `2020-01-01`.
- `totvs_new_customers_today` usa `lookbackStartDate` com default `2020-01-01` para decidir se o cliente realmente e novo.

Esse comportamento reduz falso positivo em "cliente novo", mas pode aumentar o tempo de resposta em bases grandes. Para consultas rapidas ou demonstracoes, passe uma janela menor quando fizer sentido:

```text
Analise os clientes novos de hoje considerando historico desde 2025-01-01.
```

### Usage Intelligence

O servidor registra cada chamada de tool localmente (`~/.totvs-moda-usage.jsonl`), sem envio externo. A tool `totvs_get_usage_insights` analisa o histórico e retorna:

- **Top tools**: quais ferramentas são mais usadas
- **Sequências**: padrões de navegação (ex: "sempre que busca pedidos, consulta NF em seguida")
- **Horários de pico**: quando o sistema é mais usado
- **Padrões de parâmetros**: filtros que se repetem em 70%+ das chamadas (candidatos a default)
- **Sugestões**: recomendações automáticas de composite tools, cache e rotinas

Esses dados ficam no computador do usuário e ajudam a identificar padrões, sequências e consultas que podem se beneficiar de cache.

### Composite Tools (painéis rápidos)

Tools que combinam múltiplas chamadas à API em uma única resposta:

| Tool | O que agrega | Antes | Agora |
|------|-------------|:-----:|:-----:|
| `totvs_daily_dashboard` | Vendas + receber + pagar do dia | 3-6 calls | 1 call |
| `totvs_customer_360` | Dados + histórico + recompra | 2-3 calls | 1 call |
| `totvs_stock_available` | SKUs com estoque > 0 | 18+ páginas | 1 call |
| `totvs_open_purchase_orders` | Pedidos de compra abertos | dezenas de páginas | 1 call |
| `totvs_open_production_orders` | OPs abertas | dezenas de páginas | 1 call |

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
| `totvs_search_consumption_sheet` | Ficha de consumo (matéria-prima + serviços) |
| `totvs_update_product_price_only` | Atualiza preço de venda |
| `totvs_update_product_cost` | Atualiza custo |
| `totvs_update_product_simple` | Atualiza peso, NCM, CST e flags |
| `totvs_update_product_data` | Atualiza dados (simples ou batch) |

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

### Painéis rápidos

| Tool | Descrição |
|---|---|
| `totvs_daily_dashboard` | Vendas + contas a receber + a pagar do dia |
| `totvs_customer_360` | Visão completa do cliente com histórico e flag recompra |
| `totvs_stock_available` | Produtos com estoque disponível, já filtrado |
| `totvs_sales_by_channel` | Vendas por canal/origem em um período |
| `totvs_sales_by_representative` | Vendas por representante/vendedor |
| `totvs_cash_flow_forecast` | Contas a receber, a pagar e saldo líquido previsto por dia |
| `totvs_overdue_financial_summary` | Títulos em atraso no receber e no pagar |
| `totvs_product_stock_by_kind_summary` | Estoque por produto acabado, matéria-prima e material a granel |

### Analytics

Analytics/painéis do TOTVS Moda podem depender de módulo contratado ou permissão específica. Por isso, o projeto mantém esses endpoints em um gateway isolado e desabilitado por padrão.

| Tool | Descrição |
|---|---|
| `totvs_analytics_call` | Gateway opcional para os 61 endpoints Analytics/painel (`TOTVS_ENABLE_ANALYTICS=true`) |
| `totvs_get_products_sold` | Top N produtos mais vendidos no período |
| `totvs_sales_summary_by_period` | Resumo de vendas por filial, status ou dia |
| `totvs_top_customers` | Top N clientes por faturamento |
| `totvs_low_stock_alert` | Produtos abaixo de um saldo mínimo |
| `totvs_orders_by_status_summary` | Distribuição de pedidos por status |
| `totvs_get_usage_insights` | Padrões de uso, sequências e sugestões |

### Contexto

| Tool | Descrição |
|---|---|
| `totvs_get_context` | Filiais, operações, priceTypes, costTypes |
| `totvs_get_instructions` | Guia de uso completo do servidor |

Nota de conexão: `totvs_get_context` pode retornar cache do startup. Ele ajuda a descobrir defaults da empresa, mas não deve ser usado como única prova de autenticação em tempo real. Se ele funcionar e outra consulta retornar `InvalidUserPassword`, reinicie o processo MCP e confira as variáveis `TOTVS_USERNAME`/`TOTVS_PASSWORD` no `mcp.json` ou ambiente do cliente. Quando o cliente estiver herdando env antigo, configure `TOTVS_ENV_FILE` com o caminho absoluto do `.env` correto e `TOTVS_DOTENV_OVERRIDE=true`.

---

## Desenvolvimento e testes

```bash
git clone https://github.com/fabianoomura/MCP-Server-Totvs-Moda.git
cd MCP-Server-Totvs-Moda
pip install -e ".[dev]"

# Rodar testes
PYTHONPATH=. pytest tests/ -v
```

252 testes cobrindo contratos de endpoints, agregadores, defaults, campos, perfis de tools, invalidação de cache, carregamento de ambiente, salvamento de arquivos, normalização de datas e cliente HTTP.

---

## Estrutura do projeto

```
totvs-moda-mcp/
├── server.py              # Entry point MCP, registro de tools e routing
├── totvs_client.py        # Cliente HTTP com OAuth2, retry e upsert
├── context_cache.py       # Cache de referência carregado no startup
├── response_cache.py      # Cache TTL para respostas da API
├── usage_tracker.py       # Rastreamento de uso (JSONL local)
├── usage_analyzer.py      # Análise de padrões e sugestões
├── decode_xml.py          # Decodificador de XML NF-e (base64)
├── tools/
│   ├── sales_order.py     # Pedidos de venda
│   ├── product.py         # Produtos, preços, custos, saldos
│   ├── product_engineering.py  # Ficha de consumo
│   ├── person.py          # Clientes PF/PJ
│   ├── accounts_receivable.py  # Contas a receber
│   ├── account_payable.py # Contas a pagar
│   ├── fiscal.py          # NF-e, XML, DANFE
│   ├── purchase_order.py  # Pedidos de compra
│   ├── other_modules.py   # Produção, management, localização
│   ├── logistics.py       # Pacotes, expedição
│   ├── seller.py          # Vendedores, representantes
│   ├── voucher.py         # Vouchers
│   ├── data_package.py    # Pacotes de dados
│   ├── image.py           # Imagens de produto/pessoa
│   ├── aggregators.py     # Painéis rápidos e consultas compostas
│   ├── analytics.py       # Gateway opcional de Analytics/painéis
│   ├── convenience.py     # Helpers
│   ├── _defaults.py       # Injeção automática de branchCode
│   ├── _fields.py         # Filtro de campos na resposta
│   └── _value_types.py    # Resolução de tipos de valor
├── tests/                 # 252 testes (pytest + respx)
└── docs/
    ├── API_ENDPOINT_MATRIX.md  # Matriz derivada de endpoints
    ├── AGENT_ENDPOINT_HARNESS.md
    ├── FIELDS.md         # Glossário de campos (nomes que confundem)
    └── PATTERNS.md        # Padrões obrigatórios de código
```

---

## Limitações

- Limitado ao que a **API V2 do TOTVS Moda** expõe publicamente
- Não cobre todas as funcionalidades do ERP — apenas o que a API disponibiliza
- Os exports Swagger brutos e notas estratégicas ficam fora do repositório público; o repo publica apenas código, documentação técnica e matriz derivada.

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
