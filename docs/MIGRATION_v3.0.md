# Manual de migração v2.6.1 → v3.0.0

> Esta versão **remove o módulo Analytics** do projeto. É a única mudança da v3.0.0.

---

## Por que remover?

1. **Analytics é módulo opcional do TOTVS.** A maioria dos usuários do TOTVS Moda não contrata.
2. **Quem não tem o módulo recebe 401/403.** Tools aparecem disponíveis mas não funcionam.
3. **Polui a lista vista pelo LLM.** 24 tools que ninguém usa.
4. **Aumenta tokens do system prompt** desnecessariamente.

Quem precisar de analytics no futuro pode contribuir via PR ou manter um fork.

---

## O que muda

### Arquivos REMOVIDOS

- `tools/analytics.py` — apagar inteiro

### Arquivos MODIFICADOS

**`server.py`:**
- Remover import `from tools.analytics import AnalyticsTools`
- Remover entrada `"analytics": AnalyticsTools(c)` em `get_modules()`
- Remover bloco condicional `*([] if not ANALYTICS_ENABLED else [...])` com 24 tools
- Remover variável `ANALYTICS_ENABLED` e seu `os.getenv` no topo
- Remover entradas do ROUTING relacionadas a analytics (24 entradas)
- Atualizar versão pra 3.0.0
- Atualizar header do arquivo (era "16 módulos | 135 tools", vira "15 módulos | ~111 tools")

**`pyproject.toml`:**
- `version = "3.0.0"`

**`README.md`:**
- Remover menção de analytics da lista de módulos
- Remover variável `TOTVS_ENABLE_ANALYTICS` da tabela de configuração

**`CHANGELOG.md`:**
- Adicionar seção v3.0.0 explicando a remoção

### Arquivos CRIADOS (documentação)

- `docs/PROJECT_STATE.md` — estado completo do projeto
- `docs/ROADMAP.md` — planejamento das próximas fases
- `docs/PATTERNS.md` — padrões obrigatórios

---

## Etapa a etapa

### Etapa 1 — Backup

```powershell
cd C:\Users\mooui\mcp-servers\totvs-moda-mcp
git status   # confirmar que está limpo (nada pendente)
git checkout -b v3.0.0-cleanup   # criar branch nova pra a mudança
```

### Etapa 2 — Apagar analytics.py

```powershell
Remove-Item tools\analytics.py
```

Confirmar que sumiu:

```powershell
Test-Path tools\analytics.py
# False
```

### Etapa 3 — Editar server.py

Abre `server.py` e faça **6 mudanças**:

**3a. Remover import (linha ~25 aproximadamente):**

```python
# REMOVER ESTA LINHA:
from tools.analytics import AnalyticsTools
```

**3b. Remover do get_modules() (linha ~70 aproximadamente):**

```python
def get_modules() -> dict[str, Any]:
    global _modules
    if not _modules:
        c = get_client()
        _modules = {
            "sales_order": SalesOrderTools(c),
            "product": ProductTools(c),
            "person": PersonTools(c),
            "accounts_receivable": AccountsReceivableTools(c),
            "fiscal": FiscalTools(c),
            # REMOVER ESTA LINHA:  "analytics": AnalyticsTools(c),
            "general": GeneralTools(c),
            ...
        }
    return _modules
```

**3c. Remover variável ANALYTICS_ENABLED e o log (linhas ~95-100):**

```python
# REMOVER ESTAS 4 LINHAS:
ANALYTICS_ENABLED: bool = os.getenv("TOTVS_ENABLE_ANALYTICS", "true").lower() not in ("false", "0", "no")

if not ANALYTICS_ENABLED:
    logger.info("Analytics module DISABLED (TOTVS_ENABLE_ANALYTICS=false)")
```

**3d. Remover bloco condicional de tools de analytics:**

Procurar por este bloco e **remover inteiro** (são 24 tools, ~80 linhas):

```python
# REMOVER ESTE BLOCO INTEIRO:
*([] if not ANALYTICS_ENABLED else [
    types.Tool(name="totvs_search_fiscal_movement", ...),
    types.Tool(name="totvs_search_product_fiscal_movement", ...),
    # ... 22 outras tools ...
    types.Tool(name="totvs_search_seller_pending_conditionals", ...),
]),  # end analytics block
```

**3e. Remover entradas do ROUTING:**

Procurar por entradas começando com:

