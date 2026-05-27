# MCP-Server-Totvs-Moda - Ajustes Pontuais

Lista curta de melhorias identificadas no review do repositorio. Cada item e independente e pode ser feito isoladamente.

Status revisado em 2026-05-27 apos leitura dos docs e do codigo atual.

---

## 1. Auditar historico do Git por credenciais vazadas

**Status:** parcialmente verificado.

Primeira passada local:

```powershell
git log --all --full-history -- .env
# sem commits encontrados para .env
```

Tambem foram verificadas buscas por `client_secret`, `TOTVS_PASSWORD` e `9443`. Nao apareceu `.env` versionado; apareceu URL/porta `9443` em artefatos antigos de Swagger removidos do repositorio publico.

**Proximo passo:** fechar relatorio explicito do que apareceu no historico e confirmar se qualquer URL/credencial associada deve ser considerada exposta.

**Criterio de sucesso:** lista explicita do que esteve exposto + confirmacao de que cada item sensivel foi rotacionado ou classificado como nao-secreto.

---

## 2. Documentar precedencia `.env` vs `env` do MCP config

**Status:** feito no codigo e no README.

Comportamento atual em `server.py`:

- Por padrao, variaveis herdadas pelo processo MCP ganham.
- O `.env` preenche apenas variaveis ausentes.
- Com `TOTVS_DOTENV_OVERRIDE=true`, o `.env` sobrescreve variaveis herdadas.
- `TOTVS_ENV_FILE` permite apontar para um `.env` especifico quando o cliente MCP inicia em outro diretorio.

O README ja recomenda usar `TOTVS_ENV_FILE` + `TOTVS_DOTENV_OVERRIDE=true` para evitar credenciais antigas herdadas pelo cliente MCP.

**Criterio de sucesso:** alguem clonando o repo entende em 30s onde colocar as credenciais.

---

## 3. Marcar tools de escrita com annotations MCP

**Status:** feito para as 7 tools originalmente listadas.

Annotations aplicadas:

```python
{
    "destructiveHint": True,
    "idempotentHint": False,
    "readOnlyHint": False,
    "openWorldHint": True,
}
```

Tools marcadas:

- `totvs_cancel_order`
- `totvs_change_order_status`
- `totvs_update_order_items_price`
- `totvs_update_product_price`
- `totvs_update_promotion_price`
- `totvs_create_or_update_individual_customer`
- `totvs_create_voucher`

**Proximo passo opcional:** expandir annotations para outras tools de escrita adicionadas depois do review inicial, especialmente writes destrutivas de material request, purchase order, accounts receivable e fiscal.

**Criterio de sucesso:** ao inspecionar a tool no cliente, a metadata de escrita/destrutiva aparece.

---

## 4. Pinning de dependencias criticas

**Status:** feito.

Dependencias criticas pinadas com teto em `requirements.txt` e `pyproject.toml`:

```text
mcp>=1.0.0,<2.0.0
httpx>=0.27.0,<0.28.0
```

`python-dotenv` nao foi adicionado porque o projeto nao usa a dependencia; o loader de `.env` e implementado no proprio `server.py`.

**Criterio de sucesso:** `pip install -r requirements.txt` em maquina limpa evita upgrades quebradores de `mcp` 2.x ou `httpx` 0.28+.

---

## 5. Validar `TOTVS_BRANCH_CODES` na inicializacao

**Status:** pendente.

O plano original sugeria validar as filiais configuradas contra `operations[].branches`, mas o cache atual de operations guarda apenas:

```python
{"code": ..., "name": ..., "type": ...}
```

Antes de implementar, e preciso confirmar no payload real de `/api/totvsmoda/general/v2/operations` se as filiais aparecem por operacao. Se nao aparecerem, usar outro endpoint read-only como fonte de verdade.

**Sugestao de implementacao:**

- Manter `TOTVS_BRANCH_CODES` nao fatal.
- Gerar `logger.warning` quando uma filial configurada nao for encontrada na fonte validada.
- Adicionar teste em `tests/test_context_cache.py` com filial invalida.

**Criterio de sucesso:** configurar `TOTVS_BRANCH_CODES=999` gera warning visivel no startup.

---

## 6. Smoke tests minimos para as 7 tools de escrita

**Status:** parcialmente coberto.

Ja existem testes para parte das tools de escrita, incluindo:

- `totvs_cancel_order`
- `totvs_change_order_status`
- `totvs_update_product_price_only`
- compatibilidade de `totvs_update_product_price`

**Proximo passo:** criar/completar `tests/test_writes.py` cobrindo pelo menos as 7 tools listadas neste documento, sem duplicar demais testes existentes.

**Criterio de sucesso:** mudancas em serializacao de body, path ou metodo HTTP quebram teste antes de deploy.

---

## 7. Comentario inline na descoberta de priceTypes/costTypes

**Status:** feito.

`context_cache.py` ja documenta a estrategia de discovery em:

- `_load_price_and_cost_types`
- `_discover_price_types`
- `_discover_cost_types`

**Criterio de sucesso:** docstrings presentes explicando por que o workaround existe.

---

## Resumo de prioridade atual

| # | Item | Status | Proximo passo |
|---|------|--------|---------------|
| 1 | Auditar historico git | Parcial | Fechar relatorio de exposicao |
| 2 | Precedencia `.env` | Feito | Manter README alinhado |
| 3 | Annotations MCP | Feito | Expandir para outras writes depois |
| 4 | Pinning dependencias | Feito | Validar instalacao/testes |
| 5 | Validar BRANCH_CODES startup | Pendente | Confirmar fonte de filiais |
| 6 | Smoke tests writes | Parcial | Completar lacunas |
| 7 | Docstring price/cost discovery | Feito | Sem acao |
