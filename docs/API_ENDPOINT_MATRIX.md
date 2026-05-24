# API Endpoint Harness

Generated from `json/*.json` by `scripts/build_endpoint_harness.py`.

- Total endpoints: 251
- Mapped in MCP tools: 169
- Read endpoints: 150
- Write/destructive endpoints: 101

Priority follows the current implementation plan: sales order, fiscal, accounts payable, accounts receivable, product, then the remaining areas.

## API Sales Order

- Source files: pedido de venda.json
- Endpoints: 26
- Mapped: 23

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/sales-order/v2/additional-items` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/additional-order` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/b2c-orders` | write_post | write | yes | - | - |
| DELETE | `/api/totvsmoda/sales-order/v2/batch-items` | write_delete | destructive | yes | - | - |
| GET | `/api/totvsmoda/sales-order/v2/batch-items` | read_get_query | read | yes | order,page | - |
| GET | `/api/totvsmoda/sales-order/v2/billing-suggestions` | read_get_query | read | yes | expand,order,page | - |
| POST | `/api/totvsmoda/sales-order/v2/cancel-items` | write_post | destructive | yes | - | - |
| GET | `/api/totvsmoda/sales-order/v2/changed-batch-items` | read_get_query | read | yes | - | - |
| GET | `/api/totvsmoda/sales-order/v2/classifications` | read_get_query | read | yes | page | - |
| GET | `/api/totvsmoda/sales-order/v2/discount-type` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/sales-order/v2/header` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/sales-order/v2/invoices` | read_get_query | read | yes | - | - |
| DELETE | `/api/totvsmoda/sales-order/v2/items` | write_delete | destructive | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/items` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/observations-order` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/orders/cancel` | write_post | destructive | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/orders/change-status` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/orders/search` | read_post_search | read | yes | filter,expand,order,page | items,invoices,shippingAddress,observations,invoiceObservations,representativeObservations,classifications,discounts,commissioneds,counts |
| POST | `/api/totvsmoda/sales-order/v2/pdv-transactions` | write_post | write | no | - | - |
| GET | `/api/totvsmoda/sales-order/v2/pending-items` | read_get_query | read | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/price-items` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/quantity-items` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/relationship-batch-items` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/sales-order/v2/relationship-counts` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/shipping-order` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/sales-order/v2/suggest-batch-items-nuance` | write_post | write | no | - | - |

## API Fiscal

- Source files: fiscal.json
- Endpoints: 11
- Mapped: 11

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| GET | `/api/totvsmoda/fiscal/v2/cost-center` | read_get_query | read | yes | page | - |
| POST | `/api/totvsmoda/fiscal/v2/danfe-search` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/fiscal/v2/digital-certificates` | read_get_query | read | yes | - | - |
| POST | `/api/totvsmoda/fiscal/v2/invoice-products/search` | read_post_search | read | yes | filter,expand,order,page | batchItems |
| GET | `/api/totvsmoda/fiscal/v2/invoices/disable` | read_get_query | read | yes | order,page | - |
| GET | `/api/totvsmoda/fiscal/v2/invoices/item-detail-search` | read_get_query | read | yes | expand | - |
| POST | `/api/totvsmoda/fiscal/v2/invoices/manifestations` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/fiscal/v2/invoices/pending-conditional-products` | read_get_query | read | yes | - | - |
| POST | `/api/totvsmoda/fiscal/v2/invoices/search` | read_post_search | read | yes | filter,expand,order,page | shippingCompany,salesOrder,person,items,barCodes,taxes,payments,referencedInvoices,rateDifferential,relatedProductionOrder,observationNF,observationNFE,referencedTaxInvoices |
| POST | `/api/totvsmoda/fiscal/v2/transaction/print` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/fiscal/v2/xml-contents/{accessKey}` | read_get_path | read | yes | - | - |

## API Accounts Payable

- Source files: contas a pagar.json
- Endpoints: 4
- Mapped: 4

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/accounts-payable/v2/comissions-paid/search` | read_post_search | read | yes | filter,expand,order,page | accountMovements |
| POST | `/api/totvsmoda/accounts-payable/v2/duplicates` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/accounts-payable/v2/duplicates/search` | read_post_search | read | yes | filter,order,page | - |
| POST | `/api/totvsmoda/accounts-payable/v2/group-duplicates` | write_post | write | yes | - | - |

## API Accounts Receivable

- Source files: contas a receber.json
- Endpoints: 14
- Mapped: 14

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/accounts-receivable/v2/bank-slip` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/comission` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/customer-financial-balance/search` | read_post_search | read | yes | filter,page | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/documents/change-charge-type` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/documents/search` | read_post_search | read | yes | filter,expand,order,page | check,invoice,commissioneds,calculateValue |
| GET | `/api/totvsmoda/accounts-receivable/v2/gift-check-balances` | read_get_query | read | yes | page | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/gift-check-movements` | write_post | destructive | yes | - | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/gift-checks` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/invoices` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/invoices-payment` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/invoices-print/search` | read_post_search | read | yes | filter,order,page | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/invoices-renegotiate` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/invoices-settle/create` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/accounts-receivable/v2/payment-link` | write_post | write | yes | - | - |

