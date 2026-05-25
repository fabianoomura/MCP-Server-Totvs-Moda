# Documentacao - TOTVS Moda MCP

Este diretorio concentra o contexto necessario para manter e evoluir o projeto.

## Leitura recomendada

Para entender e contribuir com o projeto publico:

1. `PATTERNS.md` - padroes obrigatorios de implementacao.
2. `AGENT_ENDPOINT_HARNESS.md` - como usar a matriz de endpoints.
3. `API_ENDPOINT_MATRIX.md` - matriz derivada do Swagger, sem schemas brutos.

## Arquivos gerados

- `API_ENDPOINT_MATRIX.md`
- `API_ENDPOINT_MATRIX.json`

Gerar novamente depois de alterar tools ou Swagger:

```powershell
python scripts\build_endpoint_harness.py --write
```

Observacao: os arquivos Swagger brutos ficam em `json/` apenas no ambiente local/privado e nao sao versionados no repositorio publico.

## Arquivos de apoio

- `AGENT_ENDPOINT_HARNESS.md` - como usar o harness.

## Estado validado

Ultima validacao local documentada:

```powershell
python -m pytest -q
# 204 passed
```

## Importante

O projeto e open source e nao deve carregar regra especifica de uma empresa no codigo principal. Parametros e defaults operacionais devem vir de contexto, `.env` ou configuracao, nao hardcoded.
