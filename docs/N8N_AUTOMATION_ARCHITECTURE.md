# Automacao n8n com TOTVS Moda MCP

Este documento descreve uma possibilidade de arquitetura para criar canais de consulta por IA usando n8n, Telegram, interface web/PC e o servidor MCP do TOTVS Moda.

O objetivo e permitir que diretoria, vendedores e representantes consultem informacoes da empresa em linguagem natural, com respostas rapidas, seguras e adequadas ao perfil de acesso.

## Objetivo

Criar uma camada conversacional para perguntas como:

- "Quanto vendemos hoje?"
- "Quais clientes novos entraram esta semana?"
- "Como esta o estoque do produto 13180?"
- "Dados do pedido 120040."
- "Pedidos de compra em aberto."
- "Ordens de producao em aberto."
- "Qual cliente do meu representante esta com pedido bloqueado?"

## Visao geral

Arquitetura sugerida:

```text
Telegram / Web / PC
        |
        v
      n8n
        |
        v
 Roteador de intencao
        |
        +--> Banco analitico
        |
        +--> TOTVS Moda MCP
        |
        +--> RAG documental
        |
        v
 Resposta formatada por perfil
```

## Componentes

### TOTVS Moda MCP

O MCP deve continuar como a camada oficial de acesso ao ERP.

Ele e indicado para:

- consultas pontuais em tempo real;
- dados de produto, pedido, cliente, NF, estoque, compras e producao;
- tools compostas, como `product_360`, `order_360`, `invoice_360`;
- operacoes que exigem o dado mais atual possivel.

Continuar otimizando o MCP e importante, porque todas as automacoes se beneficiam de tools mais rapidas e respostas mais compactas.

### n8n

O n8n deve atuar como orquestrador.

Responsabilidades:

- receber mensagens do Telegram ou webhooks;
- identificar usuario e perfil;
- chamar o LLM;
- decidir o fluxo correto;
- chamar MCP, banco analitico ou RAG;
- registrar logs;
- devolver resposta no canal correto.

### Banco analitico

Para diretoria e perguntas amplas, recomenda-se criar um banco proprio.

Sugestao inicial:

- PostgreSQL.

Pode evoluir no futuro para:

- ClickHouse;
- BigQuery;
- DuckDB para analises locais;
- outro data warehouse.

Dados recomendados:

- pedidos de venda;
- itens de pedido;
- clientes;
- produtos;
- saldos de estoque;
- notas fiscais;
- contas a receber;
- contas a pagar;
- pedidos de compra;
- ordens de producao;
- representantes/vendedores;
- metas, se existirem.

O banco analitico evita que perguntas amplas dependam sempre de varrer a API do TOTVS ao vivo.

### RAG documental

RAG deve ser usado para conhecimento textual, nao para dados transacionais.

Bom uso de RAG:

- politica comercial;
- regras de desconto;
- regras de comissao;
- manuais internos;
- significado operacional de status;
- procedimentos de venda;
- treinamentos;
- contratos e condicoes comerciais;
- documentos fiscais/operacionais internos.

Evitar RAG para:

- venda do dia;
- estoque atual;
- dados de pedido;
- dados de NF;
- ranking de clientes;
- contas a receber/pagar.

Esses casos sao dados estruturados e devem vir do banco analitico ou do MCP.

### LangGraph

LangGraph nao precisa ser a primeira escolha.

Comecar com:

- n8n;
- LLM;
- MCP;
- PostgreSQL;
- RAG simples.

LangGraph passa a fazer sentido quando:

- o agente precisa executar planos com muitos passos;
- existe memoria de estado entre etapas;
- ha revisao automatica da resposta;
- ha aprovacao humana em fluxos complexos;
- o roteamento de ferramentas fica grande demais para manter no n8n;
- o agente precisa comparar varias hipoteses antes de responder.

Para MVP, n8n provavelmente e suficiente.

## Canais

### Canal diretoria

Perfil com acesso amplo.

Pode responder:

- vendas do dia, semana, mes;
- comparativo com periodos anteriores;
- ranking de produtos;
- ranking de clientes;
- desempenho por vendedor;
- contas a receber/pagar resumidas;
- pedidos bloqueados;
- estoque parado;
- producao em aberto;
- compras em aberto;
- alertas gerenciais.

Respostas devem ser:

- objetivas;
- agregadas;
- com numeros principais primeiro;
- com detalhamento sob demanda.

### Canal vendedores e representantes

Perfil com acesso restrito.

Pode responder:

- produtos disponiveis;
- preco e estoque;
- dados de cliente permitido;
- pedidos do proprio vendedor/representante;
- status de pedido;
- historico comercial autorizado;
- comissoes, se permitido;
- alertas de cliente ou pedido.

Regras importantes:

