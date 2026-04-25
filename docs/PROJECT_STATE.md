# TOTVS Moda MCP Server — Estado do Projeto

> **Este documento é o ponto de partida para qualquer thread futura sobre este projeto.** Cole no início de uma nova conversa com Claude para que ele entenda o contexto completo.

---

## Identificação do projeto

- **Repositório:** https://github.com/fabianoomura/MCP-Server-Totvs-Moda
- **PyPI:** https://pypi.org/project/totvs-moda-mcp/
- **Autor:** Fabiano Omura ([LinkedIn](https://www.linkedin.com/in/fabiano-o-50619734/))
- **Empresa de uso interno:** MOOUI (textil infantil/cama/casa, brasileira)
- **Localização do código:** `C:\Users\mooui\mcp-servers\totvs-moda-mcp`
- **Ambiente:** Windows + PowerShell + VS Code com Copilot Chat (cliente MCP)
- **Versão Python:** 3.11
- **Instalação:** modo editable (`pip install -e .`) — código local é o que roda

---

## O que é o projeto

MCP Server (Model Context Protocol) para a API V2 do TOTVS Moda. Permite que LLMs (Claude, GPT via Copilot, etc.) consultem e ajam no ERP TOTVS via linguagem natural.

**Não é oficial da TOTVS.** É projeto pessoal de um usuário do sistema (Fabiano), aberto sob licença MIT.

**Cobertura atual:** 18 módulos da API V2, ~135 tools mapeadas. Existem ~215 endpoints adicionais não mapeados ainda (ver `ROADMAP.md`).

---

## Histórico de versões

| Versão | Tema | Status |
|--------|------|--------|
| v2.0.0 | Release inicial pelo Fabiano | publicada PyPI |
| v2.1.0–v2.1.6 | Hotfixes (5 bugs críticos, security hardening, robustness) | aplicada |
| v2.2.0 | Suite de testes pytest + CI GitHub Actions | aplicada |
| v2.3.0 | +15 endpoints novos (sales order items, gift checks, etc) | aplicada |
| v2.4.0 | 5 tools agregadoras + descrições ricas | aplicada |
| v2.5.0 | Parâmetro `fields` (redução de tokens em retornos) | aplicada |
| v2.6.0 | Default injection de `branchCode` | aplicada |
| v2.6.1 | Fix logistics + restauração de testes | aplicada |
| **v3.0.0** | **Remoção do módulo Analytics + auditoria** | **em planejamento** |

**Estado atual no GitHub:** branch `main` sincronizada, tag `v2.6.1` aplicada, **91 testes passando**.

---

## Decisões arquiteturais já tomadas

### Arquivos da estrutura

```
totvs-moda-mcp/
├── server.py                  # MCP server, ~1213 linhas, registra todas as tools
├── totvs_client.py           # HTTP client com OAuth2, retry, error parsing
├── context_cache.py          # Cache de dados de referência (filiais, etc)
├── pyproject.toml            # Metadata, deps, version
├── tools/
│   ├── _defaults.py          # inject_branch_defaults() — v2.6
│   ├── _fields.py            # apply_fields() — v2.5
│   ├── aggregators.py        # 5 tools agregadoras — v2.4
│   ├── sales_order.py        # ~25 métodos
│   ├── product.py            # ~30 métodos
│   ├── person.py             # ~12 métodos
│   ├── accounts_receivable.py # ~14 métodos
│   ├── account_payable.py    # 3 métodos (incompleto)
│   ├── fiscal.py             # ~10 métodos
│   ├── analytics.py          # 24 métodos — A SER REMOVIDO em v3.0
│   ├── general.py            # ~10 métodos
│   ├── seller.py             # 4 métodos
│   ├── voucher.py            # 3 métodos
│   ├── purchase_order.py     # 4 métodos
│   ├── logistics.py          # 3 métodos
│   ├── data_package.py       # 7 métodos
│   ├── image.py              # 6 métodos
│   ├── other_modules.py      # ProductionOrder, Management, Global
│   └── convenience.py        # search_customer_by_document, upsert_product_value
└── tests/
    ├── conftest.py
    ├── test_aggregators.py        (8 tests)
    ├── test_defaults.py           (14 tests)
    ├── test_fields.py             (10 tests)
    ├── test_fields_integration.py (2 tests)
    ├── test_new_endpoints_v23.py  (21 tests)
    ├── test_tools_regressions.py  (20 tests)
    └── test_totvs_client.py       (16 tests)
```

### Padrões obrigatórios em qualquer mudança

**1. Toda tool de busca deve aceitar `fields` opcional**
```python
async def search_xxx(self, args):
    args = inject_branch_defaults(args)  # se precisar de branchCode
    excluded = ("page", "pageSize", "order", "fields")
    flt = {k: v for k, v in args.items() if k not in excluded and v is not None}
    body = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
    if args.get("order"):
        body["order"] = args["order"]
    result = await self.client.post(f"{BASE}/...", body)
    return apply_fields(result, args)
```

**2. Toda tool que precisa de `branchCode` deve injetar default**
```python
async def my_tool(self, args):
    args = inject_branch_defaults(args)  # primeira linha
    # ...
```

**3. Toda tool nova precisa ter teste em `tests/`**
- Mock OAuth com `respx`
- Mock endpoint da API com resposta esperada
- Validar shape do retorno e payload enviado

**4. Descrições de tool devem ser ricas**

Não basta "Busca pedidos". Tem que documentar:
- Shape do retorno (campos principais)
- Quando usar vs quando NÃO usar
- Redirecionar para tools melhores quando aplicável
- Mencionar `fields=[...]` como hint de redução de tokens

**5. Métodos Python devem usar filtro genérico (não hardcode de campos)**

```python
# CORRETO (aceita qualquer campo da API):
body = {k: v for k, v in args.items() if v is not None}

# ERRADO (limitado a campos pré-definidos):
body = {"description": args.get("description"), "isActive": args.get("isActive")}
```

### Schema do MCP é o que limita o LLM, não o método Python

Esse é um conceito-chave que apareceu várias vezes:

**O método Python aceita qualquer campo via filtro genérico.** Mas o LLM só sabe usar os campos que estão no `inputSchema` da tool no `server.py`. Se um campo está na API mas não no schema, o LLM não tenta passar.

Isso significa que **adicionar campos ao schema é trabalho cosmético** — não muda lógica, só expõe ao LLM o que já era aceito.

---

## Os 3 pontos pendentes da última thread

### Ponto 1 — `update_product_data` aceita peso (e mais campos)

**Status:** Identificado, **não aplicado ainda**.

**Diagnóstico:**
- `tools/product.py` linha 272-275: método aceita qualquer campo (`{k: v for k, v in args.items() if v is not None}`)
- `server.py` linha ~356-385: schema só expõe `description` e `isActive`

**Solução:** adicionar no `inputSchema` da tool `totvs_update_product_data`:
- `grossWeight` (peso bruto em kg)
- `netWeight` (peso líquido em kg)
- `height` (altura em cm)
- `width` (largura em cm)
- `depth` (profundidade em cm)

E qualquer outro campo que o `product.json` (Postman collection) confirmar que a API aceita.

### Ponto 2 — Analytics em `false` mas tools ainda apareciam

**Status:** ✅ **Resolvido** (variável `TOTVS_ENABLE_ANALYTICS=false` adicionada ao `mcp.json`)

**Decisão para v3.0:** remover o módulo analytics completamente do projeto. Razões:
- Fabiano não contrata o módulo (false no env)
- Maioria dos usuários TOTVS Moda não tem o módulo
- Mantém o projeto mais simples
- Quem precisar pode adicionar via PR depois

### Ponto 3 — Endpoints de Preço (P) e Custo (C) são separados

**Status:** Identificado, precisa investigação.

**Diagnóstico parcial:**
- `update_product_price` e `create_product_value` no projeto atual tratam preço e custo como se fossem o mesmo endpoint
- A API TOTVS tem endpoints separados:
  - Preço de venda (P): `/product/v2/prices` ou similar
  - Custo (C): `/product/v2/costs` ou similar
- Precisa ler `product.json` (Postman collection) pra confirmar URLs exatas

**Solução pendente:** mapear o `product.json` e gerar tools separadas (ou adaptar as existentes para aceitar tipo P/C corretamente).

---

## Configuração de ambiente

### `.env` ou `mcp.json` env block

| Variável | Obrigatória? | Valor MOOUI |
|----------|--------------|-------------|
| `TOTVS_BASE_URL` | sim | `https://www30.bhan.com.br:9443` |
| `TOTVS_CLIENT_ID` | sim | `moouiapiv2` |
| `TOTVS_CLIENT_SECRET` | sim | (sensível) |
| `TOTVS_USERNAME` | sim | `INTEGRACAO` |
| `TOTVS_PASSWORD` | sim | (sensível) |
| `TOTVS_BRANCH_CODES` | recomendada | `1` |
| `TOTVS_ENABLE_ANALYTICS` | opcional | `false` |
| `TOTVS_TIMEOUT` | opcional | `30` |
| `TOTVS_MAX_RETRIES` | opcional | `3` |
| `TOTVS_TLS_VERIFY` | opcional | `true` |

⚠️ **AVISO DE SEGURANÇA:** as credenciais já vazaram no histórico de conversas anteriores (TOTVS_CLIENT_SECRET=7556720068, TOTVS_PASSWORD=654321). **Devem ser trocadas no TOTVS antes de continuar usando o projeto.**

---

## Limitações conhecidas da API TOTVS

Endpoints que **não existem na API V2** (precisam de automação de interface desktop com pyautogui/AutoHotkey):

- **PRDFM164**: informações Web do produto (visão site, SEO, meta tags, dimensões web)
- **DELETE de código de barras**: existe POST mas não DELETE
- **Ficha técnica completa com composições avançadas** (cobertura parcial)

---

## Próximos passos planejados

Ver `ROADMAP.md` para detalhamento. Resumo:

1. **v3.0.0** — Remover módulo analytics (esta thread)
2. **v3.1.0** — Auditoria + completar módulo `product` (preço, custo, peso, classificações)
3. **v3.2.0** — Auditoria + completar módulo `accounts_receivable`
4. **v3.3.0** — Auditoria + completar módulo `accounts_payable`
5. **v3.4.0** — Auditoria + completar módulos restantes (fiscal, person, etc)
6. **v3.5.0** — Documentação consolidada + publicação no PyPI

---

## Como retomar em uma nova thread

1. Cole `PROJECT_STATE.md` (este arquivo) inteiro no início da conversa
2. Cole `ROADMAP.md` se for uma thread de implementação de fase específica
3. Cole o JSON Postman collection do módulo da fase (se houver)
4. Diga qual fase está executando

Exemplo de mensagem de abertura:

> "Estou retomando o projeto MCP Server TOTVS Moda. Segue o estado atual e o roadmap. Quero implementar a v3.1.0 (auditoria + completar módulo `product`). Tenho o `product.json` da API anexado. Vamos começar pela auditoria."

Claude na nova thread terá tudo que precisa pra continuar sem perder contexto.

---

## Documentos relacionados

- `PROJECT_STATE.md` (este arquivo) — estado atual completo
- `ROADMAP.md` — plano por fases
- `MIGRATION_v3.0.md` — migração da v2.6.1 → v3.0.0 (remoção do analytics)
- `PATTERNS.md` — padrões de código que devem ser seguidos
