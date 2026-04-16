# TOTVS Moda MCP — Instruções de desenvolvimento

## Padrão para endpoints de escrita

### Create → fallback para Update
Ao implementar um endpoint de **inclusão** (create/incluir), sempre tratar o caso em que o registro já existe:

1. Tenta o endpoint de **create** (`/create`, `/incluir`)
2. Se retornar erro `AlreadyExist`, busca o endpoint equivalente de **update** (`/update`, `/alterar`) no mesmo path
3. Executa o update para os registros que já existiam
4. Retorna um `summary` com `{total, created, updated}` para rastreabilidade

**Exemplo aplicado:** `classification-relationship/create` → fallback para `classification-relationship/update`

### Summary
Todo método de escrita em lote deve retornar um objeto `summary` indicando quantos registros foram criados, atualizados ou falharam. Facilita conferência sem precisar inspecionar o payload completo.
