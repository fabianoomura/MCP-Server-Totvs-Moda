# TOTVS Moda MCP - Roadmap

Atualizado em 2026-05-24.

Este roadmap substitui o plano antigo por fases baseadas na matriz real de Swagger em `docs/API_ENDPOINT_MATRIX.md`.

## Situacao atual

- Total no harness: 251 endpoints
- Mapeados: 169
- Testes: 176 passing
- Swagger local: `json/*.json`

## Principios

1. Preservar retrocompatibilidade das tools existentes.
2. Priorizar read-only antes de writes.
3. Tratar writes com upsert quando a TOTVS separar incluir/alterar.
4. Evitar logica especifica de uma empresa no codigo open source.
5. Nao executar destructive writes na API real sem confirmacao explicita.
6. Cada endpoint novo precisa de teste.

## Fase A - Product auxiliares

Prioridade alta. Melhora agentes de Produto, PCP e Comercial.

Status: concluida para endpoints read-only.

Implementados:

- `GET /api/totvsmoda/product/v2/additional-fields-types`
- `GET /api/totvsmoda/product/v2/classificationType`
- `GET /api/totvsmoda/product/v2/composition-group-product`
- `GET /api/totvsmoda/product/v2/composition-product`
- `GET /api/totvsmoda/product/v2/instruction-items`
- `GET /api/totvsmoda/product/v2/price-table-scales`
- `GET /api/totvsmoda/product/v2/product-grouper-configuration`

Writes de produto que exigem cuidado:

- `PUT /batch-info`
- `POST /batch-preferentialsalesorder`
- `POST /colors`
- `POST /grids`

## Fase B - Purchase Order final

Restam 2 endpoints:

- `POST /api/totvsmoda/purchase-order/v2/purchase-order/batch-link`
- `POST /api/totvsmoda/purchase-order/v2/quantity-items`

Ambos sao write. Implementar somente com contrato bem descrito e testes mock.

## Fase C - General

Restam endpoints uteis para agentes operacionais:

- `POST /financial-compensations`
- `POST /product-counts/additional-count`
- `POST /relationship-counts`
- `POST /transaction-classification-relationship/create`
- `GET /transactions/search`

Priorizar `GET /transactions/search` antes dos writes.

## Fase D - Image

Restam:

- `GET /image/v2/person-images`
- `GET /image/v2/persons`
- `POST /image/v2/persons`
- `POST /image/V2/imports`

Implementar primeiro os GETs. Writes de imagem exigem schema e payload base64 claros.

## Fase E - Seller

Fechar:

- `GET /api/totvsmoda/seller/v2/operational-area-state`

Baixo risco.

## Fase F - Product Engineering final

Resta:

- `POST /api/totvsmoda/product-engineering/v2/references`

Write complexo. Implementar apenas se houver caso de uso claro.

## Fase G - Sales Order gaps

Restam:

- `POST /pdv-transactions`
- `POST /relationship-batch-items`
- `POST /suggest-batch-items-nuance`

Todos writes. Avaliar com Swagger e testes mock.

## Fase H - Analytics / paineis internos

Analytics aparece com 61 endpoints no Swagger, mas pode depender de modulo contratado ou permissao especifica.

Recomendacao:

1. Fazer apenas testes read-only pequenos quando necessario.
2. Se nao funcionar no ambiente, manter fora do MCP principal.
3. Se funcionar, criar modulo opcional/isolado para dashboards.

## Rotina de implementacao por fase

1. Ler o bloco da area em `docs/API_ENDPOINT_MATRIX.md`.
2. Conferir o schema no JSON local em `json/`.
3. Implementar no arquivo `tools/<area>.py`.
4. Adicionar tool no `server.py`.
5. Adicionar rota no `ROUTING`.
6. Criar teste mock em `tests/test_tools_regressions.py` ou arquivo especifico.
7. Rodar:

```powershell
python -m compileall -q server.py tools
python -m pytest -q
python scripts\build_endpoint_harness.py --write
```

## Criterio de pronto

- Testes passando.
- Harness atualizado.
- Tool com descricao clara.
- Writes marcados com risco.
- Docs atualizados quando houver novo padrao ou mudanca de cobertura.
