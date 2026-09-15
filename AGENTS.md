# TOTVS Moda MCP — Instruções de desenvolvimento

## Convenções de DX (v3.11+)

Padrões adotados para tornar as respostas mais úteis a um LLM. Ao criar/alterar tools, seguir:

- **Saída de arquivos grandes** — payloads binários (PDF/imagem) não devem voltar como base64 inline (estoura o limite de tokens). Use `tools/_output.py`: `save_base64()` grava na pasta resolvida por `resolve_output_dir()` (`TOTVS_OUTPUT_DIR` → Downloads → home → temp) e retorna o caminho. Exponha uma flag `returnBase64` para o conteúdo cru. Aplicado em `get_danfe` e `search_product_images`.
- **Filtros de data de "dia"** — em buscas com `start*/end*Date`, chame `tools/_dates.normalize_day_ranges(args)` logo após `inject_branch_defaults`. Uma data única (start == end, date-only) é expandida para o dia inteiro, contornando o `GeneralGreaterThan` da API.
- **Validação de `fields=`** — `apply_fields` anexa `_fieldsWarning` quando um nome não casa com a resposta (em vez de retornar vazio). Mantenha `pick_fields` puro; a validação fica no wrapper. Campos que confundem ficam em `docs/FIELDS.md` — atualize lá ao descobrir novos.
- **Contas a receber (venda x recebimento)** — `billingType` separa o lado venda (1/2 = a receber) do recebimento/caixa (3/4). Nunca some os dois. O opt-in `withStatusFlags` marca `billingSide`/`isOpen`/`isSettled`/`openValue` e devolve `receivableSummary {open, settled, receiptSide}`.
- **Visões compactas (`*_360`)** — quando a fonte de produtos não traz valores (ex.: `/invoice-products/search`), enriqueça a partir dos itens da nota (`expand=items`, `netValue`/`unitNetValue`) antes de retornar.

Documentação destas convenções vive em 3 lugares (manter sincronizado ao mudar comportamento): descrição das tools em `tools/*.py`, guia em `server._build_instructions()` / `_build_connect_instructions()`, e `docs/FIELDS.md`.

---

## Padrão para endpoints de escrita

Escritas exigem `TOTVS_ENABLE_WRITES=true` no processo do servidor e confirmação
operacional antes/depois. O perfil `completo` e `TOTVS_TOOLS_EXTRA` não anulam a trava.
Declarar mutações com aviso `⚠️ ESCRITA` e `readOnlyHint=False`; tools legadas com
aviso na descrição também são tratadas como escrita. A trava não é teto monetário.

### Create → fallback para Update
Ao implementar um endpoint de **inclusão** (create/incluir), sempre tratar o caso em que o registro já existe:

1. Tenta o endpoint de **create** (`/create`, `/incluir`)
2. Se retornar erro `AlreadyExist`, busca o endpoint equivalente de **update** (`/update`, `/alterar`) no mesmo path
3. Executa o update para os registros que já existiam
4. Retorna um `summary` com `{total, created, updated}` para rastreabilidade

**Exemplo aplicado:** `classification-relationship/create` → fallback para `classification-relationship/update`

### Summary
Todo método de escrita em lote deve retornar um objeto `summary` indicando quantos registros foram criados, atualizados ou falharam. Facilita conferência sem precisar inspecionar o payload completo.

---

## Schema do ProductFilterModel (product/v2)

Campos disponíveis no objeto `filter` dos endpoints de produto:

```
productCodeList         integer[]   Códigos internos de produto
referenceCodeList       string[]    Códigos de referência
productName             string      Descrição do produto
groupCodeList           string[]    Códigos de grupo (último nível da referência)
startProductCode        integer     Código inicial (intervalo)
endProductCode          integer     Código final (intervalo)

classifications         array       Filtro por classificação
  type                  integer     Código do tipo de classificação
  codeList              string[]    Códigos da classificação

branchInfo              object      Filtro por dados da filial
  branchCode            integer     Código da filial (obrigatório neste filtro)
  isActive              boolean     Produto ativo
  isFinishedProduct     boolean     Produto acabado
  isRawMaterial         boolean     Matéria-prima
  isBulkMaterial        boolean     Material de consumo
  isOwnProduction       boolean     Produção própria

hasPrice                boolean     Possui preço cadastrado
  branchPriceCodeList   integer[]   Filiais do preço
  priceCodeList         integer[]   Tipos de preço

hasCost                 boolean     Possui custo cadastrado
  branchCostCodeList    integer[]   Filiais do custo
  costCodeList          integer[]   Tipos de custo

hasPriceTableItem       boolean     Possui item em tabela de preço
  branchPriceTableCodeList integer[] Filiais
  priceTableCodeList    integer[]   Tabelas de preço

hasStock                boolean     Possui saldo em estoque
  branchStockCode       integer     Filial
  stockCode             integer     Tipo de saldo

hasWebInfo              boolean     Possui dados de e-commerce

change                  object      Filtro por data de alteração
  startDate / endDate   datetime    Intervalo de alteração
  inProduct             boolean     Alteração no cadastro do produto
  inPrice               boolean     Alteração de preço
  inCost                boolean     Alteração de custo
  inStock               boolean     Alteração de saldo
  inWebInfo             boolean     Alteração de dados web
  (+ outros flags de alteração por módulo)
```

### PriceTableOptionModel (obrigatório em price-tables/search)
```
branchCodeList*   integer[]   Lista de filiais (obrigatório)
priceTableCode*   integer     Código da tabela de preço (obrigatório)
```

> **Nota:** `branchCode` não é campo direto de `ProductFilterModel`. Filtragem por filial é feita via `branchInfo.branchCode` (dados cadastrais) ou nos campos específicos de preço/custo/saldo.
