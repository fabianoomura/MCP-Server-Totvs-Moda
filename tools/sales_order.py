"""
Sales Order Tools
=================
Implements all MCP tools for the TOTVS Moda Sales Order API V2.
Endpoint base: /api/totvsmoda/sales-order/v2/
"""

import logging
from typing import Any

from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults
from tools._dates import normalize_day_ranges
import response_cache as cache

logger = logging.getLogger("totvs-moda-mcp.sales-order")

BASE = "/api/totvsmoda/sales-order/v2"


class SalesOrderTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    def _invalidate_after_write(self) -> None:
        for prefix in (
            "orders",
            "dashboard",
            "customer360",
            "stock",
            "product360_full",
            "order360_full",
            "sales_today_summary",
            "sales_by_representative",
            "sales_by_channel",
        ):
            cache.invalidate(prefix)

    # ------------------------------------------------------------------ #
    # READ operations                                                      #
    # ------------------------------------------------------------------ #

    async def search_orders(self, args: dict[str, Any]) -> Any:
        """
        POST /orders/search
        Busca pedidos de venda com filtros flexíveis.
        """
        args = inject_branch_defaults(args)
        args = normalize_day_ranges(args)
        # Build filter object from flat args
        filter_fields = [
            "startOrderDate",
            "endOrderDate",
            "branchCodeList",
            "orderCodeList",
            "orderIdList",
            "customerOrderCodeList",
            "integrationCodeList",
            "customerCodeList",
            "customerCpfCnpjList",
            "representativeCodeList",
            "representativeCpfCnpjList",
            "orderStatusList",
            "operationCodeList",
            "startBillingForecastDate",
            "endBillingForecastDate",
            "hasShippingCompany",
            "hasPdvTransaction",
            "hasFinancialProcessed",
            "classifications",
            "experienceTypeList",
            "change",
        ]

        order_filter = {}
        for field in filter_fields:
            if field in args and args[field] is not None:
                order_filter[field] = args[field]

        body: dict[str, Any] = {}

        if order_filter:
            body["filter"] = order_filter

        if "expand" in args:
            body["expand"] = args["expand"]

        if "order" in args:
            body["order"] = args["order"]

        body["page"] = args.get("page", 1)
        body["pageSize"] = args.get("pageSize", 100)

        cached = cache.get("orders", body, cache.SALES)
        if cached is not None:
            return apply_fields(cached, args)

        result = await self.client.post(f"{BASE}/orders/search", body)
        cache.put("orders", body, result)
        return apply_fields(result, args)

    async def get_order_invoices(self, args: dict[str, Any]) -> Any:
        """
        GET /invoices?branchCode=X&orderCode=Y
        Retorna notas fiscais vinculadas ao pedido.
        """
        args = inject_branch_defaults(args)
        params = self._pascal_params(
            args,
            (
                "branchCode",
                "orderCode",
                "orderId",
                "maxChangeFilterDate",
                "invoiceStatusType",
            ),
        )
        result = await self.client.get(f"{BASE}/invoices", params=params)
        return apply_fields(result, args)

    async def get_pending_items(self, args: dict[str, Any]) -> Any:
        """
        GET /pending-items?branchCode=X&orderCode=Y
        Retorna itens pendentes (não faturados) do pedido.
        """
        args = inject_branch_defaults(args)
        params = self._pascal_params(
            args,
            ("branchCode", "orderCode", "orderId", "maxChangeFilterDate"),
        )
        result = await self.client.get(f"{BASE}/pending-items", params=params)
        return apply_fields(result, args)

    async def get_discount_types(self, args: dict[str, Any]) -> Any:
        """
        GET /discount-type?branchCode=X
        Consulta tipos de desconto disponíveis.
        """
        params = self._pascal_params(
            args,
            ("startChangeDate", "endChangeDate", "order", "page", "pageSize"),
        )
        return await self.client.get(f"{BASE}/discount-type", params=params or None)

    async def get_billing_suggestions(self, args: dict[str, Any]) -> Any:
        """
        GET /billing-suggestions?branchCode=X&orderCode=Y
        Consulta sugestões de faturamento.
        """
        args = inject_branch_defaults(args)
        params = self._pascal_params(
            args,
            (
                "branchCode",
                "suggestionCode",
                "startSuggestionDate",
                "endSuggestionDate",
                "suggestionStatusList",
                "orderBranchCode",
                "orderCode",
                "startChangeDate",
                "endChangeDate",
                "order",
                "page",
                "pageSize",
                "expand",
            ),
        )
        result = await self.client.get(f"{BASE}/billing-suggestions", params=params)
        return apply_fields(result, args)

    async def get_classifications(self, args: dict[str, Any]) -> Any:
        """
        GET /classifications?branchCode=X
        Consulta classificações disponíveis.
        """
        params = self._pascal_params(
            args,
            ("startChangeDate", "endChangeDate", "typeCodeList", "page", "pageSize"),
        )
        result = await self.client.get(f"{BASE}/classifications", params=params or None)
        return apply_fields(result, args)

    async def get_changed_batch_items(self, args: dict[str, Any]) -> Any:
        """GET /changed-batch-items — Itens de lote associados a pedidos atualizados."""
        args = inject_branch_defaults(args)
        params = self._pascal_params(
            args,
            ("branchCode", "orderCode", "batchCode", "startDate", "endDate"),
        )
        result = await self.client.get(f"{BASE}/changed-batch-items", params=params)
        return apply_fields(result, args)

    # ------------------------------------------------------------------ #
    # WRITE operations                                                     #
    # ------------------------------------------------------------------ #

    async def create_order(self, args: dict[str, Any]) -> Any:
        """
        POST /b2c-orders
        Cria um novo pedido de venda B2C.
        """
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/b2c-orders", body)
        self._invalidate_after_write()
        return result

    async def cancel_order(self, args: dict[str, Any]) -> Any:
        """
        POST /orders/cancel
        Cancela um pedido de venda. reasonCancellationCode é obrigatório (integer).
        """
        args = inject_branch_defaults(args)
        body: dict[str, Any] = {
            "branchCode": args["branchCode"],
            "orderCode": args["orderCode"],
            "reasonCancellationCode": args["reasonCancellationCode"],
        }
        result = await self.client.post(f"{BASE}/orders/cancel", body)
        self._invalidate_after_write()
        return result

    async def change_order_status(self, args: dict[str, Any]) -> Any:
        """POST /orders/change-status — Altera a situação do pedido."""
        args = inject_branch_defaults(args)
        # Accept both swagger field (statusOrder) and legacy alias (newStatus)
        status = args.get("statusOrder") or args.get("newStatus")
        if not status:
            raise ValueError("statusOrder é obrigatório (ou newStatus como alias legado)")
        body = {k: v for k, v in args.items() if v is not None and k != "newStatus"}
        body["statusOrder"] = status
        body.pop("newStatus", None)
        result = await self.client.post(f"{BASE}/orders/change-status", body)
        self._invalidate_after_write()
        return result

    async def add_order_items(self, args: dict[str, Any]) -> Any:
        """POST /items — ⚠️ Adiciona itens a pedido existente."""
        if not args.get("items"):
            raise ValueError("'items' é obrigatório")
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/items", body)
        self._invalidate_after_write()
        return result

    async def remove_order_item(self, args: dict[str, Any]) -> Any:
        """DELETE /items — ⚠️ Remove item de pedido (query params PascalCase)."""
        params: dict[str, Any] = {}
        for field, param in (
            ("branchCode", "BranchCode"), ("orderCode", "OrderCode"),
            ("productCode", "ProductCode"), ("productSku", "ProductSku"),
        ):
            if args.get(field) is not None:
                params[param] = args[field]
        result = await self.client.delete(f"{BASE}/items", params=params)
        self._invalidate_after_write()
        return result

    async def cancel_order_items(self, args: dict[str, Any]) -> Any:
        """POST /cancel-items — ⚠️ Cancela quantidades de itens."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/cancel-items", body)
        self._invalidate_after_write()
        return result

    async def change_order_item_quantity(self, args: dict[str, Any]) -> Any:
        """POST /quantity-items — ⚠️ Altera quantidade de itens."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/quantity-items", body)
        self._invalidate_after_write()
        return result

    async def update_order_items_additional(self, args: dict[str, Any]) -> Any:
        """POST /additional-items — ⚠️ Altera dados adicionais de itens."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/additional-items", body)
        self._invalidate_after_write()
        return result

    async def add_order_observation(self, args: dict[str, Any]) -> Any:
        """POST /observations-order — ⚠️ Adiciona observação ao pedido."""
        if not args.get("observation"):
            raise ValueError("'observation' é obrigatório")
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/observations-order", body)
        self._invalidate_after_write()
        return result

    async def update_order_shipping(self, args: dict[str, Any]) -> Any:
        """POST /shipping-order — ⚠️ Altera dados de transporte do pedido."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/shipping-order", body)
        self._invalidate_after_write()
        return result

    async def update_order_additional(self, args: dict[str, Any]) -> Any:
        """POST /additional-order — ⚠️ Altera dados adicionais do pedido."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/additional-order", body)
        self._invalidate_after_write()
        return result

    async def search_batch_items(self, args: dict[str, Any]) -> Any:
        """GET /batch-items — Lista lotes de itens (query params PascalCase)."""
        params = self._pascal_params(
            args,
            ("status", "startChangeDate", "endChangeDate", "order", "page", "pageSize"),
        )
        result = await self.client.get(f"{BASE}/batch-items", params=params or None)
        return apply_fields(result, args)

    def _pascal_params(self, args: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
        """Map lower camelCase tool args to TOTVS PascalCase query params."""
        return {field[:1].upper() + field[1:]: args[field] for field in fields if args.get(field) is not None}

    async def create_order_relationship_counts(self, args: dict[str, Any]) -> Any:
        """POST /relationship-counts — ⚠️ Cria contagens de relacionamento de pedido."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/relationship-counts", body)
        self._invalidate_after_write()
        return result

    async def create_pdv_transaction(self, args: dict[str, Any]) -> Any:
        """POST /pdv-transactions - grava dados de transacao PDV."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/pdv-transactions", body)
        self._invalidate_after_write()
        return result

    async def create_relationship_batch_items(self, args: dict[str, Any]) -> Any:
        """POST /relationship-batch-items - relaciona item de lote ao item do pedido."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/relationship-batch-items", body)
        self._invalidate_after_write()
        return result

    async def suggest_batch_items_by_nuance(self, args: dict[str, Any]) -> Any:
        """POST /suggest-batch-items-nuance - sugere e grava lote por nuance de cor."""
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/suggest-batch-items-nuance", body)
        self._invalidate_after_write()
        return result

    async def update_order_header(self, args: dict[str, Any]) -> Any:
        """
        POST /header
        Altera dados de capa do pedido.
        """
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        result = await self.client.post(f"{BASE}/header", body)
        self._invalidate_after_write()
        return result

    async def update_order_items_price(self, args: dict[str, Any]) -> Any:
        """
        POST /price-items
        Altera preço de itens do pedido.
        """
        args = inject_branch_defaults(args)
        body = {
            "branchCode": args["branchCode"],
            "orderCode": args["orderCode"],
            "items": args["items"],
        }
        result = await self.client.post(f"{BASE}/price-items", body)
        self._invalidate_after_write()
        return result


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

