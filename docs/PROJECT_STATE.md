# TOTVS Moda MCP - Estado do Projeto

Atualizado em 2026-05-24.

## Identificacao

- Projeto: MCP Server para API V2 do TOTVS Moda
- Repo: https://github.com/fabianoomura/MCP-Server-Totvs-Moda
- PyPI: https://pypi.org/project/totvs-moda-mcp/
- Local: `C:\Users\mooui\mcp-servers\totvs-moda-mcp`
- Ambiente: Windows + VS Code + MCP via stdio
- Python: 3.11
- Licenca: MIT

Projeto open source, nao oficial da TOTVS.

## Status atual

- Testes locais: `202 passed`
- Harness de endpoints: `251/251` mapeados
- Cobertura do nucleo nao-Analytics: `190/190`
- Analytics/painel: `61/61` mapeado via gateway opcional `totvs_analytics_call`
- Swagger local: pasta `json/`
- Publicacao em preparacao: `totvs-moda-mcp==3.7.0`, tag `v3.7.0`

## Modulos e cobertura por harness

| Area | Endpoints | Mapeados | Status |
| --- | ---: | ---: | --- |
| Sales Order | 26 | 26 | fechado |
| Fiscal | 11 | 11 | fechado |
| Accounts Payable | 4 | 4 | fechado |
| Accounts Receivable | 14 | 14 | fechado |
| Product Engineering | 7 | 7 | fechado |
| Production Order | 3 | 3 | fechado no harness |
| Product | 42 | 42 | fechado |
| Material Request | 9 | 9 | fechado |
| Product Prototype | 3 | 3 | fechado |
| Logistics | 4 | 4 | fechado |
| Person | 20 | 20 | fechado, inclui destrutivo bem marcado |
| Purchase Order | 6 | 6 | fechado |
| Seller | 5 | 5 | fechado |
| Voucher | 4 | 4 | fechado |
| Data Package | 7 | 7 | mapeado, mas pode depender de modulo contratado |
| General | 15 | 15 | fechado |
| Global/location | 4 | 4 | fechado |
| Image | 6 | 6 | fechado |
| Analytics | 61 | 61 | gateway opcional, habilitado por `TOTVS_ENABLE_ANALYTICS=true` |

Fonte: `docs/API_ENDPOINT_MATRIX.md`.

## Entregas recentes

- Harness de Swagger em `scripts/build_endpoint_harness.py`.
- Docs de matriz gerados:
  - `docs/API_ENDPOINT_MATRIX.md`
  - `docs/API_ENDPOINT_MATRIX.json`
- Tools rapidas e agregadoras para diretoria/operacao:
  - dashboards diarios
  - cliente 360
  - produto 360
  - pedido 360
  - NF 360
  - estoque a pronta entrega
  - pedidos de compra em aberto
  - ordens de producao em aberto
- Defaults operacionais carregados no contexto inicial.
- Paginacao paralela para consultas grandes.
- Product Engineering ampliado para services, operations, applications, engineering default/configurations e references.
- Product auxiliares read-only adicionados: additional fields, tipos de classificacao, composicoes, instruction items, escalas de tabela e grouper configuration.
- Nucleo nao-Analytics fechado no harness: Sales Order, Product, Person, Purchase Order, General, Seller e Image completados.
- Analytics/painel mapeado 61/61 por gateway isolado `totvs_analytics_call`, sem poluir o contexto principal quando desabilitado.
- Material Request mapeado 9/9.
- Product Prototype mapeado 3/3.
- Logistics mapeado 4/4.
- Person/CRM ampliado para 20/20, com `option`, `expand`, filtros oficiais PF/PJ e remocao de classificacao bem marcada como destrutiva.
- Upsert TOTVS documentado e testado:
  - preco/custo: update primeiro, create se `NotFound`.
  - classificacao/vinculo: create primeiro, update se `AlreadyExist`.

## Padroes obrigatorios

Detalhes em `docs/PATTERNS.md`.

1. Search tools devem separar campos de controle do `filter`.
2. `fields` e reducao de payload sao locais, nao devem ir para a API.
3. Writes devem ser marcados com risco no schema/descricao.
4. Writes destrutivos nao devem ser smoke-tested na API real sem confirmacao.
5. Endpoint novo exige teste de contrato com `respx`.
6. Depois de mudar cobertura, rodar `python scripts\build_endpoint_harness.py --write`.

## Arquivos principais

```text
server.py
totvs_client.py
context_cache.py
tools/
tests/
scripts/build_endpoint_harness.py
json/
docs/API_ENDPOINT_MATRIX.md
docs/PATTERNS.md
docs/PERFORMANCE.md
docs/N8N_AUTOMATION_ARCHITECTURE.md
```

## Proximos passos recomendados

1. Rodar smoke tests read-only dos endpoints de Analytics/painel apenas se houver modulo contratado.
2. Evoluir endpoints Analytics mais usados para tools dedicadas se houver uso real.
3. Refinar schemas dos writes complexos com exemplos do Swagger.
4. Rodar smoke tests read-only selecionados dos novos reads.

## Comandos de validacao

```powershell
python -m compileall -q server.py tools
python -m pytest -q
python scripts\build_endpoint_harness.py --write
```

Estado validado: `202 passed`.