## API Product Engineering

- Source files: engenhearia de produto.json
- Endpoints: 7
- Mapped: 6

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| GET | `/api/totvsmoda/product-engineering/v2/applications/search` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/product-engineering/v2/consumption-sheet/search` | read_post_search | read | yes | page | - |
| GET | `/api/totvsmoda/product-engineering/v2/engineering-configurations` | read_get_query | read | yes | - | - |
| POST | `/api/totvsmoda/product-engineering/v2/engineering-default/search` | read_post_search | read | yes | page | - |
| GET | `/api/totvsmoda/product-engineering/v2/operations` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/product-engineering/v2/references` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/product-engineering/v2/services/search` | read_post_search | read | yes | filter,expand,order,page | dataProviders,dataLevelGroup |

## API Production Order

- Source files: ordem de producao.json
- Endpoints: 3
- Mapped: 3

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/production-order/v2/materials/movement` | write_post | destructive | yes | - | - |
| POST | `/api/totvsmoda/production-order/v2/orders/search` | read_post_search | read | yes | filter,expand,order,page | observations,classifications,references,locations,programmings,items,materials,relationships,relationshipItems,productionNotes,productFinishedQuantitiesTypes,orderFinishedQuantitiesTypes |
| POST | `/api/totvsmoda/production-order/v2/pending-material-consumption` | read_post_search | read | yes | page | - |

## Api Product

