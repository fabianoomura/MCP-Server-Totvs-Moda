# TOTVS Moda MCP Server — Roadmap

> Plano de evolução do projeto da v3.0 em diante. Cada fase é uma thread separada com Claude.

---

## Visão geral

A API V2 do TOTVS Moda tem aproximadamente **350 endpoints**. O projeto atual mapeia ~135. A v3.x amplia gradualmente a cobertura, com 4-6 fases que podem ser executadas em qualquer ordem (por prioridade do uso).

Cada fase é independente — pode ser feita em uma thread separada sem precisar das outras.

---

## v3.0.0 — Limpeza estrutural (esta thread)

**Objetivo:** remover o módulo Analytics do projeto.

**Razão:** Analytics é módulo opcional do TOTVS, não vem por padrão. Manter no projeto adiciona 24 tools que a maioria dos usuários nunca usa, polui a lista vista pelo LLM, e gera erros 401/403 quando o LLM tenta usar sem o módulo contratado.

**Decisão:** quem precisar de analytics no futuro pode contribuir via PR ou fork. O projeto principal foca no que a maioria das empresas tem.

**Mudanças:**
- Remover `tools/analytics.py`
- Remover bloco condicional de analytics do `server.py`
- Remover variável `TOTVS_ENABLE_ANALYTICS` (não precisa mais)
- Remover entradas do ROUTING para tools de analytics
- Remover import `AnalyticsTools` do `server.py`
- Documentar a remoção no CHANGELOG e README
- Bump para v3.0.0 (major bump por remoção de funcionalidade)

**Testes:** suite continua em 91 passing (analytics não tinha testes específicos).

**Estimativa:** 1 thread, 30-45 min.

---

## v3.1.0 — Módulo Product completo

**Objetivo:** ampliar cobertura do módulo Product de ~30 para ~80 endpoints + corrigir gaps conhecidos.

**Pontos pendentes que entram aqui:**

1. **Adicionar campos no schema de `update_product_data`:**
   - `grossWeight`, `netWeight`, `height`, `width`, `depth`
   - Outros campos que o `product.json` revelar

2. **Separar Preço (P) e Custo (C):**
   - Identificar endpoints distintos pra preço de venda vs custo
   - Criar tools separadas: `totvs_search_product_prices` (já existe) vs `totvs_search_product_costs`
   - Mesma coisa pra updates: `update_product_price` vs `update_product_cost`

3. **Endpoints de classificação completos:**
   - `update_classification_type`
   - `delete_classification_type`
   - `link_classifications_to_products` (lote)

4. **Endpoints de cor, grade, batch que faltam**

5. **Composição de produto (ficha técnica):**
   - Cobertura é parcial hoje. Mapear o que é viável via API.

**Pré-requisitos:**
- Ler `product.json` (Postman collection, 376 KB) inteiro
- Comparar com `tools/product.py` atual (linha por linha)
- Identificar gaps

**Entregáveis:**
- Pacote zip com tools/product.py atualizado
- server.py com schemas novos/atualizados
- Testes para cada endpoint novo
- Manual de aplicação

**Estimativa:** 2-3 threads, 4-6 horas total.

---

## v3.2.0 — Módulo Accounts Receivable completo

**Objetivo:** ampliar cobertura de ~14 para ~25 endpoints.

**Endpoints conhecidos faltantes:**
- `settle_invoice` (liquidação)
- `renegotiate_invoices`
- `create_invoice` (inclusão direta)
- `pay_invoices` (lote)
- Vários endpoints de gift_check
- Operações de adiantamento e crédito
- Cancelamento de faturas

**Pré-requisitos:**
- Ler `accounts_receivable.json` (160 KB)
- Comparar com `tools/accounts_receivable.py`

**Estimativa:** 1-2 threads.

---

## v3.3.0 — Módulo Accounts Payable completo

**Objetivo:** ampliar cobertura de 3 para ~10 endpoints.

**Status atual:** subdimensionado. Tem só search de duplicatas, search de comissões pagas e create de duplicata. Falta:
- `update_duplicate`
- `cancel_duplicate`
- `pay_duplicate` (liquidação)
- `change_duplicate_charge_type`
- Outros que o JSON revelar

**Pré-requisitos:**
- Ler `account_payable.json` (67 KB)

**Estimativa:** 1 thread.

---

