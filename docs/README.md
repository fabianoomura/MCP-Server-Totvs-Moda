# Documentacao - TOTVS Moda MCP

Este diretorio concentra o contexto tecnico necessario para manter o projeto.

> O estado/versao atual do projeto vive no codigo, no `CHANGELOG.md` e no
> `git log`. Este diretorio nao guarda mais docs de "status", "roadmap" ou
> "avancos", que ficavam defasados rapido. Para saber a versao atual,
> consulte o `pyproject.toml` e o `CHANGELOG.md`.

## Leitura recomendada

Para entender e contribuir com o projeto:

1. `PATTERNS.md` - padroes obrigatorios de implementacao.
2. `AGENT_ENDPOINT_HARNESS.md` - como usar a matriz de endpoints.
3. `API_ENDPOINT_MATRIX.md` - matriz derivada do Swagger, sem schemas brutos.
4. `PERFORMANCE.md` - cache, paginacao paralela e tools compostas.
5. `N8N_AUTOMATION_ARCHITECTURE.md` - integracao com automacao externa.

## Arquivos gerados

- `API_ENDPOINT_MATRIX.md`
- `API_ENDPOINT_MATRIX.json`

Gerar novamente depois de alterar tools ou Swagger:

```powershell
python scripts\build_endpoint_harness.py --write
```

Observacao: os arquivos Swagger brutos ficam em `json/` apenas no ambiente
local/privado e nao sao versionados no repositorio publico.

## Validacao local

```powershell
python -m compileall -q server.py tools
python -m pytest -q
python scripts\build_endpoint_harness.py --write
```

## Importante

O projeto e open source e nao deve carregar regra especifica de uma empresa no
codigo principal. Parametros e defaults operacionais devem vir de contexto,
`.env` ou configuracao, nao hardcoded.