- Source files: produto.json
- Endpoints: 42
- Mapped: 38

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| GET | `/api/totvsmoda/product/v2/additional-fields-types` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/product/v2/balances/search` | read_post_search | read | yes | filter,expand,order,page | locations |
| POST | `/api/totvsmoda/product/v2/barcodes` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/product/v2/barcodes/update` | write_post | write | yes | - | - |
| PUT | `/api/totvsmoda/product/v2/batch-info` | write_put | write | no | - | - |
| POST | `/api/totvsmoda/product/v2/batch-preferentialsalesorder` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/product/v2/batch/create` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/product/v2/batch/search` | read_post_search | read | yes | filter,page | - |
| PUT | `/api/totvsmoda/product/v2/branch-info/{branchCode}` | write_put | write | yes | filter | - |
| GET | `/api/totvsmoda/product/v2/category` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/product/v2/classification-relationship/create` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/product/v2/classification-relationship/update` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/product/v2/classificationType` | read_get_query | read | yes | order,page | - |
| GET | `/api/totvsmoda/product/v2/classifications` | read_get_query | read | yes | page | - |
| POST | `/api/totvsmoda/product/v2/classifications` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/product/v2/colors` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/product/v2/colors/search` | read_post_search | read | yes | filter,expand,page | additionalColorInformation |
| GET | `/api/totvsmoda/product/v2/composition-group-product` | read_get_query | read | yes | page | - |
| GET | `/api/totvsmoda/product/v2/composition-product` | read_get_query | read | yes | page | - |
| POST | `/api/totvsmoda/product/v2/compositions` | read_post_search | read | yes | expand,order,page | fibers |
| POST | `/api/totvsmoda/product/v2/costs/search` | read_post_search | read | yes | filter,order,page | - |
| PUT | `/api/totvsmoda/product/v2/data` | write_put | write | yes | filter | - |
| GET | `/api/totvsmoda/product/v2/grid` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/product/v2/grids` | write_post | write | no | - | - |
| GET | `/api/totvsmoda/product/v2/instruction-items` | read_get_query | read | yes | expand,order,page | - |
| GET | `/api/totvsmoda/product/v2/kardex-movement` | read_get_query | read | yes | - | - |
| GET | `/api/totvsmoda/product/v2/measurement-unit` | read_get_query | read | yes | expand,page | - |
| POST | `/api/totvsmoda/product/v2/omni-changed-balances` | read_post_search | read | yes | filter,order,page | - |
| GET | `/api/totvsmoda/product/v2/price-table-scales` | read_get_query | read | yes | page | - |
| GET | `/api/totvsmoda/product/v2/price-tables-headers` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/product/v2/price-tables/search` | read_post_search | read | yes | filter,order,page | - |
| POST | `/api/totvsmoda/product/v2/prices/search` | read_post_search | read | yes | filter,expand,order,page | promotionalInformation,informationOtherPromotions |
| POST | `/api/totvsmoda/product/v2/product-codes/search` | read_post_search | read | yes | filter,order,page | - |
| GET | `/api/totvsmoda/product/v2/product-grouper-configuration` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/product/v2/products/search` | read_post_search | read | yes | filter,expand,order,page | barCodes,classifications,additionalFields,suppliers,manufacturers,additionalColorInformation,referenceCategories,referenceCodeSequences,webData,details,branchesProductBlocked,conservationInstructions,observations |
| GET | `/api/totvsmoda/product/v2/products/{code}/{branchCode}` | read_get_path | read | yes | - | - |
| PUT | `/api/totvsmoda/product/v2/products/{code}/{branchCode}` | write_put | write | yes | - | - |
| POST | `/api/totvsmoda/product/v2/promotion-values/update` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/product/v2/references` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/product/v2/references/search` | read_post_search | read | yes | filter,expand,order,page | observations,details,barCodes,classifications,additionalFields,composition,suppliers,manufacturers,referenceCodeSequences,webData,webDetail,referenceCategories,measurementTableOmni,branchesProductBlocked,conservationInstructions |
| POST | `/api/totvsmoda/product/v2/values/create` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/product/v2/values/update` | write_post | write | yes | - | - |

## Api Product Material Request

- Source files: requisicao de material.json
- Endpoints: 9
- Mapped: 9

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/material-request/v2/approve` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/material-request/v2/headers/modify` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/material-request/v2/items` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/material-request/v2/items/cancel` | write_post | destructive | yes | - | - |
| POST | `/api/totvsmoda/material-request/v2/items/modify` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/material-request/v2/items/movement` | write_post | destructive | yes | - | - |
| POST | `/api/totvsmoda/material-request/v2/items/remove` | write_post | destructive | yes | - | - |
| POST | `/api/totvsmoda/material-request/v2/requests` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/material-request/v2/search` | read_post_search | read | yes | filter,expand,order,page | items,classifications,observations |

## Api Product Prototype

- Source files: prototipo.json
- Endpoints: 3
- Mapped: 3

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/product-prototype/v2/prototypes` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/product-prototype/v2/prototypes/search` | read_post_search | read | yes | expand,page | Destiny |
| POST | `/api/totvsmoda/product-prototype/v2/prototypes/update` | write_post | write | yes | - | - |

## API Logistics

- Source files: logistica.json
- Endpoints: 4
- Mapped: 4

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/logistics/v2/product-packagings` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/logistics/v2/product-packagings/add-quantity` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/logistics/v2/product-packagings/subtract-quantity` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/logistics/v2/product-storages/search` | read_post_search | read | yes | filter,order,page | - |

## API Person

- Source files: pessoa.json
- Endpoints: 20
- Mapped: 19

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/person/v2/bonus-consume` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/person/v2/branches/{branchId}` | read_get_path | read | yes | - | - |
| GET | `/api/totvsmoda/person/v2/branchesList` | read_get_query | read | yes | expand,order,page | - |
| POST | `/api/totvsmoda/person/v2/classification-relationship/remove` | write_post | destructive | no | - | - |
| GET | `/api/totvsmoda/person/v2/classifications` | read_get_query | read | yes | page | - |
| GET | `/api/totvsmoda/person/v2/contact-types` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/person/v2/customer-representatives` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/person/v2/email-types` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/person/v2/individual-customers` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/person/v2/individuals/search` | read_post_search | read | yes | filter,expand,order,page | phones,addresses,emails,classifications,additionalFields,references,observations,relateds,shippingCompany,statistics,representatives,customerObservations,familiars |
| POST | `/api/totvsmoda/person/v2/legal-customers` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/person/v2/legal-entities/search` | read_post_search | read | yes | filter,expand,order,page | phones,addresses,emails,classifications,additionalFields,references,observations,relateds,partners,shippingCompany,contacts,statistics,paymentMethods,preferences,socialNetworks,representatives,customerObservations |
| POST | `/api/totvsmoda/person/v2/list-balance-bonus` | write_post | write | yes | - | - |
| DELETE | `/api/totvsmoda/person/v2/messages` | write_delete | destructive | yes | - | - |
| POST | `/api/totvsmoda/person/v2/messages` | write_post | write | yes | - | - |
| PUT | `/api/totvsmoda/person/v2/messages/change` | write_put | write | yes | filter | - |
| GET | `/api/totvsmoda/person/v2/person-statistics` | read_get_query | read | yes | - | - |
| GET | `/api/totvsmoda/person/v2/phone-types` | read_get_query | read | yes | order,page | - |
| GET | `/api/totvsmoda/person/v2/reception-sale/search` | read_get_query | read | yes | page | - |
| POST | `/api/totvsmoda/person/v2/representatives/search` | read_post_search | read | yes | filter,expand,order,page | addresses,classifications,emails,additionalFields,phones,observations,pricetables,customers,salesRegions,representativeParameters |