WRITE_TOOL_ANNOTATIONS: dict[str, bool] = {
    "destructiveHint": True,
    "idempotentHint": False,
    "readOnlyHint": False,
    "openWorldHint": True,
}

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_orders",
        description=(
            "Busca pedidos de venda (filtros flexíveis). Retorna: items[] com orderCode, orderDate, branchCode, customerCode, customerName, customerCpfCnpj, orderStatus, totalValue, representativeCode. Cada item em items[] tem: productCode, name, productSku, quantity, price, discount, totalValue. Use expand='items' APENAS quando precisar detalhes dos produtos (resposta fica grande). Para agregar vendas por produto use totvs_get_products_sold. Para resumo por filial/status use totvs_sales_summary_by_period. Para top clientes use totvs_top_customers. Suporta filtro por data, status, cliente, CPF, código de integração Shopify (SHP-XXXX), e expand para itens/NF-e/endereço/observações."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "startOrderDate": {
                    "type": "string",
                    "description": "Data inicial ISO 8601"
                },
                "endOrderDate": {
                    "type": "string",
                    "description": "Data final ISO 8601"
                },
                "orderCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos TOTVS do pedido"
                },
                "integrationCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Códigos de integração ex: SHP-1234"
                },
                "customerCpfCnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "CPF/CNPJ dos clientes"
                },
                "customerCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "orderStatusList": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "InProgress",
                            "BillingReleased",
                            "PartiallyAnswered",
                            "Attended",
                            "Blocked",
                            "Canceled",
                            "InComposition",
                            "InAnalysis"
                        ]
                    },
                    "description": "Situação do pedido: 1=InProgress(Em andamento), 2=BillingReleased(Liberado faturamento), 3=PartiallyAnswered(Parcialmente atendido), 4=Attended(Atendido), 5=Blocked(Bloqueado), 6=Canceled(Cancelado), 7=InComposition(Em composição), 8=InAnalysis(Em análise)"
                },
                "branchCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos das filiais"
                },
                "operationCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "representativeCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Códigos dos representantes"
                },
                "representativeCpfCnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "CPF/CNPJ dos representantes"
                },
                "startBillingForecastDate": {
                    "type": "string"
                },
                "endBillingForecastDate": {
                    "type": "string"
                },
                "hasShippingCompany": {
                    "type": "boolean"
                },
                "hasPdvTransaction": {
                    "type": "boolean"
                },
                "hasFinancialProcessed": {
                    "type": "boolean"
                },
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "integer"
                            },
                            "codeList": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": [
                            "type"
                        ]
                    },
                    "description": "Filtro por classificações: [{type, codeList}]"
                },
                "experienceTypeList": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "Ecommerce",
                            "ShipFromStore",
                            "ClickAndCollect",
                            "PickupStore",
                            "InfiniteShelf"
                        ]
                    },
                    "description": "Tipo de experiência: Ecommerce, ShipFromStore, ClickAndCollect, PickupStore, InfiniteShelf"
                },
                "change": {
                    "type": "object",
                    "description": "Filtro oficial por alteração de dados"
                },
                "expand": {
                    "type": "string",
                    "description": "items,invoices,shippingAddress,observations,invoiceObservations,representativeObservations,classifications,discounts,commissioneds,counts"
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100,
                    "description": "Máximo 500 no Swagger"
                },
                "order": {
                    "type": "string",
                    "description": "Ordenação suportada: branchCode, orderCode, operationCode, customerCode, maxChangeFilterDate, items, batchItems. Use - para desc."
                },
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Lista opcional de campos a retornar. Reduz tokens. Ex: ['orderCode','customerName','totalValue']. Suporta notação aninhada: 'items.productCode'."
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_order_invoices",
        description="NF-e vinculadas a um pedido de venda.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "maxChangeFilterDate": {
                    "type": "string"
                },
                "invoiceStatusType": {
                    "type": "integer"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_pending_items",
        description="Itens pendentes de faturamento em um pedido.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "maxChangeFilterDate": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_billing_suggestions",
        description="Sugestões de faturamento do TOTVS.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "suggestionCode": {
                    "type": "integer"
                },
                "startSuggestionDate": {
                    "type": "string"
                },
                "endSuggestionDate": {
                    "type": "string"
                },
                "suggestionStatusList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "orderBranchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "startChangeDate": {
                    "type": "string"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "order": {
                    "type": "string"
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100
                },
                "expand": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_cancel_order",
        description=(
            "⚠️ ESCRITA — Cancela pedido de venda (irreversível). Somente pedidos não aceitos na retaguarda podem ser cancelados."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "orderCode": {
                    "type": "integer"
                },
                "reasonCancellationCode": {
                    "type": "integer",
                    "description": "Código do motivo de cancelamento (obrigatório)"
                },
                "ReasonCancellationDescription": {
                    "type": "string",
                    "description": "Descrição do cancelamento (max 80 chars)"
                }
            },
            "required": [
                "branchCode",
                "orderCode",
                "reasonCancellationCode"
            ]
        },
        annotations=WRITE_TOOL_ANNOTATIONS,
    ),
    types.Tool(
        name="totvs_change_order_status",
        description=(
            "⚠️ ESCRITA — Altera situação do pedido. Aceita apenas valores do enum: InProgress (Em andamento), BillingReleased (Liberado p/ faturamento), Blocked (Bloqueado), InComposition (Em composição), InAnalysis (Em análise)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "orderCode": {
                    "type": "integer"
                },
                "statusOrder": {
                    "type": "string",
                    "enum": [
                        "InProgress",
                        "BillingReleased",
                        "Blocked",
                        "InComposition",
                        "InAnalysis"
                    ],
                    "description": "Nova situação do pedido"
                },
                "reasonBlockingCode": {
                    "type": "integer",
                    "description": "Código do motivo de bloqueio (apenas para statusOrder=Blocked)"
                },
                "reasonBlockingDescription": {
                    "type": "string",
                    "description": "Descrição do motivo de bloqueio"
                }
            },
            "required": [
                "branchCode",
                "orderCode",
                "statusOrder"
            ]
        },
        annotations=WRITE_TOOL_ANNOTATIONS,
    ),
    types.Tool(
        name="totvs_update_order_items_price",
        description="⚠️ ESCRITA — Altera preço de itens do pedido.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial"
                },
                "orderCode": {
                    "type": "integer"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "itemSequential": {
                                "type": "integer"
                            },
                            "price": {
                                "type": "number"
                            }
                        },
                        "required": [
                            "itemSequential",
                            "price"
                        ]
                    }
                }
            },
            "required": [
                "branchCode",
                "orderCode",
                "items"
            ]
        },
        annotations=WRITE_TOOL_ANNOTATIONS,
    ),
    types.Tool(
        name="totvs_add_order_items",
        description=(
            "⚠️ ESCRITA — Adiciona itens a pedido existente. Informe branchCode+orderCode OU orderId + lista 'items'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "items": {
                    "type": "array",
                    "description": "Lista de itens. Cada item exige: productCode, productSku, quantity, price. Opcionais: originalPrice, discountPercentage, discountValue, billingForecastDate, billingStartDate, customerOrderCode, customerProductCode, rollMeasureCode, sequentials, sequentialsValues, groupObservations, commissioneds.",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "items"
            ]
        },
    ),
    types.Tool(
        name="totvs_remove_order_item",
        description="⚠️ ESCRITA — Remove item de pedido (DELETE). Identifica item por productCode ou productSku.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "productCode": {
                    "type": "integer"
                },
                "productSku": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_cancel_order_items",
        description="⚠️ ESCRITA — Cancela quantidades de itens do pedido.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "items": {
                    "type": "array",
                    "description": "Lista CancelOrderItemModel (productCode, productSku, quantityToCancel, reasonCancellationCode)",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "items"
            ]
        },
    ),
    types.Tool(
        name="totvs_change_order_item_quantity",
        description="⚠️ ESCRITA — Altera quantidade de itens do pedido.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "items": {
                    "type": "array",
                    "description": "Lista UpdateOrderItemQuantityModel (productCode, productSku, newQuantity)",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "items"
            ]
        },
    ),
    types.Tool(
        name="totvs_update_order_items_additional",
        description=(
            "⚠️ ESCRITA — Altera dados adicionais de itens (customerOrderCode, customerProductCode, billingForecastDate etc)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "items"
            ]
        },
    ),
    types.Tool(
        name="totvs_add_order_observation",
        description="⚠️ ESCRITA — Adiciona observação ao pedido.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "observation": {
                    "type": "string"
                },
                "visualizationType": {
                    "type": "string",
                    "description": "Enum VisualizationObservationType"
                }
            },
            "required": [
                "observation"
            ]
        },
    ),
    types.Tool(
        name="totvs_update_order_shipping",
        description="⚠️ ESCRITA — Altera dados de transporte do pedido (transportadora, frete, endereço).",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "shippingCompanyCode": {
                    "type": "integer"
                },
                "shippingCompanyCpfCnpj": {
                    "type": "string"
                },
                "redispatchingShippingCompanyCode": {
                    "type": "integer"
                },
                "redispatchingShippingCompanyCpfCnpj": {
                    "type": "string"
                },
                "redispatchingFreightType": {
                    "type": "integer"
                },
                "freightType": {
                    "type": "string",
                    "description": "Enum FreitghtType"
                },
                "freightPercentage": {
                    "type": "number"
                },
                "freightValue": {
                    "type": "number"
                },
                "shippingAddress": {
                    "type": "object"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_update_order_additional",
        description="⚠️ ESCRITA — Altera dados adicionais do pedido (tracking, ecommerce, omni, etc).",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "shippingService": {
                    "type": "string"
                },
                "trackingId": {
                    "type": "string"
                },
                "ecommerceStage": {
                    "type": "string"
                },
                "omniSiteId": {
                    "type": "integer"
                },
                "compensationDays": {
                    "type": "integer"
                },
                "anticipationDay": {
                    "type": "integer"
                },
                "entryType": {
                    "type": "string"
                },
                "experienceType": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_search_batch_items",
        description="Consulta lote de pedidos por status e período de alteração.",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string"
                },
                "startChangeDate": {
                    "type": "string",
                    "description": "ISO 8601"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100
                },
                "order": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_changed_batch_items",
        description="Itens de lote associados a pedidos atualizados.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "batchCode": {
                    "type": "integer"
                },
                "startDate": {
                    "type": "string"
                },
                "endDate": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_create_order_relationship_counts",
        description="⚠️ ESCRITA — Vincula contagens ao pedido.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "counts": {
                    "type": "array",
                    "description": "Lista de contagens (countCode, etc)",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "counts"
            ]
        },
    ),
    types.Tool(
        name="totvs_create_pdv_transaction",
        description="⚠️ ESCRITA — Grava dados de transação TOTVS Moda PDV no pedido.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "transactions": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            }
        },
    ),
    types.Tool(
        name="totvs_create_order_relationship_batch_items",
        description="⚠️ ESCRITA — Relaciona item de lote ao item do pedido de venda.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            }
        },
    ),
    types.Tool(
        name="totvs_suggest_order_batch_items_by_nuance",
        description="⚠️ ESCRITA — Sugere e grava relacionamento de lote com item do pedido por nuance de cor.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "orderId": {
                    "type": "string"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            }
        },
    ),
    types.Tool(
        name="totvs_create_order",
        description="⚠️ Cria um pedido de venda B2C (POST /sales-order/v2/b2c-orders). Aceita o payload completo do endpoint; campos extras nao listados sao repassados.",
        inputSchema={
            "type": "object",
            "properties": {
                "orderId": {"type": "string"},
                "branchCode": {"type": "integer"},
                "customerOrderCode": {"type": "string"},
                "integrationCode": {"type": "string"},
                "orderDate": {"type": "string"},
                "customerCode": {"type": "integer"},
                "representativeCode": {"type": "integer"},
                "representativeCpfCnpj": {"type": "string"},
                "operationCode": {"type": "integer"},
                "priceTableCode": {"type": "integer"},
                "paymentConditionCode": {"type": "integer"},
                "paymentBaseDate": {"type": "string"},
                "shippingCompanyCode": {"type": "integer"},
                "billingForecastDate": {"type": "string"},
                "freightType": {"type": ["string", "integer"]},
                "freightValue": {"type": "number"},
                "totalAmountOrder": {"type": "number"},
                "statusOrder": {"type": "string"},
                "experienceType": {"type": "string"},
                "chargeType": {"type": "string"},
                "priorityCode": {"type": "integer"},
                "classifications": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "items": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "payments": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "shippingAddress": {"type": "object"}
            },
            "required": [
                "branchCode",
                "customerCode",
                "operationCode",
                "items"
            ]
        },
    ),
    types.Tool(
        name="totvs_update_order_header",
        description="⚠️ Altera dados de capa (cabeçalho) do pedido.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "orderCode": {
                    "type": "integer"
                },
                "paymentConditionCode": {
                    "type": "integer"
                },
                "representativeCode": {
                    "type": "integer"
                },
                "observation": {
                    "type": "string"
                }
            },
            "required": [
                "branchCode",
                "orderCode"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_order_classifications",
        description="Classificações de pedido disponíveis.",
        inputSchema={
            "type": "object",
            "properties": {
                "startChangeDate": {
                    "type": "string"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "typeCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_discount_types",
        description="Tipos de desconto disponíveis para pedido de venda.",
        inputSchema={
            "type": "object",
            "properties": {
                "startChangeDate": {
                    "type": "string"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "order": {
                    "type": "string"
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100
                }
            }
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_orders": "search_orders",
    "totvs_get_order_invoices": "get_order_invoices",
    "totvs_get_pending_items": "get_pending_items",
    "totvs_get_billing_suggestions": "get_billing_suggestions",
    "totvs_cancel_order": "cancel_order",
    "totvs_change_order_status": "change_order_status",
    "totvs_update_order_items_price": "update_order_items_price",
    "totvs_add_order_items": "add_order_items",
    "totvs_remove_order_item": "remove_order_item",
    "totvs_cancel_order_items": "cancel_order_items",
    "totvs_change_order_item_quantity": "change_order_item_quantity",
    "totvs_update_order_items_additional": "update_order_items_additional",
    "totvs_add_order_observation": "add_order_observation",
    "totvs_update_order_shipping": "update_order_shipping",
    "totvs_update_order_additional": "update_order_additional",
    "totvs_search_batch_items": "search_batch_items",
    "totvs_get_changed_batch_items": "get_changed_batch_items",
    "totvs_create_order_relationship_counts": "create_order_relationship_counts",
    "totvs_create_pdv_transaction": "create_pdv_transaction",
    "totvs_create_order_relationship_batch_items": "create_relationship_batch_items",
    "totvs_suggest_order_batch_items_by_nuance": "suggest_batch_items_by_nuance",
    "totvs_create_order": "create_order",
    "totvs_update_order_header": "update_order_header",
    "totvs_get_order_classifications": "get_classifications",
    "totvs_get_discount_types": "get_discount_types",
}