"""
Fiscal Tools
============
API Fiscal v2 — /api/totvsmoda/fiscal/v2/
Notas fiscais, XML NF-e, DANFE, certificado digital, centro de custo.
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults
import response_cache as cache

logger = logging.getLogger("totvs-moda-mcp.fiscal")
BASE = "/api/totvsmoda/fiscal/v2"


class FiscalTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_invoices(self, args: dict[str, Any]) -> Any:
        """POST /invoices/search — Lista NF-e por filtro geral."""
        args = inject_branch_defaults(args)
        flt: dict[str, Any] = {
            "branchCodeList": args["branchCodeList"],
        }
        for field in (
            "invoiceSequenceList", "invoiceCodeList", "operationType", "origin",
            "invoiceStatusList", "personCodeList", "operationCodeList",
            "documentTypeCodeList", "personCpfCnpjList",
            "startInvoiceCode", "endInvoiceCode",
            "startIssueDate", "endIssueDate",
            "serialCodeList", "eletronicInvoiceStatusList",
            "shippingCompanyCodeList", "shippingCompanyCpfCnpjList",
            "amountLastDays",
            "transactionBranchCode", "transactionCode", "transactionDate",
        ):
            if args.get(field) is not None:
                flt[field] = args[field]

        if args.get("startChangeDate") or args.get("endChangeDate"):
            flt["change"] = {k: v for k, v in {
                "startDate": args.get("startChangeDate"),
                "endDate": args.get("endChangeDate"),
            }.items() if v is not None}

        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        if args.get("expand"):
            body["expand"] = args["expand"]
        if args.get("order"):
            body["order"] = args["order"]

        cached = cache.get("fiscal_invoices", body, cache.FINANCIAL)
        if cached is not None:
            return apply_fields(cached, args)
        result = await self.client.post(f"{BASE}/invoices/search", body)
        cache.put("fiscal_invoices", body, result)
        return apply_fields(result, args)

    async def get_xml_content(self, args: dict[str, Any]) -> Any:
        """GET /xml-contents/{accessKey} — XML da NF-e pela chave de acesso (44 dígitos)."""
        return await self.client.get(f"{BASE}/xml-contents/{args['accessKey']}")

    async def get_invoice_item_detail(self, args: dict[str, Any]) -> Any:
        """GET /invoices/item-detail-search — Detalhe de itens da NF-e."""
        params = self._pascal_params(
            args,
            ("branchCode", "invoiceDate", "invoiceSequence", "accessKey", "expand"),
        )
        # Preserve official PascalCase args for backward compatibility.
        params.update({k: v for k, v in args.items() if k[:1].isupper() and v is not None})
        return await self.client.get(f"{BASE}/invoices/item-detail-search", params=params or None)

    async def get_danfe(self, args: dict[str, Any]) -> Any:
        """POST /danfe-search — Base64 do DANFE via XML da NF-e."""
        body: dict[str, Any] = {"mainInvoiceXml": args["mainInvoiceXml"]}
        if args.get("nfeDocumentType"):
            body["nfeDocumentType"] = args["nfeDocumentType"]
        return await self.client.post(f"{BASE}/danfe-search", body)

    async def search_invoice_products(self, args: dict[str, Any]) -> Any:
        """POST /invoice-products/search — Produtos de NF-e por filtro geral."""
        args = inject_branch_defaults(args)
        flt: dict[str, Any] = {
            "branchCodeList": args["branchCodeList"],
        }
        for field in (
            "ProductCodeList", "BatchBarCodeList", "invoiceCodeList",
            "operationType", "modality", "origin",
            "invoiceStatusList", "personCodeList", "ignorePersonCodeList",
            "operationCodeList", "personCpfCnpjList", "ignorePersonCpfCnpjList",
            "startIssueDate", "endIssueDate", "acessKeyList",
        ):
            if args.get(field) is not None:
                flt[field] = args[field]

        # More natural aliases while preserving Swagger's historical casing.
        aliases = {
            "productCodeList": "ProductCodeList",
            "batchBarCodeList": "BatchBarCodeList",
            "accessKeyList": "acessKeyList",
        }
        for alias, official in aliases.items():
            if args.get(alias) is not None and official not in flt:
                flt[official] = args[alias]

        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        if args.get("option"):
            body["option"] = args["option"]
        if args.get("expand"):
            body["expand"] = args["expand"]
        if args.get("order"):
            body["order"] = args["order"]

        result = await self.client.post(f"{BASE}/invoice-products/search", body)
        return apply_fields(result, args)

    async def get_digital_certificates(self, args: dict[str, Any]) -> Any:
        """GET /digital-certificates — Dados de certificados digitais."""
        args = inject_branch_defaults(args)
        params: dict[str, Any] = {
            "BranchCode": args["branchCode"],
            "EnviromentType": args["environmentType"],
        }
        return await self.client.get(f"{BASE}/digital-certificates", params=params)

    async def get_cost_center(self, args: dict[str, Any]) -> Any:
        """GET /cost-center — Centros de custo (datas obrigatórias)."""
        args = inject_branch_defaults(args)
        params: dict[str, Any] = {
            "StartChangeDate": args["startChangeDate"],
            "EndChangeDate": args["endChangeDate"],
        }
        if args.get("isInactive") is not None:
            params["IsInactive"] = args["isInactive"]
        if args.get("page"):
            params["Page"] = args["page"]
        if args.get("pageSize"):
            params["PageSize"] = args["pageSize"]
        return await self.client.get(f"{BASE}/cost-center", params=params)

    async def get_pending_conditional_products(self, args: dict[str, Any]) -> Any:
        """GET /invoices/pending-conditional-products — Saldo de produto em condicional por pessoa."""
        args = inject_branch_defaults(args)
        params: dict[str, Any] = {
            "BranchCode": args["branchCode"],
            "OnlyPendingItem": args.get("onlyPendingItem", True),
        }
        if args.get("personCode"):
            params["PersonCode"] = args["personCode"]
        if args.get("personCpfCnpj"):
            params["PersonCpfCnpj"] = args["personCpfCnpj"]
        return await self.client.get(f"{BASE}/invoices/pending-conditional-products", params=params)

    async def get_disabled_invoices(self, args: dict[str, Any]) -> Any:
        """GET /invoices/disable — NF-e inutilizadas por período e filial."""
        args = inject_branch_defaults(args)
        params: dict[str, Any] = {
            "StartDate": args["startDate"],
            "EndDate": args["endDate"],
            "BranchCodeList": args["branchCodeList"],
        }
        if args.get("page"):
            params["Page"] = args["page"]
        if args.get("pageSize"):
            params["PageSize"] = args["pageSize"]
        if args.get("order"):
            params["Order"] = args["order"]
        return await self.client.get(f"{BASE}/invoices/disable", params=params)

    async def print_transaction(self, args: dict[str, Any]) -> Any:
        """POST /transaction/print — Base64 da impressão da transação em PDF."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/transaction/print", body)

    async def create_manifestation(self, args: dict[str, Any]) -> Any:
        """POST /invoices/manifestations — ⚠️ Manifestação do destinatário NF-e."""
        args = inject_branch_defaults(args)
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/invoices/manifestations", body)

    def _pascal_params(self, args: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
        """Map lower camelCase tool args to TOTVS PascalCase query params."""
        return {field[:1].upper() + field[1:]: args[field] for field in fields if args.get(field) is not None}


# ------------------------------------------------------------------------
# Tool definitions (schemas) — imported by server.py
# ------------------------------------------------------------------------

import mcp.types as types

TOOLS: list[types.Tool] = [
    types.Tool(
        name="totvs_search_fiscal_invoices",
        description=(
            "Busca NF-e por período, cliente, status ou chave de acesso. Suporta expand para itens, pagamentos e observações."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "branchCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Lista de filiais (obrigatório)"
                },
                "invoiceSequenceList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "invoiceCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "operationType": {
                    "type": "string",
                    "enum": [
                        "All",
                        "Input",
                        "Output"
                    ],
                    "description": "Tipo de operação: All, Input(Entrada), Output(Saída)"
                },
                "origin": {
                    "type": "string",
                    "enum": [
                        "All",
                        "Own",
                        "ThirdParty"
                    ],
                    "description": "Origem: All, Own(Emissão própria), ThirdParty(Emissão de terceiro)"
                },
                "invoiceStatusList": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "Canceled",
                            "Denied",
                            "Issued",
                            "Normal",
                            "Deleted"
                        ]
                    },
                    "description": "Situação da NF: Normal, Issued(Emitida), Canceled(Cancelada), Denied(Denegada), Deleted(Excluída)"
                },
                "personCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "operationCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "documentTypeCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "personCpfCnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "startIssueDate": {
                    "type": "string",
                    "description": "ISO 8601"
                },
                "endIssueDate": {
                    "type": "string"
                },
                "serialCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "eletronicInvoiceStatusList": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "Authorized",
                            "Canceled",
                            "Denied",
                            "Sent",
                            "Generated",
                            "Rejected"
                        ]
                    }
                },
                "startChangeDate": {
                    "type": "string"
                },
                "endChangeDate": {
                    "type": "string"
                },
                "amountLastDays": {
                    "type": "integer"
                },
                "transactionBranchCode": {
                    "type": "integer"
                },
                "transactionCode": {
                    "type": "integer"
                },
                "transactionDate": {
                    "type": "string"
                },
                "expand": {
                    "type": "string",
                    "description": "shippingCompany,salesOrder,person,items,barCodes,taxes,payments,referencedInvoices,rateDifferential,relatedProductionOrder,observationNF,observationNFE,referencedTaxInvoices"
                },
                "order": {
                    "type": "string",
                    "description": "Ordenação suportada: branchCode, invoiceSequence, invoiceDate, maxChangeFilterDate. Use - para desc."
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100,
                    "description": "Máximo 100 no Swagger"
                },
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Lista opcional de campos a retornar. Reduz tokens. Ex: ['accessKey','invoiceCode','value']."
                }
            },
            "required": [
                "branchCodeList"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_nfe_xml",
        description="XML completo de uma NF-e pela chave de acesso (44 dígitos).",
        inputSchema={
            "type": "object",
            "properties": {
                "accessKey": {
                    "type": "string"
                }
            },
            "required": [
                "accessKey"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_invoice_item_detail",
        description="Detalhe de itens de NF-e. Informe accessKey OU branchCode + invoiceDate + invoiceSequence.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "invoiceDate": {
                    "type": "string"
                },
                "invoiceSequence": {
                    "type": "integer"
                },
                "accessKey": {
                    "type": "string"
                },
                "expand": {
                    "type": "string"
                },
                "BranchCode": {
                    "type": "integer",
                    "description": "Alias oficial PascalCase"
                },
                "InvoiceDate": {
                    "type": "string",
                    "description": "Alias oficial PascalCase"
                },
                "InvoiceSequence": {
                    "type": "integer",
                    "description": "Alias oficial PascalCase"
                },
                "AccessKey": {
                    "type": "string",
                    "description": "Alias oficial PascalCase"
                },
                "Expand": {
                    "type": "string",
                    "description": "Alias oficial PascalCase"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_get_danfe",
        description="DANFE em base64 (PDF) de uma NF-e a partir do XML.",
        inputSchema={
            "type": "object",
            "properties": {
                "mainInvoiceXml": {
                    "type": "string",
                    "description": "Conteúdo XML da NF-e"
                },
                "nfeDocumentType": {
                    "type": "string",
                    "description": "Tipo de documento NF-e"
                }
            },
            "required": [
                "mainInvoiceXml"
            ]
        },
    ),
    types.Tool(
        name="totvs_search_invoice_products",
        description="Produtos de NF-e por período, produto, pessoa, chave ou operação.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Lista de filiais (obrigatório)"
                },
                "productCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Alias natural de ProductCodeList"
                },
                "ProductCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "batchBarCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Alias natural de BatchBarCodeList"
                },
                "BatchBarCodeList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "invoiceCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "operationType": {
                    "type": "string",
                    "description": "E=Entrada, S=Saída"
                },
                "modality": {
                    "type": "string"
                },
                "origin": {
                    "type": "string"
                },
                "invoiceStatusList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "personCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "operationCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },
                "personCpfCnpjList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "startIssueDate": {
                    "type": "string"
                },
                "endIssueDate": {
                    "type": "string"
                },
                "accessKeyList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Alias natural de acessKeyList"
                },
                "acessKeyList": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "option": {
                    "type": "object"
                },
                "expand": {
                    "type": "string",
                    "description": "batchItems"
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
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Lista opcional de campos a retornar. Reduz tokens. Suporta notação aninhada."
                }
            },
            "required": [
                "branchCodeList"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_cost_center",
        description="Centros de custo por período de alteração.",
        inputSchema={
            "type": "object",
            "properties": {
                "startChangeDate": {
                    "type": "string",
                    "description": "Data inicial ISO 8601 (obrigatório)"
                },
                "endChangeDate": {
                    "type": "string",
                    "description": "Data final ISO 8601 (obrigatório)"
                },
                "isInactive": {
                    "type": "boolean"
                },
                "page": {
                    "type": "integer",
                    "default": 1
                },
                "pageSize": {
                    "type": "integer",
                    "default": 100
                }
            },
            "required": [
                "startChangeDate",
                "endChangeDate"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_digital_certificates",
        description="Dados de certificados digitais de uma filial.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial (obrigatório)"
                },
                "environmentType": {
                    "type": "string",
                    "description": "P=Produção, H=Homologação (obrigatório)"
                }
            },
            "required": [
                "branchCode",
                "environmentType"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_pending_conditional_products",
        description="Saldo de produtos em condicional (consignação) pendentes por pessoa.",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer",
                    "description": "Código da filial (obrigatório)"
                },
                "onlyPendingItem": {
                    "type": "boolean",
                    "default": True,
                    "description": "Apenas itens com saldo pendente"
                },
                "personCode": {
                    "type": "integer"
                },
                "personCpfCnpj": {
                    "type": "string"
                }
            },
            "required": [
                "branchCode"
            ]
        },
    ),
    types.Tool(
        name="totvs_get_disabled_invoices",
        description="NF-e inutilizadas por período e filial.",
        inputSchema={
            "type": "object",
            "properties": {
                "startDate": {
                    "type": "string",
                    "description": "Data inicial ISO 8601 (obrigatório)"
                },
                "endDate": {
                    "type": "string",
                    "description": "Data final ISO 8601 (obrigatório)"
                },
                "branchCodeList": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "Lista de filiais (obrigatório)"
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
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": [
                "startDate",
                "endDate",
                "branchCodeList"
            ]
        },
    ),
    types.Tool(
        name="totvs_print_transaction",
        description="Impressão de transação fiscal em PDF (base64).",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "transactionCode": {
                    "type": "integer"
                },
                "transactionDate": {
                    "type": "string"
                }
            }
        },
    ),
    types.Tool(
        name="totvs_create_nfe_manifestation",
        description="⚠️ Manifestação do destinatário de NF-e (ciência, confirmação, desconhecimento, não realização).",
        inputSchema={
            "type": "object",
            "properties": {
                "branchCode": {
                    "type": "integer"
                },
                "accessKey": {
                    "type": "string"
                },
                "manifestationType": {
                    "type": "string",
                    "description": "Tipo de manifestação"
                }
            },
            "required": [
                "branchCode",
                "accessKey",
                "manifestationType"
            ]
        },
    ),
]

ROUTES: dict[str, str] = {
    "totvs_search_fiscal_invoices": "search_invoices",
    "totvs_get_nfe_xml": "get_xml_content",
    "totvs_get_invoice_item_detail": "get_invoice_item_detail",
    "totvs_get_danfe": "get_danfe",
    "totvs_search_invoice_products": "search_invoice_products",
    "totvs_get_cost_center": "get_cost_center",
    "totvs_get_digital_certificates": "get_digital_certificates",
    "totvs_get_pending_conditional_products": "get_pending_conditional_products",
    "totvs_get_disabled_invoices": "get_disabled_invoices",
    "totvs_print_transaction": "print_transaction",
    "totvs_create_nfe_manifestation": "create_manifestation",
}