## API Purchase Order

- Source files: ordem de compra.json
- Endpoints: 6
- Mapped: 4

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/purchase-order/v2/orders` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/purchase-order/v2/orders/cancel` | write_post | destructive | yes | - | - |
| POST | `/api/totvsmoda/purchase-order/v2/orders/change-status` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/purchase-order/v2/purchase-order/batch-link` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/purchase-order/v2/quantity-items` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/purchase-order/v2/search` | read_post_search | read | yes | filter,expand,order,page | items |

## API Seller

- Source files: vendedor.json
- Endpoints: 5
- Mapped: 4

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| GET | `/api/totvsmoda/seller/v2/operational-area` | read_get_query | read | yes | order,page | - |
| GET | `/api/totvsmoda/seller/v2/operational-area-cep` | read_get_query | read | yes | order,page | - |
| GET | `/api/totvsmoda/seller/v2/operational-area-city` | read_get_query | read | yes | order,page | - |
| GET | `/api/totvsmoda/seller/v2/operational-area-state` | read_get_query | read | no | order,page | - |
| POST | `/api/totvsmoda/seller/v2/search` | read_post_search | read | yes | filter,page | - |

## API Voucher

- Source files: voucher.json
- Endpoints: 4
- Mapped: 4

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/voucher/v2/create` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/voucher/v2/customer/create` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/voucher/v2/search` | read_get_query | read | yes | page | - |
| POST | `/api/totvsmoda/voucher/v2/update` | write_post | write | yes | - | - |

