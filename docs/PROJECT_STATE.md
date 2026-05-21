# TOTVS Moda MCP Server — Estado do Projeto

> **Atualizado em 2026-05-21.** Este documento é o ponto de partida para qualquer thread futura.

---

## Identificação

- **Repositório:** https://github.com/fabianoomura/MCP-Server-Totvs-Moda
- **PyPI:** https://pypi.org/project/totvs-moda-mcp/
- **Autor:** Fabiano Omura — MOOUI (textil infantil/cama/casa, Londrina-PR)
- **Local:** `C:\Users\mooui\mcp-servers\totvs-moda-mcp`
- **Ambiente:** Windows 11 + VS Code + Claude Code (cliente MCP via stdio)
- **Python:** 3.11 | Instalação: `pip install -e .`

---

## O que é

MCP Server para API V2 do TOTVS Moda. Permite que LLMs (Claude, GPT, etc.) consultem e operem no ERP TOTVS via linguagem natural.

**Não é oficial da TOTVS.** Projeto pessoal, open source (MIT).

---

## Versão atual: v3.2.0

**Branch `main` sincronizada com PyPI. 117 testes passando.**

### Histórico de versões

| Versão | Tema | Status |
|--------|------|--------|
| v2.0.0 | Release inicial | publicada |
| v2.1.0–v2.1.6 | Hotfixes, security hardening | aplicada |
| v2.2.0 | Suite de testes pytest + CI | aplicada |
| v2.3.0 | +15 endpoints (sales order items, gift checks, etc) | aplicada |
| v2.4.0 | 5 tools agregadoras + descrições ricas | aplicada |
| v2.5.0 | Parâmetro `fields` (redução de tokens) | aplicada |
| v2.6.0 | Default injection de `branchCode` | aplicada |
| v2.6.1 | Fix logistics + restauração de testes | aplicada |
| v3.0.0 | Remoção do módulo Analytics | aplicada |
| v3.1.0 | context_cache + search_costs + totvs_get_instructions | aplicada |
| v3.1.1 | context_cache fixes + README rewrite | aplicada |
| v3.1.2 | Patches | aplicada |
| **v3.2.0** | **consumption_sheet + fix purchase/production orders** | **atual** |

---

## Cobertura atual

**19 módulos | ~136 tools | 117 testes**

### Estrutura de arquivos

```
totvs-moda-mcp/
├── server.py                    # MCP server, registra tools + ROUTING dict
├── totvs_client.py              # HTTP client OAuth2, retry, error parsing
├── context_cache.py             # Cache de referência (filiais, operações, preços, custos)
├── decode_xml.py                # Utilitário: decodifica XML NF-e base64
├── pyproject.toml               # Metadata, deps, version
├── tools/
│   ├── _defaults.py             # inject_branch_defaults()
│   ├── _fields.py               # apply_fields()
│   ├── _value_types.py          # Resolução de tipos de valor
│   ├── sales_order.py           # ~25 métodos (pedidos de venda)
│   ├── product.py               # ~30 métodos (produtos, preços, custos, grades)
│   ├── product_engineering.py   # Ficha de consumo (matéria-prima + serviços) — v3.2
│   ├── person.py                # ~12 métodos (clientes PF/PJ)
│   ├── accounts_receivable.py   # ~14 métodos (contas a receber)
│   ├── account_payable.py       # 3 métodos (contas a pagar)
│   ├── fiscal.py                # ~10 métodos (NF-e, XML, DANFE)
│   ├── general.py               # ~10 métodos (CEP, cidades, estados)
│   ├── seller.py                # 4 métodos (vendedores, representantes)
│   ├── voucher.py               # 3 métodos
│   ├── purchase_order.py        # 4 métodos (pedidos de compra)
│   ├── logistics.py             # 3 métodos (pacotes, expedição)
│   ├── data_package.py          # 7 métodos
│   ├── image.py                 # 6 métodos (imagens produto/pessoa)
│   ├── other_modules.py         # ProductionOrder, Management, Global
│   ├── aggregators.py           # 5 tools agregadoras
│   └── convenience.py           # search_customer_by_document, upsert_product_value
├── tests/                       # 117 testes (pytest + respx)
└── docs/
    ├── START.md                 # Contexto rápido para novas conversas
    ├── PROJECT_STATE.md         # Este arquivo
    ├── ROADMAP.md               # Plano de fases
    └── PATTERNS.md              # Padrões obrigatórios de código
```

