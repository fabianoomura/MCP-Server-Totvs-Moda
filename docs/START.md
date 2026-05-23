# TOTVS Moda MCP — Contexto para Nova Conversa

> Cole este arquivo no início de qualquer nova conversa com Claude para retomar o projeto com contexto completo.

---

## Projeto

**TOTVS Moda MCP Server** — MCP Server (Model Context Protocol) para API V2 do TOTVS Moda.
Permite que LLMs consultem e ajam no ERP TOTVS via linguagem natural.

- **Repo:** https://github.com/fabianoomura/MCP-Server-Totvs-Moda
- **Autor:** Fabiano Omura (MOOUI — textil infantil/cama/casa)
- **Local:** `C:\Users\mooui\mcp-servers\totvs-moda-mcp`
- **Python:** 3.11 | **Instalação:** `pip install -e .`

---

## Estrutura

```
totvs-moda-mcp/
├── server.py              # MCP server, registra todas as tools + ROUTING dict
├── totvs_client.py        # HTTP client OAuth2, retry, error parsing
├── context_cache.py       # Cache de dados de referência (filiais, operações)
├── decode_xml.py          # Utilitário: decodifica XML NF-e base64 → XML legível
├── tools/
│   ├── _defaults.py       # inject_branch_defaults()
│   ├── _fields.py         # apply_fields()
│   ├── _value_types.py    # Tipos de valor
│   ├── aggregators.py     # 5 tools agregadoras (top_customers, sales_summary, etc)
│   ├── sales_order.py     # ~25 métodos (pedidos de venda)
│   ├── product.py         # ~30 métodos (produtos, preços, custos, grades)
│   ├── person.py          # ~12 métodos (clientes PF/PJ, mensagens)
│   ├── accounts_receivable.py  # ~14 métodos (contas a receber, duplicatas)
│   ├── account_payable.py      # 3 métodos (contas a pagar)
│   ├── fiscal.py          # ~10 métodos (NF-e, XML, DANFE, certificados)
│   ├── general.py         # ~10 métodos (CEP, cidades, estados, países)
│   ├── seller.py          # 4 métodos (vendedores, representantes)
│   ├── voucher.py         # 3 métodos (vouchers)
│   ├── purchase_order.py  # 4 métodos (pedidos de compra)
│   ├── logistics.py       # 3 métodos (pacotes, expedição)
│   ├── data_package.py    # 7 métodos (pacotes de dados)
│   ├── image.py           # 6 métodos (imagens de produto/pessoa)
│   ├── other_modules.py   # ProductionOrder, Management, Global
│   ├── convenience.py     # search_customer_by_document, upsert_product_value
│   └── product_engineering.py  # Ficha de consumo (matéria-prima + serviços)
├── tests/                 # pytest + respx (91+ testes)
└── docs/
    ├── START.md           # Este arquivo
    ├── PROJECT_STATE.md   # Estado completo e histórico
    ├── ROADMAP.md         # Plano de fases v3.x
    ├── PATTERNS.md        # Padrões obrigatórios de código
    ├── PERFORMANCE.md     # Benchmarks e tools rapidas
    └── MIGRATION_v3.0.md  # Migração v2.6.1 → v3.0.0
```

---

## Cobertura atual

~135 tools MCP mapeadas cobrindo 18 módulos da API V2. ~215 endpoints adicionais não mapeados (ver ROADMAP.md).

**Versão atual:** v3.1.1 (branch `main`)

---

## Padrões rápidos (detalhes em PATTERNS.md)

1. **Search tools:** `inject_branch_defaults` → build filter (excluir page/pageSize/order/fields) → `apply_fields`
2. **Write tools:** filtro genérico `{k: v for k, v in args.items() if v is not None}` — schema do MCP é o que limita o LLM
3. **Create com fallback:** tenta create → se `AlreadyExist` → fallback update → retorna summary `{total, created, updated}`
4. **Toda tool nova:** precisa de teste, descrição rica, entrada no ROUTING dict

---

## Utilitários

### decode_xml.py — Decodificador de XML NF-e

A API TOTVS retorna XMLs de NF-e em base64. Este script decodifica e formata:

```bash
python decode_xml.py "PD94bWw..."              # imprime formatado no terminal
python decode_xml.py "PD94bWw..." -o nfe.xml   # salva em arquivo
python decode_xml.py -f arquivo_b64.txt        # lê base64 de um arquivo
python decode_xml.py --raw "PD94bWw..."         # sem pretty-print
echo "PD94bWw..." | python decode_xml.py       # via stdin/pipe
```

---

## Configuração MCP (Claude Code)

O server roda via stdio. Config em `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "totvs-moda": {
      "command": "python",
      "args": ["C:/Users/mooui/mcp-servers/totvs-moda-mcp/server.py"],
      "env": {
        "TOTVS_BASE_URL": "https://...",
        "TOTVS_CLIENT_ID": "...",
        "TOTVS_CLIENT_SECRET": "...",
        "TOTVS_USERNAME": "...",
        "TOTVS_PASSWORD": "...",
        "TOTVS_BRANCH_CODES": "1"
      }
    }
  }
}
```

---

## Como usar este arquivo

1. Abra nova conversa com Claude
2. Cole o conteúdo deste START.md
3. Se for implementação, cole também PATTERNS.md e ROADMAP.md
4. Diga o que quer fazer

Exemplo:
> "Retomando o projeto TOTVS Moda MCP. [conteúdo do START.md]. Quero completar o módulo de produtos — vamos auditar gaps contra a API."