## Api Data Package

- Source files: pacote de dados.json
- Endpoints: 7
- Mapped: 7

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| GET | `/api/totvsmoda/data-package/v2/content-packages/{packageId}` | read_get_path | read | yes | - | - |
| GET | `/api/totvsmoda/data-package/v2/input-packages` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/data-package/v2/input-packages` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/data-package/v2/output-packages` | read_get_query | read | yes | order,page | - |
| POST | `/api/totvsmoda/data-package/v2/output-packages/receive` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/data-package/v2/packages/reactivate` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/data-package/v2/packages/{packageId}` | read_get_path | read | yes | - | - |

## Api General

- Source files: geral.json
- Endpoints: 15
- Mapped: 10

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| GET | `/api/totvsmoda/general/v2/classifications` | read_get_query | read | yes | page | - |
| POST | `/api/totvsmoda/general/v2/devolutions/create` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/general/v2/devolutions/search` | read_get_query | read | yes | expand | - |
| POST | `/api/totvsmoda/general/v2/financial-compensations` | write_post | write | no | - | - |
| GET | `/api/totvsmoda/general/v2/operations` | read_get_query | read | yes | expand,order,page | - |
| GET | `/api/totvsmoda/general/v2/payment-conditions` | read_get_query | read | yes | page | - |
| POST | `/api/totvsmoda/general/v2/payment-plan-simulate` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/general/v2/payment-plans` | read_get_query | read | yes | - | - |
| POST | `/api/totvsmoda/general/v2/product-counts` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/general/v2/product-counts/additional-count` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/general/v2/relationship-counts` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/general/v2/transaction-classification-relationship/create` | write_post | write | no | - | - |
| GET | `/api/totvsmoda/general/v2/transactions` | read_get_query | read | yes | expand | - |
| POST | `/api/totvsmoda/general/v2/transactions` | write_post | write | yes | - | - |
| GET | `/api/totvsmoda/general/v2/transactions/search` | read_get_query | read | no | expand,order,page | - |

## Api Global

- Source files: global.json
- Endpoints: 4
- Mapped: 4

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| GET | `/api/totvsmoda/location/v2/ceps/{cep}` | read_get_path | read | yes | - | - |
| GET | `/api/totvsmoda/location/v2/city` | read_get_query | read | yes | page | - |
| GET | `/api/totvsmoda/location/v2/country` | read_get_query | read | yes | page | - |
| GET | `/api/totvsmoda/location/v2/state` | read_get_query | read | yes | page | - |

## Api Image

- Source files: imagem.json
- Endpoints: 6
- Mapped: 2

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/image/V2/imports` | write_post | write | no | - | - |
| GET | `/api/totvsmoda/image/v2/person-images` | read_get_query | read | no | - | - |
| GET | `/api/totvsmoda/image/v2/persons` | read_get_query | read | no | page | - |
| POST | `/api/totvsmoda/image/v2/persons` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/image/v2/product` | write_post | write | yes | - | - |
| POST | `/api/totvsmoda/image/v2/product/search` | read_post_search | read | yes | filter,page | - |

## API Analytics

- Source files: analytics.json
- Endpoints: 61
- Mapped: 0

| Method | Path | Type | Risk | Mapped | Flags | Expand |
|---|---|---|---|---|---|---|
| POST | `/api/totvsmoda/analytics/v2/branch-fiscal-movement/search` | read_post_search | read | no | filter,page | - |
| GET | `/api/totvsmoda/analytics/v2/branch-sale` | read_get_query | read | no | page | - |
| POST | `/api/totvsmoda/analytics/v2/buyer-fiscal-movement/search` | read_post_search | read | no | filter,page | - |
| POST | `/api/totvsmoda/analytics/v2/fiscal-movement/search` | read_post_search | read | no | filter,page | - |
| POST | `/api/totvsmoda/analytics/v2/operation-fiscal-movement/search` | read_post_search | read | no | filter,page | - |
| POST | `/api/totvsmoda/analytics/v2/payment-fiscal-movement/search` | read_post_search | read | no | filter,page | - |
| POST | `/api/totvsmoda/analytics/v2/person-fiscal-movement/search` | read_post_search | read | no | filter,page | - |
| POST | `/api/totvsmoda/analytics/v2/product-fiscal-movement/search` | read_post_search | read | no | filter,page | - |
| POST | `/api/totvsmoda/analytics/v2/representative-fiscal-movement/search` | read_post_search | read | no | filter,page | - |
| POST | `/api/totvsmoda/analytics/v2/seller-fiscal-movement/search` | read_post_search | read | no | filter,page | - |
| POST | `/api/totvsmoda/analytics/v2/seller-panel/product-classification/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/analytics/v2/seller-panel/sales-target/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/analytics/v2/seller-panel/sales-vs-returns/search` | read_post_search | read | no | - | - |
| GET | `/api/totvsmoda/analytics/v2/seller-panel/seller-code` | read_get_query | read | no | - | - |
| GET | `/api/totvsmoda/analytics/v2/seller-panel/seller/branchesList` | read_get_query | read | no | - | - |
| POST | `/api/totvsmoda/analytics/v2/seller-panel/seller/conditional-rate` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/analytics/v2/seller-panel/seller/customer-purchased-products` | read_post_search | read | no | page | - |
| POST | `/api/totvsmoda/analytics/v2/seller-panel/seller/day-count-customers` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/analytics/v2/seller-panel/seller/pending-conditionals` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/analytics/v2/seller-panel/seller/period-birthday` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/analytics/v2/seller-panel/seller/top-customers` | write_post | write | no | - | - |
| POST | `/api/totvsmoda/analytics/v2/seller-panel/totals/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/analytics/v2/seller-panel/weekdays/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/analytics/v2/stock-fiscal-movement/search` | read_post_search | read | no | filter,page | - |
| POST | `/api/totvsmoda/ecommerce-sales-order/v2/best-selling-products/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/ecommerce-sales-order/v2/orders-customer-quantity/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/ecommerce-sales-order/v2/sales-quantity-hour/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/ecommerce-sales-order/v2/sales-quantity-weekday/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/account-balance/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/amount-received-document/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/average-payment-period/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/average-receipt-period/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/biweekly/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/financial-income-statement/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/open-amount-document/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/overdue-cards/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/ranking-customer-biggers/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/ranking-customer-debtors/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/ranking-supplier-biggers/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/ranking-supplier-debtors/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/total-payable/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/financial-panel/v2/total-receivable/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/manufacturing/v2/defect-finalization/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/manufacturing/v2/defect-panel/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/manufacturing/v2/fifteenDays-finalization/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/manufacturing/v2/normal-finalization/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/manufacturing/v2/quantity-location/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/manufacturing/v2/quantity-part-location/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/manufacturing/v2/throughput-movement-place/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/sale-panel/v2/branch-ranking/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/sale-panel/v2/document-types/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/sale-panel/v2/hours/search` | read_post_search | read | no | - | - |
| GET | `/api/totvsmoda/sale-panel/v2/product-classification-types` | read_get_query | read | no | - | - |
| POST | `/api/totvsmoda/sale-panel/v2/product-classifications/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/sale-panel/v2/sellers-list/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/sale-panel/v2/sellers/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/sale-panel/v2/totals-branch-type/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/sale-panel/v2/totals-branch/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/sale-panel/v2/totals-seller/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/sale-panel/v2/totals/search` | read_post_search | read | no | - | - |
| POST | `/api/totvsmoda/sale-panel/v2/weekdays/search` | read_post_search | read | no | - | - |