---

## Bugs corrigidos na v3.2.0

| Módulo | Bug | Fix |
|--------|-----|-----|
| purchase_order | API exige `branchCodeList` (array), tool enviava `branchCode` (int) | Conversão automática no método Python |
| production_order | Mesmo bug de `branchCode` vs `branchCodeList` | Mesmo fix |
| production_order | Schema declarava `statusList` como `string[]`, API espera `integer[]` | Corrigido + documentado (20=Andamento, 30=Finalizada, 40=Aberta) |

---

## Pontos pendentes conhecidos

### 1. Schema de `update_product_data` incompleto
- Método Python aceita qualquer campo, mas schema só expõe `description` e `isActive`
- Faltam: `grossWeight`, `netWeight`, `height`, `width`, `depth`
- **Ação:** expandir schema no server.py

### 2. ~215 endpoints da API V2 ainda não mapeados
- Maior gap: módulos Person (~28 faltam), Fiscal (~15), Sales Order (~10)
- Menor gap: Product (quase completo), Accounts Receivable (razoável)

### 3. Ordens de produção/compra com histórico aberto
- 1.426 PCs "Open" (muitas desde 2021 — provavelmente deveriam ser fechadas/canceladas)
- 62 OPs status 40 (Aberta) antigas sem movimentação

---

## Plano de finalização — Junho/2026

**Meta:** completar cobertura dos módulos principais e publicar versão estável até fim de junho/2026.

### Fases restantes

| Fase | Módulo | Gap estimado | Prioridade |
|------|--------|-------------|------------|
| v3.3 | Product — expandir schemas + campos faltantes | ~10 endpoints | Alta |
| v3.4 | Person — CRUD endereços, telefones, e-mails | ~28 endpoints | Alta |
| v3.5 | Fiscal — CCe, inutilização, SPED | ~15 endpoints | Média |
| v3.6 | Accounts Receivable — renegociação, adiantamento | ~11 endpoints | Média |
| v3.7 | Accounts Payable — completar CRUD | ~7 endpoints | Média |
| v3.8 | Sales Order — liberação, reserva, kits | ~10 endpoints | Média |
| v3.9 | Módulos pequenos consolidados (voucher, seller, logistics, etc) | ~15 endpoints | Baixa |
| v4.0 | Documentação final + release estável PyPI | — | Final |

**Cada fase pode ser feita em 1-2 sessões com Claude.** Total estimado: ~10 sessões ao longo de junho.

---

## Padrões obrigatórios (resumo)

Detalhes completos em `PATTERNS.md`. Resumo:

1. **Search tools:** `inject_branch_defaults` → filtro genérico (excluir page/pageSize/order/fields) → `apply_fields`
2. **Write tools:** filtro genérico `{k: v for k, v in args.items() if v is not None}`
3. **Create com fallback:** tenta create → se `AlreadyExist` → update → summary `{total, created, updated}`
4. **Schema do MCP limita o LLM**, não o método Python — expandir schema é cosmético
5. **Toda tool nova:** teste + descrição rica + entrada no ROUTING
6. **API gotcha:** vários endpoints exigem `branchCodeList` (array), não `branchCode` (int) — sempre converter

---

## Limitações da API TOTVS V2

Endpoints que **não existem** na API (precisam de automação desktop):
- **PRDFM164**: informações Web do produto (SEO, meta tags, dimensões web)
- **DELETE de código de barras**: só existe POST
- **Ficha técnica avançada**: cobertura parcial (consumption-sheet resolve parte)

---

## Como retomar em nova conversa

1. Cole `docs/START.md` (versão curta) ou este `PROJECT_STATE.md` (versão completa)
2. Se for implementação de fase, cole também `PATTERNS.md`
3. Diga qual fase/módulo quer trabalhar

> "Retomando o projeto TOTVS Moda MCP v3.2.0. Quero completar o módulo Person (fase v3.4). Vamos auditar gaps contra a API."

---

## Documentos relacionados

- `docs/START.md` — contexto rápido para novas conversas
- `docs/PATTERNS.md` — padrões obrigatórios de código
- `docs/ROADMAP.md` — roadmap original (referência histórica, substituído pela seção "Plano de finalização" acima)
