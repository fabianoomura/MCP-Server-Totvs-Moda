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