## v3.4.0 — Módulo Fiscal completo

**Objetivo:** ampliar cobertura de ~10 para ~25 endpoints.

**Status atual:** parcial. Tem search/get básico de NF-e. Falta:
- Inutilização de NF-e (cancelamento)
- Carta de correção (CCe)
- Manifestação adicional (já tem 1)
- Reimpressão
- Exportação SPED

**Pré-requisitos:**
- Ler `fiscal.json` (153 KB)

**Estimativa:** 1-2 threads.

---

## v3.5.0 — Módulo Person completo

**Objetivo:** ampliar cobertura de ~12 para ~40 endpoints.

**Endpoints faltantes prováveis:**
- Endereços do cliente (CRUD)
- Telefones (CRUD)
- E-mails (CRUD)
- Bancos do cliente
- Histórico de mudanças
- Importação em lote
- Bloqueio/desbloqueio

**Pré-requisitos:**
- Ler `person.json` (212 KB)

**Estimativa:** 2 threads.

---

## v3.6.0 — Módulo Sales Order endpoints faltantes

**Objetivo:** completar gaps após o salto da v2.3.

**Endpoints prováveis:**
- Liberação de pedido bloqueado
- Reserva manual de itens
- Composição/edição de kit
- Acompanhamento de logística (timeline)

**Pré-requisitos:**
- Ler `pedido_venda.json` (252 KB)

**Estimativa:** 1-2 threads.

---

## v3.7.0 — Módulos pequenos consolidados

Combinando em uma única release:
- `purchase_order` — completar
- `production_order` — completar
- `voucher` — completar
- `seller` — completar
- `image` — completar
- `data_package` — completar
- `general` — completar

**Estimativa:** 2-3 threads.

---

## v3.8.0 — Documentação + PyPI release

**Objetivo:** consolidar tudo, atualizar README, publicar versão major no PyPI.

- README atualizado com todas as novas tools
- CHANGELOG completo
- Exemplos de uso atualizados
- Build e upload no PyPI
- Tag `v3.8.0` no GitHub
- Anúncio no LinkedIn (se Fabiano quiser)

**Estimativa:** 1 thread.

---

## Como executar uma fase em thread nova

### Mensagem de abertura padrão

```
Estou retomando o projeto MCP Server TOTVS Moda.

Estado atual: [colar conteúdo de PROJECT_STATE.md]

Roadmap: [colar conteúdo de ROADMAP.md]

Padrões: [colar conteúdo de PATTERNS.md]

Quero executar a fase v3.X.0 (descrição da fase).

Tenho anexado o JSON Postman collection do módulo: [arquivo].
```

### Anexos necessários por fase

| Fase | JSON necessário | Tamanho |
|------|----------------|---------|
| v3.1 product | product.json | 376 KB |
| v3.2 receivable | accounts_receivable.json | 160 KB |
| v3.3 payable | account_payable.json | 67 KB |
| v3.4 fiscal | fiscal.json | 153 KB |
| v3.5 person | person.json | 212 KB |
| v3.6 sales order | pedido_venda.json | 252 KB |
| v3.7 small modules | múltiplos JSONs | ~200 KB total |

---

## Princípios para todas as fases

**Manter retrocompatibilidade.** Tools existentes não devem mudar de nome ou parâmetros required. Adições são bem-vindas, mudanças não.

**Aplicar os 3 padrões da v2.4-v2.6:**
- `apply_fields` em tools de busca
- `inject_branch_defaults` em tools que precisam de branchCode
- Descrições ricas com hint de fields e redirecionamento

**Cada endpoint novo precisa de teste.** Sem exceção.

**Bump de versão só major (3.x.0).** Patches e minor (3.x.y) são reservados pra hotfixes.

**MOOUI não vaza.** Nenhuma fase deve introduzir lógica específica da MOOUI no código público. Se aparecer caso de uso interno, vira script privado, não entra no projeto.

---

## Princípios para retomar em qualquer thread

1. Sempre cole `PROJECT_STATE.md` no início
2. Sempre cole `ROADMAP.md` se for fase específica
3. Sempre cole `PATTERNS.md` antes de pedir código
4. Diga claramente qual fase está executando
5. Se for fase de auditoria, anexe o JSON do módulo

Sem esses 4 passos, Claude na thread nova não vai ter contexto e vai inventar coisa.
