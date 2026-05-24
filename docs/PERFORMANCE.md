# Performance

Este projeto usa duas estrategias principais para consultas rapidas:

- Tools agregadoras: uma chamada MCP retorna uma resposta de negocio pronta, ja filtrada e somada.
- Paginacao paralela: consultas grandes buscam a primeira pagina para descobrir o total e depois carregam as demais paginas em paralelo.

## Benchmarks locais

Data dos testes: 2026-05-22.

Ambiente: servidor MCP local com API TOTVS remota.

| Consulta | Sequencial | Paralelo | Ganho |
| --- | ---: | ---: | ---: |
| 5 chamadas MCP comuns | 1.50s | 0.66s | 2.28x |
| Ordens de producao em aberto, 40 paginas | 13.79s | 1.97s | 7.00x |
| Pedidos de compra em aberto, 15 paginas | 10.27s | 1.85s | 5.55x |

O startup do servidor MCP levou aproximadamente 7.8s nos testes por carregar contexto inicial. Depois de iniciado, `list_tools` ficou em aproximadamente 0.05s.

## Tools rapidas

### `totvs_product_360`

Use para perguntas como "dados do produto 13180".

Comportamento:

- Busca cadastro, saldo, preco, custo, composicao e ficha de consumo em paralelo.
- Usa `branchCode`, `priceCodeList`, `costCodeList` e `stockCodeList` do contexto inicial quando nao informados.
- Retorna cada secao bruta e um `summary` com as contagens.

Benchmark local do prototipo:

- Sequencial: 0.814s.
- Paralelo: 0.190s.
- Ganho: 4.28x.

### `totvs_raw_material_360`

Use para perguntas como "sobre a materia-prima 1000258".

Comportamento:

- Reaproveita a visao de produto para dados, saldo, preco e custo.
- Tenta localizar usos na ficha de consumo via codigos de materia-prima/material.

### `totvs_order_360`

Use para perguntas como "dados do pedido 120040".

Comportamento:

- Busca o pedido com itens.
- Usa a filial retornada pelo pedido quando o usuario nao informou `branchCode`.
- Busca notas vinculadas e itens pendentes em paralelo.
- Nao chama sugestoes de faturamento por padrao, pois o endpoint validou chave incompleta nos testes reais.

Benchmark local do prototipo:

- Sequencial: 0.264s.
- Paralelo apos cabecalho: 0.148s.
- Ganho: 1.78x.

### `totvs_invoice_360`

Use para perguntas como "dados da NF 143218".

Comportamento:

- Busca cabecalho fiscal e produtos da nota em paralelo.

Benchmark local do prototipo:

- Sequencial: 0.676s.
- Paralelo: 0.045s.
- Ganho: 15.0x.

### `totvs_sales_today_summary`

Use para perguntas como "o que vendi hoje".

Comportamento:

- Busca pedidos da data.
- Retorna total de pedidos, valor total, resumo por status e ranking de pedidos.

### `totvs_stock_available`

Use para perguntas como "quais itens tenho a pronta entrega".

Parametros importantes:

- `productKind="finished"`: produto acabado ativo, melhor padrao para pronta entrega comercial.
- `productKind="raw_material"`: materia-prima.
- `productKind="bulk"`: material de consumo.
- `productKind="all"`: todos os SKUs com saldo, incluindo insumos e embalagens.

Mapeamento TOTVS:

- `finished` aplica `branchInfo.isFinishedProduct=true`, `isRawMaterial=false`, `isBulkMaterial=false`.
- `raw_material` aplica `branchInfo.isRawMaterial=true`.
- `bulk` aplica `branchInfo.isBulkMaterial=true`.
- Para `productKind` diferente de `all`, `onlyActive` assume `true` por padrao.

### `totvs_new_customers_today`

Use para perguntas como "algum cliente novo hoje".

Comportamento:

- Busca clientes que compraram na data.
- Verifica em paralelo o historico desde `lookbackStartDate` (default `2020-01-01`).
- Considera novo quando a quantidade total do historico ate a data e igual a quantidade de compras da data.

### `totvs_open_purchase_orders`

Use para perguntas como "pedidos de compra em aberto".

Comportamento:

- Pagina `/api/totvsmoda/purchase-order/v2/search` em paralelo.
- Usa `branchCodeList` do contexto quando nao informado.
- Considera abertos os status `[1, 3, 5]` por padrao.
- Filtra status localmente apos carregar as paginas, evitando depender de comportamento variavel do filtro da API.
- Retorna totais, resumo por status, maiores valores e pedidos mais recentes.

Parametros uteis:

- `openStatusList`: sobrescreve os status considerados abertos.
- `concurrency`: numero de paginas paralelas, default 10, limite interno 20.
- `pageSize`: itens por pagina, default 100.
- `topN`: tamanho dos rankings, default 20.

### `totvs_open_production_orders`

Use para perguntas como "ordens de producao em aberto".

Comportamento:

- Pagina `/api/totvsmoda/production-order/v2/orders/search` em paralelo.
- Usa `branchCodeList` do contexto quando nao informado.
- Considera aberta a ordem com `pendingQuantity > 0` e `endDate` vazio.
- Retorna totais de quantidade, quantidade pendente, resumo por status, atrasadas, maiores pendencias e ordens mais recentes.

Parametros uteis:

- `asOfDate`: data `YYYY-MM-DD` para calcular atrasos, default hoje.
- `concurrency`: numero de paginas paralelas, default 10, limite interno 20.
- `pageSize`: itens por pagina, default 100.
- `topN`: tamanho dos rankings, default 20.

## Recomendacoes

- Prefira essas tools para perguntas operacionais de "em aberto" em vez de chamar a busca base e paginar manualmente.
- Mantenha `concurrency=10` como padrao. Aumentar acima disso pode pressionar a API sem ganho proporcional.
- Use cache curto para dados operacionais: financeiro em 15 minutos e estoque/producao em 5 minutos.
- Para novas consultas grandes, siga o mesmo padrao: primeira pagina sequencial, demais paginas com semaforo, filtro local e resposta agregada pequena.

## Defaults operacionais

O contexto inicial expõe `operationalDefaults` para evitar que as tools 360 fiquem presas a uma empresa:

- `priceCodeList`: vem de `TOTVS_DEFAULT_PRICE_CODES`, fallback `1`.
- `costCodeList`: vem de `TOTVS_DEFAULT_COST_CODES`, fallback `1,2,3`.
- `stockCodeList`: vem de `TOTVS_DEFAULT_STOCK_CODES`, fallback `1`.
- `purchaseOrderOpenStatusList`: `[1,3,5]`, padrao TOTVS para pedidos de compra em aberto.

As tools aceitam sobrescrever esses valores por chamada quando necessario.