```python
# REMOVER TODAS ESTAS LINHAS DO ROUTING:
"totvs_search_fiscal_movement": ("analytics", "search_fiscal_movement"),
"totvs_search_product_fiscal_movement": ("analytics", "search_product_fiscal_movement"),
"totvs_search_person_fiscal_movement": ("analytics", "search_person_fiscal_movement"),
"totvs_search_seller_fiscal_movement": ("analytics", "search_seller_fiscal_movement"),
"totvs_search_payment_fiscal_movement": ("analytics", "search_payment_fiscal_movement"),
"totvs_search_representative_fiscal_movement": ("analytics", "search_representative_fiscal_movement"),
"totvs_search_buyer_fiscal_movement": ("analytics", "search_buyer_fiscal_movement"),
"totvs_search_operation_fiscal_movement": ("analytics", "search_operation_fiscal_movement"),
"totvs_search_best_selling_products": ("analytics", "search_best_selling_products"),
"totvs_search_sales_by_hour": ("analytics", "search_sales_by_hour"),
"totvs_search_sales_by_weekday": ("analytics", "search_sales_by_weekday"),
"totvs_search_total_receivable": ("analytics", "search_total_receivable"),
"totvs_search_total_payable": ("analytics", "search_total_payable"),
"totvs_search_top_customers": ("analytics", "search_top_customers"),
"totvs_search_top_debtors": ("analytics", "search_top_debtors"),
"totvs_search_financial_income_statement": ("analytics", "search_financial_income_statement"),
"totvs_search_biweekly": ("analytics", "search_biweekly"),
"totvs_search_top_suppliers": ("analytics", "search_top_suppliers"),
"totvs_search_seller_panel_totals": ("analytics", "search_seller_panel_totals"),
"totvs_search_seller_top_customers": ("analytics", "search_seller_top_customers"),
"totvs_search_seller_period_birthday": ("analytics", "search_seller_period_birthday"),
"totvs_search_seller_sales_target": ("analytics", "search_seller_sales_target"),
"totvs_search_customer_purchased_products": ("analytics", "search_customer_purchased_products"),
"totvs_search_seller_pending_conditionals": ("analytics", "search_seller_pending_conditionals"),
```

**Atenção:** uma das tools `totvs_search_top_customers` foi reaproveitada no v2.4 como tool agregadora própria, em `aggregators.py`. Confirmar que **só está sendo removida a referência ao módulo `analytics`**, não a entrada nova:

```python
# MANTER (esta é a tool nova v2.4 do aggregators):
"totvs_top_customers": ("aggregators", "top_customers"),

# REMOVER (esta é a versão velha do analytics):
"totvs_search_top_customers": ("analytics", "search_top_customers"),
```

**3f. Atualizar versão e header:**

No topo do arquivo:

```python
"""
TOTVS Moda MCP Server v3.0.0
============================
MCP server para API V2 do TOTVS Moda.
15 módulos | ~111 tools | OAuth2 ROPC

Author: ATL4S
"""
```

E no `main()`:

```python
logger.info(f"TOTVS Moda MCP Server v3.0 — {len(TOOLS)} tools | {len(get_modules())} módulos")

# E:
InitializationOptions(
    server_name="totvs-moda-mcp",
    server_version="3.0.0",
    ...
)
```

### Etapa 4 — Editar pyproject.toml

```toml
[project]
name = "totvs-moda-mcp"
version = "3.0.0"   # antes era 2.6.1
```

### Etapa 5 — Editar README.md

Procurar e remover/ajustar:

**Na lista de módulos** (provavelmente perto do início):

```markdown
- **Analytics** (se sua empresa tem o módulo contratado): ...
```

Remover essa linha completa.

**Na tabela de variáveis de ambiente:**

```markdown
| `TOTVS_ENABLE_ANALYTICS` | `true` | Desabilita o módulo Analytics... |
```

Remover essa linha.

### Etapa 6 — Atualizar CHANGELOG.md

Adicionar no topo:

```markdown
## [3.0.0] — 2026-04-24

### Removido
- Módulo Analytics completo (24 tools)
- Variável de ambiente `TOTVS_ENABLE_ANALYTICS` (não tem mais função)

### Razão da remoção
Analytics é módulo opcional do TOTVS Moda — a maioria dos usuários não contrata. Manter no projeto adicionava 24 tools que aparecem no LLM mas retornam 401/403, pollu a interface, e gera consumo desnecessário de tokens no system prompt.

Quem precisar de analytics pode contribuir via PR ou manter um fork.

### Migração
Se você tem `TOTVS_ENABLE_ANALYTICS` no seu `.env` ou `mcp.json`, pode remover. Não tem mais efeito.

Nenhuma outra mudança. Tools dos demais 15 módulos continuam idênticas.

### Documentação adicionada
- `docs/PROJECT_STATE.md` — estado consolidado do projeto
- `docs/ROADMAP.md` — plano de evolução
- `docs/PATTERNS.md` — padrões obrigatórios
```

