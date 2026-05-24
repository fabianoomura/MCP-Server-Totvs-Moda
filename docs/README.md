# Documentacao - TOTVS Moda MCP

Este diretorio concentra o contexto necessario para manter e evoluir o projeto.

## Leitura recomendada

Para retomar o projeto:

1. `START.md` - resumo rapido e estado atual.
2. `PROJECT_STATE.md` - estado completo, cobertura e decisoes recentes.
3. `PATTERNS.md` - padroes obrigatorios de implementacao.
4. `ROADMAP.md` - proximas fases baseadas no harness.
5. `API_ENDPOINT_MATRIX.md` - matriz completa gerada do Swagger.

## Arquivos gerados

- `API_ENDPOINT_MATRIX.md`
- `API_ENDPOINT_MATRIX.json`

Gerar novamente depois de alterar tools ou Swagger:

```powershell
python scripts\build_endpoint_harness.py --write
```

## Arquivos de apoio

- `PERFORMANCE.md` - benchmarks e tools rapidas.
- `AGENT_ENDPOINT_HARNESS.md` - como usar o harness.
- `N8N_AUTOMATION_ARCHITECTURE.md` - proposta de infraestrutura com n8n/agentes.
- `MIGRATION_v3.0.md` - historico da remocao do modulo Analytics.

## Estado validado

Ultima validacao local documentada:

```powershell
python -m pytest -q
# 176 passed
```

## Importante

O projeto e open source e nao deve carregar regra especifica de uma empresa no codigo principal. Parametros e defaults operacionais devem vir de contexto, `.env` ou configuracao, nao hardcoded.