- vendedor nao deve enxergar carteira de outro vendedor se a empresa restringir;
- dados financeiros sensiveis devem ser filtrados;
- CPF/CNPJ devem ser mascarados quando nao forem necessarios;
- qualquer operacao de escrita deve exigir confirmacao.

## Roteamento de perguntas

O roteador deve decidir a origem da resposta:

```text
Pergunta ampla/historica
        -> banco analitico

Pergunta pontual/tempo real
        -> MCP TOTVS

Pergunta sobre regra/documento/procedimento
        -> RAG documental

Pergunta que mistura indicadores e regra
        -> banco/MCP + RAG
```

Exemplos:

| Pergunta | Fonte ideal |
| --- | --- |
| "Quanto vendemos hoje?" | Banco analitico ou `totvs_sales_today_summary` |
| "Dados do produto 13180" | `totvs_product_360` |
| "Dados da NF 143218" | `totvs_invoice_360` |
| "Pedidos de compra em aberto" | `totvs_open_purchase_orders` |
| "Qual a regra de desconto para atacado?" | RAG documental |
| "Quais clientes novos entraram hoje?" | Banco analitico ou `totvs_new_customers_today` |

## Sincronizacao de dados

Sugestao de jobs n8n:

| Frequencia | Dados |
| --- | --- |
| A cada 5 minutos | vendas recentes, pedidos recentes, estoque critico |
| A cada 15 minutos | contas a receber, contas a pagar, compras, producao |
| A cada 1 hora | saldos gerais, produtos alterados, clientes alterados |
| Diario | cadastros completos, custos, classificacoes, consolidacoes |
| Sob demanda | consultas pontuais via MCP |

O ideal e usar carga incremental quando a API permitir filtros por data de alteracao.

## Modelo de permissao

Criar uma tabela de usuarios:

```text
users
- id
- name
- telegram_id
- email
- role
- person_code
- representative_code
- active
```

Perfis sugeridos:

- `director`;
- `manager`;
- `salesperson`;
- `representative`;
- `admin`.

Cada perfil deve ter uma matriz de permissao:

```text
permissions
- role
- can_view_sales_total
- can_view_financial
- can_view_all_customers
- can_view_own_customers
- can_view_cost
- can_write_erp
```

## Segurança

Recomendacoes:

- autenticar Telegram ID ou login web;
- registrar pergunta, usuario, ferramentas chamadas e resposta;
- mascarar dados sensiveis quando possivel;
- separar canal diretoria e canal vendedores;
- nunca executar escrita no ERP sem confirmacao explicita;
- limitar acesso por representante/vendedor;
- usar variaveis de ambiente para credenciais;
- manter o MCP em rede privada quando possivel.

## Infra sugerida

MVP em Docker Compose:

```text
n8n
postgres
redis
totvs-moda-mcp
rag-service opcional
reverse-proxy opcional
```

Componentes:

- n8n para fluxos;
- PostgreSQL para banco analitico, permissoes e logs;
- Redis para filas/cache, se necessario;
- MCP TOTVS Moda como servico interno;
- Telegram Bot;
- interface web simples, se desejado.

## Fases de implantacao

### Fase 1: MVP diretoria

- Canal Telegram diretoria.
- Perguntas de vendas do dia.
- Clientes novos.
- Pedidos de compra em aberto.
- Ordens de producao em aberto.
- Dados de produto, pedido e NF via MCP.
- Logs basicos.

### Fase 2: Banco analitico

- Criar PostgreSQL.
- Sincronizar pedidos, itens, clientes, produtos e estoque.
- Criar consultas SQL para perguntas gerenciais.
- Reduzir dependencia de consultas amplas ao TOTVS ao vivo.

### Fase 3: Canal vendedores/representantes

- Autenticacao por Telegram ID ou login.
- Restricao por representante/vendedor.
- Consulta de produto, estoque, preco e pedidos.
- Respostas filtradas por permissao.

### Fase 4: RAG documental

- Indexar politicas comerciais.
- Indexar regras de comissao.
- Indexar procedimentos internos.
- Responder perguntas de regra com citacao de fonte interna.

### Fase 5: Agente mais avancado

- Avaliar LangGraph se o roteamento ficar complexo.
- Adicionar memoria operacional.
- Adicionar aprovacao humana.
- Criar analises proativas e alertas.

## Recomendacao

Comecar sem LangGraph.

Prioridade sugerida:

1. Continuar otimizando o MCP com tools compostas.
2. Criar canal diretoria no n8n.
3. Criar banco analitico PostgreSQL.
4. Criar canal vendedores/representantes com permissao.
5. Adicionar RAG documental.
6. Avaliar LangGraph apenas se os fluxos ficarem complexos demais para n8n puro.

Resumo:

```text
MCP para tempo real.
Banco analitico para perguntas amplas.
RAG para documentos e regras.
n8n para orquestrar.
LangGraph somente se a complexidade justificar.
```
