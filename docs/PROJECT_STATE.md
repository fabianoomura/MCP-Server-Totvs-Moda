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

- Testes locais: `176 passed`
- Harness de endpoints: `169/251` mapeados
- Swagger local: pasta `json/`
- Publicacao preparada: `totvs-moda-mcp==3.6.0`, tag `v3.6.0`
- Existem mudancas locais posteriores a publicacao, ainda nao necessariamente publicadas.

## Modulos e cobertura por harness

| Area | Endpoints | Mapeados | Status |
| --- | ---: | ---: | --- |
| Sales Order | 26 | 23 | principal coberto |
| Fiscal | 11 | 11 | fechado |
| Accounts Payable | 4 | 4 | fechado |
| Accounts Receivable | 14 | 14 | fechado |
| Product Engineering | 7 | 6 | falta write de references |
| Production Order | 3 | 3 | fechado no harness |
| Product | 42 | 38 | auxiliares read-only cobertos; restam writes sensiveis |
| Material Request | 9 | 9 | fechado |
| Product Prototype | 3 | 3 | fechado |
| Logistics | 4 | 4 | fechado |
| Person | 20 | 19 | faltou apenas endpoint destrutivo |
| Purchase Order | 6 | 4 | faltam writes auxiliares |
| Seller | 5 | 4 | quase fechado |
| Voucher | 4 | 4 | fechado |
| Data Package | 7 | 7 | mapeado, mas pode depender de modulo contratado |
| General | 15 | 10 | parcial |
| Global/location | 4 | 4 | fechado |
| Image | 6 | 2 | parcial |
| Analytics | 61 | 0 | opcional/possivelmente nao contratado |

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
- Product Engineering ampliado para services, operations, applications, engineering default/configurations.
- Product auxiliares read-only adicionados: additional fields, tipos de classificacao, composicoes, instruction items, escalas de tabela e grouper configuration.
- Material Request mapeado 9/9.
- Product Prototype mapeado 3/3.
- Logistics mapeado 4/4.
- Person/CRM ampliado para 19/20, com `option`, `expand` e filtros oficiais PF/PJ.
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

1. Purchase Order: avaliar os 2 writes restantes com cautela.
2. General: completar `GET /transactions/search` antes dos writes.
3. Product: avaliar writes auxiliares restantes somente com contrato mockado.
4. Image: mapear imagem de pessoa e imports se fizer sentido.
5. Seller: fechar `operational-area-state`.
6. Analytics: testar apenas se houver modulo contratado e necessidade real.

## Comandos de validacao

```powershell
python -m compileall -q server.py tools
python -m pytest -q
python scripts\build_endpoint_harness.py --write
```

Estado validado: `176 passed`.
