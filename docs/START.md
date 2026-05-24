# TOTVS Moda MCP - Contexto rapido

Use este arquivo para retomar o projeto em uma nova conversa.

## Projeto

MCP Server para API V2 do TOTVS Moda. Permite que agentes/LLMs consultem e executem operacoes no ERP usando tools MCP.

- Repo: https://github.com/fabianoomura/MCP-Server-Totvs-Moda
- PyPI: https://pypi.org/project/totvs-moda-mcp/
- Local: `C:\Users\mooui\mcp-servers\totvs-moda-mcp`
- Python: 3.11
- Instalacao local: `pip install -e .`

## Estado atual

Atualizado em 2026-05-24.

- Testes: `202 passed`
- Endpoint harness: `docs/API_ENDPOINT_MATRIX.md` e `.json`
- Swagger local: pasta `json/`
- Cobertura atual do harness: `251/251` endpoints mapeados por path
- Cobertura do nucleo nao-Analytics: `190/190`
- Analytics: `61/61` mapeado via gateway opcional `totvs_analytics_call` (`TOTVS_ENABLE_ANALYTICS=true`)
- Areas fechadas ou quase fechadas:
  - Fiscal: `11/11`
  - Accounts payable: `4/4`
  - Accounts receivable: `14/14`
  - Material request: `9/9`
  - Product prototype: `3/3`
  - Logistics: `4/4`
  - Person: `20/20`
  - Product engineering: `7/7`
  - Product: `42/42`
  - Purchase Order: `6/6`
  - Seller: `5/5`
  - General: `15/15`
  - Image: `6/6`

## Arquivos importantes

```text
server.py                       # MCP server, schemas e ROUTING
totvs_client.py                 # OAuth2, retry, erro TOTVS, upsert helpers
context_cache.py                # contexto inicial e defaults
tools/                          # modulos por area TOTVS
tools/aggregators.py            # tools 360 e consultas rapidas
scripts/build_endpoint_harness.py
docs/API_ENDPOINT_MATRIX.md
docs/API_ENDPOINT_MATRIX.json
docs/PATTERNS.md
docs/PERFORMANCE.md
docs/PROJECT_STATE.md
docs/ROADMAP.md
```

## Padroes rapidos

1. Search tools: montar `filter`, manter `expand`, `option`, `order`, `page`, `pageSize` no topo do body e aplicar `fields` localmente.
2. Write tools: aceitar body generico `{k: v for k, v in args.items() if v is not None}` quando o Swagger permitir evolucao.
3. Upsert TOTVS:
   - Preco/custo: `update -> NotFound -> create`.
   - Vinculo/classificacao: `create -> AlreadyExist -> update`.
4. Toda tool nova precisa de teste, descricao clara de risco e entrada no `ROUTING`.
5. Nao testar writes/destructive na API real sem alvo seguro e confirmacao explicita.

## Consultas rapidas preferenciais

- `totvs_daily_dashboard`
- `totvs_customer_360`
- `totvs_product_360`
- `totvs_raw_material_360`
- `totvs_order_360`
- `totvs_invoice_360`
- `totvs_sales_today_summary`
- `totvs_new_customers_today`
- `totvs_stock_available`
- `totvs_open_purchase_orders`
- `totvs_open_production_orders`

## Como retomar

1. Ler `docs/START.md`, `docs/PROJECT_STATE.md`, `docs/PATTERNS.md`.
2. Consultar `docs/API_ENDPOINT_MATRIX.md` para escolher o proximo bloco.
3. Se implementar endpoint novo, usar o Swagger local em `json/`.
4. Rodar:

```powershell
python -m compileall -q server.py tools
python -m pytest -q
python scripts\build_endpoint_harness.py --write
```

## Proximo ataque sugerido

O harness esta completo, incluindo Analytics como modulo opcional isolado. Proximo bloco sugerido:

- Rodar smoke tests read-only em ambiente real para os endpoints de Analytics/painel que forem contratados.
- Refinar schemas dos writes mais complexos com exemplos do Swagger.
- Criar smoke tests read-only selecionados para os novos reads.