### Etapa 7 — Adicionar pasta docs/

```powershell
New-Item -ItemType Directory -Path docs -Force
Copy-Item /caminho/v3.0.0_delivery/docs/PROJECT_STATE.md docs\
Copy-Item /caminho/v3.0.0_delivery/docs/ROADMAP.md docs\
Copy-Item /caminho/v3.0.0_delivery/docs/PATTERNS.md docs\
```

### Etapa 8 — Validar

```powershell
# Sintaxe Python ok
python -m py_compile server.py
python -m py_compile tools\sales_order.py

# Suite de testes ainda passa
$env:PYTHONPATH = "."
python -m pytest tests/ -v

# Esperado: 91 passed (mesmo número que v2.6.1, porque analytics não tinha testes)
```

Se algum teste quebrou: provavelmente removeu coisa demais. Reverte com `git checkout server.py` e tenta de novo com mais cuidado.

### Etapa 9 — Reinstalar editable e reiniciar VS Code

```powershell
pip install -e .
```

Verificar versão:

```powershell
pip show totvs-moda-mcp
# Version: 3.0.0
```

Fechar VS Code completamente e reabrir.

### Etapa 10 — Commit, push, tag

```powershell
git add tools/
git add server.py pyproject.toml README.md CHANGELOG.md docs/
git status   # revisar mudanças

git commit -m "v3.0.0: remove analytics module

- Removed tools/analytics.py (24 tools)
- Removed conditional analytics block from server.py
- Removed TOTVS_ENABLE_ANALYTICS env var (no longer needed)
- Added docs/ with PROJECT_STATE, ROADMAP, PATTERNS
- Bumped to 3.0.0 (major version because of removal)

Analytics is an optional TOTVS module that most users don't have.
Keeping the tools in the project caused 401/403 errors and bloated
the LLM context. Removed cleanly. Future contributors can add it
back via PR if needed."

git push origin v3.0.0-cleanup
```

Voltar pro main e merge:

```powershell
git checkout main
git merge v3.0.0-cleanup
git push origin main

git tag v3.0.0
git push origin v3.0.0
```

### Etapa 11 — Atualizar o `mcp.json` (opcional)

Se você tem `TOTVS_ENABLE_ANALYTICS` no seu `mcp.json`, pode remover (não causa erro mas não tem mais efeito):

```json
"env": {
    "TOTVS_BASE_URL": "...",
    "TOTVS_CLIENT_ID": "...",
    "TOTVS_CLIENT_SECRET": "...",
    "TOTVS_USERNAME": "...",
    "TOTVS_PASSWORD": "...",
    "TOTVS_BRANCH_CODES": "1"
    // TOTVS_ENABLE_ANALYTICS removido — não usado mais
}
```

### Etapa 12 — Publicar no PyPI (opcional)

```powershell
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue
hatch build
twine check dist/*
twine upload dist/*
```

---

## Validação final

No Copilot Chat, em Agent mode, pergunte:

> "Liste tools do servidor totvs-moda que tenham 'fiscal_movement', 'sales_by_hour', 'top_debtors' ou 'financial_income_statement'."

Resposta esperada: nenhuma encontrada.

> "Quantas tools do totvs-moda estão disponíveis?"

Resposta esperada: ~111 (era ~135).

---

## Tempo estimado

30-45 minutos. Mecânico. Maior parte do tempo é localizar os blocos certos no `server.py`.

## Se algo der errado

- **Teste falha em `test_aggregators.py`:** removeu sem querer alguma tool de aggregator. `git diff` pra ver.
- **Erro de import no startup:** removeu o `from tools.analytics` mas esqueceu de remover algum uso. Procurar `AnalyticsTools` no `server.py` e ver se sobrou.
- **Tools de analytics ainda aparecem:** VS Code não reiniciou de verdade. Fechar todas as janelas e reabrir.
- **`TOTVS_ENABLE_ANALYTICS` tá quebrando alguma coisa:** rebuild da v3.0 sem essa variável era pra ser idempotente. Se quebrar, abrir issue.
