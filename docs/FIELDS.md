# Glossário de campos — nomes que confundem

A API V2 do TOTVS Moda nem sempre usa o nome de campo "óbvio". Esta página lista
os campos reais das respostas mais consultadas, com foco nos que costumam ser
errados ao usar `fields=[...]`.

> A partir da v3.11, quando um nome em `fields=` não existe na resposta, a tool
> devolve um aviso em `_fieldsWarning` (em vez de simplesmente retornar vazio).

---

## Notas fiscais — `totvs_search_fiscal_invoices`

| Quer | Campo real | Observação |
|------|-----------|-----------|
| Valor da nota | `totalValue` | **não** é `value` |
| Valor dos produtos | `productValue` | |
| Status SEFAZ | `eletronic.electronicInvoiceStatus` | aninhado; valores: `Authorized`, `Canceled`, `Denied`… |
| Chave de acesso | `eletronic.accessKey` | aninhado |
| Nome da operação | `operatioName` | typo herdado da API (sem o 2º "o") |
| Situação da NF | `invoiceStatus` | `Issued`, `Canceled`, `Normal`… |
| Data de emissão | `issueDate` / `invoiceDate` | |

### Itens da NF (`expand=items`)

Os valores **por item** só vêm com `expand=items`, e usam nomes próprios:

| Quer | Campo real |
|------|-----------|
| Valor líquido do item | `items.netValue` |
| Valor unitário líquido | `items.unitNetValue` |
| Valor bruto / unitário bruto | `items.grossValue` / `items.unitGrossValue` |
| Código / descrição | `items.code` / `items.name` |

> `totvs_invoice_360` (visão compacta) **não** traz valor por item — use
> `search_fiscal_invoices` com `expand=items` para os valores.

---

## Contas a receber — `totvs_search_receivable_documents`

| Quer | Campo real |
|------|-----------|
| Valor da parcela | `installmentValue` |
| Valor pago | `paidValue` |
| Vencimento | `expiredDate` |
| Data de liquidação | `settlementDate` (nulo = em aberto) |
| Situação | `status` (1=Normal, 2=Devolvido, 3=Cancelado, 4=Quebrado) |
| Portador | `bearerName` / `bearerCode` |

> Em aberto ≈ `paidValue == 0` e `settlementDate == null`.

---

## Contas a pagar — `totvs_search_payable_duplicates`

| Quer | Campo real |
|------|-----------|
| Valor da duplicata | `duplicateValue` |
| Valor pago | `paidValue` |
| Vencimento | `dueDate` |
| Liquidação | `settlementDate` |
| Despesa / centro de custo | `expense[].expenseName` / `expense[].costCenterCode` |
| Situação | `status` (N=Normal, C=Cancelada, A=Agrupada…) |

---

## Pedidos de venda — `totvs_search_orders`

| Quer | Campo real |
|------|-----------|
| Valor do pedido | `totalValue` |
| Situação | `orderStatus` |
| Itens (`expand=items`) | `items.productCode`, `items.name`, `items.quantity`, `items.price`, `items.totalValue` |

---

## Preços / custos — `totvs_search_product_prices` / `_costs`

| Quer | Campo real |
|------|-----------|
| Preço | `prices[].price` |
| Preço promocional | `prices[].promotionalPrice` |
| Nome da tabela | `prices[].priceName` |
| Custo | `costs[].cost` (com `costs[].costName`) |

---

## Filtros de data

Filtros de período exigem `start < end`. Para "vence hoje", passe a **mesma
data** em início e fim — desde a v3.11 a tool expande automaticamente para o dia
inteiro (`00:00:00`/`23:59:59`). Antes disso, use o horário explícito.
