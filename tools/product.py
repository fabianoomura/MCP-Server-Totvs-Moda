"""
Product Tools
=============
TOTVS Moda Product API V2 — /api/totvsmoda/product/v2/

v2.3.0 additions (3 new endpoints):
- create_reference: POST /references
- update_barcode: POST /barcodes/update
- create_classification_type: POST /classifications (not to be confused with GET)
"""
import logging
from typing import Any
from totvs_client import TotvsClient
from tools._fields import apply_fields
from tools._defaults import inject_branch_defaults
from tools._value_types import normalize_value_type

logger = logging.getLogger("totvs-moda-mcp.product")
BASE = "/api/totvsmoda/product/v2"


class ProductTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    # ── READ ──────────────────────────────────────────────────────────────

    async def search_products(self, args: dict[str, Any]) -> Any:
        """POST /products/search."""
        args = inject_branch_defaults(args)
        # Business filter fields per CLAUDE.md ProductFilterModel
        filter_fields = {
            "productCodeList", "referenceCodeList", "productName", "groupCodeList",
            "startProductCode", "endProductCode", "classifications", "branchInfo",
            "hasPrice", "branchPriceCodeList", "priceCodeList", "hasCost",
            "branchCostCodeList", "costCodeList", "hasPriceTableItem",
            "branchPriceTableCodeList", "priceTableCodeList", "hasStock",
            "branchStockCode", "stockCode", "hasWebInfo", "change"
        }

        # Build filter object
        flt: dict[str, Any] = {k: v for k, v in args.items() if k in filter_fields and v is not None}

        # Build option object - BranchInfoCode is required
        option: dict[str, Any] = {}
        if args.get("branchCodeList"):
            option["BranchInfoCode"] = args["branchCodeList"][0] if isinstance(args["branchCodeList"], list) else args["branchCodeList"]

        # If priceCodeList provided in args, set hasPrice and copy to filter
        if args.get("priceCodeList"):
            flt["hasPrice"] = True
            if "priceCodeList" not in flt:
                flt["priceCodeList"] = args["priceCodeList"]
            # branchPriceCodeList defaults to branchCodeList if not specified
            if "branchPriceCodeList" not in flt and args.get("branchCodeList"):
                flt["branchPriceCodeList"] = args["branchCodeList"]

        # Build body
        body: dict[str, Any] = {"page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}

        if option:
            body["option"] = option
        if flt:
            body["filter"] = flt
        if args.get("order"):
            body["order"] = args["order"]

        result = await self.client.post(f"{BASE}/products/search", body)
        return apply_fields(result, args)

    async def get_product(self, args: dict[str, Any]) -> Any:
        """GET /products/{code}/{branchCode}."""
        args = inject_branch_defaults(args)
        code = args["code"]
        branch = args.get("branchCode", 1)
        return await self.client.get(f"{BASE}/products/{code}/{branch}")

    async def search_product_codes(self, args: dict[str, Any]) -> Any:
        """POST /product-codes/search."""
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE}/product-codes/search", body)
        return apply_fields(result, args)

    async def search_balances(self, args: dict[str, Any]) -> Any:
        """POST /balances/search — Saldos de estoque por filtro geral.
        option.balances[{branchCode, stockCodeList}] é obrigatório."""
        args = inject_branch_defaults(args)
        filter_keys = {"productCodeList", "referenceCodeList", "productName", "groupCodeList",
                       "startProductCode", "endProductCode", "classifications", "branchInfo",
                       "hasStock", "change"}
        flt = {k: v for k, v in args.items() if k in filter_keys and v is not None}
        balance_option: dict[str, Any] = {
            "branchCode": args.get("branchCode", 1),
            "stockCodeList": args.get("stockCodeList", [1]),
        }
        if args.get("isSalesOrder") is not None:
            balance_option["isSalesOrder"] = args["isSalesOrder"]
        body: dict[str, Any] = {
            "filter": flt,
            "option": {"balances": [balance_option]},
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 1000),
        }
        if args.get("order"):
            body["order"] = args["order"]
        if args.get("expand"):
            body["expand"] = args["expand"]
        result = await self.client.post(f"{BASE}/balances/search", body)
        return apply_fields(result, args)

    async def search_prices(self, args: dict[str, Any]) -> Any:
        """POST /prices/search."""
        args = inject_branch_defaults(args)
        filter_fields = {"productCodeList", "referenceCodeList", "priceTableCodeList"}
        price_codes = args.get("priceCodeList")
        if not price_codes:
            raise ValueError("priceCodeList é obrigatório.")
        prices_option = {
            "branchCode": args.get("branchCode"),
            "priceCodeList": [int(c) for c in price_codes],
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        prices_option = {k: v for k, v in prices_option.items() if v is not None}
        body = {
            "filter": {k: v for k, v in args.items() if k in filter_fields and v is not None},
            "option": {"prices": [prices_option]},
        }
        result = await self.client.post(f"{BASE}/prices/search", body)
        return apply_fields(result, args)

    async def search_price_tables(self, args: dict[str, Any]) -> Any:
        """POST /price-tables/search."""
        args = inject_branch_defaults(args)
        filter_fields = {
            "productCodeList", "referenceCodeList", "productName", "groupCodeList",
            "startProductCode", "endProductCode", "classifications",
        }
        branch_codes = args.get("branchCodeList") or ([args["branchCode"]] if args.get("branchCode") else None)
        if not branch_codes:
            raise ValueError("branchCode ou branchCodeList é obrigatório.")
        price_table_code = args.get("priceTableCode")
        if not price_table_code:
            raise ValueError("priceTableCode é obrigatório.")
        body: dict[str, Any] = {
            "filter": {k: v for k, v in args.items() if k in filter_fields and v is not None},
            "option": {"branchCodeList": branch_codes, "priceTableCode": int(price_table_code)},
        }
        if args.get("page"):
            body["page"] = args["page"]
        if args.get("pageSize"):
            body["pageSize"] = args["pageSize"]
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE}/price-tables/search", body)
        return apply_fields(result, args)

    async def get_price_tables_headers(self, args: dict[str, Any]) -> Any:
        """GET /price-tables-headers."""
        args = inject_branch_defaults(args)
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/price-tables-headers", params=params or None)

    async def search_costs(self, args: dict[str, Any]) -> Any:
        """POST /costs/search."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE}/costs/search", body)
        return apply_fields(result, args)

    async def search_references(self, args: dict[str, Any]) -> Any:
        """POST /references/search — Consulta referências."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE}/references/search", body)
        return apply_fields(result, args)

    async def get_grid(self, args: dict[str, Any]) -> Any:
        """GET /grid."""
        args = inject_branch_defaults(args)
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/grid", params=params or None)

    async def get_category(self, args: dict[str, Any]) -> Any:
        """GET /category."""
        args = inject_branch_defaults(args)
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/category", params=params or None)

    async def search_colors(self, args: dict[str, Any]) -> Any:
        """POST /colors/search."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE}/colors/search", body)
        return apply_fields(result, args)

    async def get_classifications(self, args: dict[str, Any]) -> Any:
        """GET /classifications — Consulta classificações (método GET)."""
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/classifications", params=params or None)

    async def search_batch(self, args: dict[str, Any]) -> Any:
        """POST /batch/search."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE}/batch/search", body)
        return apply_fields(result, args)

    async def get_measurement_units(self, args: dict[str, Any]) -> Any:
        """GET /measurement-unit."""
        return await self.client.get(f"{BASE}/measurement-unit")

    async def get_kardex_movement(self, args: dict[str, Any]) -> Any:
        """GET /kardex-movement."""
        args = inject_branch_defaults(args)
        params = {k: v for k, v in args.items() if v is not None}
        return await self.client.get(f"{BASE}/kardex-movement", params=params or None)

    async def search_compositions(self, args: dict[str, Any]) -> Any:
        """POST /compositions."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order", "fields") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        result = await self.client.post(f"{BASE}/compositions", body)
        return apply_fields(result, args)

    async def search_omni_changed_balances(self, args: dict[str, Any]) -> Any:
        """POST /omni-changed-balances."""
        args = inject_branch_defaults(args)
        flt = {k: v for k, v in args.items() if k not in ("page", "pageSize", "order") and v is not None}
        body: dict[str, Any] = {"filter": flt, "page": args.get("page", 1), "pageSize": args.get("pageSize", 100)}
        if args.get("order"):
            body["order"] = args["order"]
        return await self.client.post(f"{BASE}/omni-changed-balances", body)

    # ── WRITE ─────────────────────────────────────────────────────────────

    async def update_product_price(self, args: dict[str, Any]) -> Any:
        """⚠️ DEPRECATED em v3.1 — use update_product_price_only ou update_product_cost.

        Mantida por retrocompatibilidade. Detecta valueType e delega.
        Aceita aliases 'P'/'C' como atalhos de 'Price'/'Cost'.
        Sem valueType, assume 'Price' (default histórico).
        """
        args = dict(args)
        vt = normalize_value_type(args.get("valueType"))
        if vt == "Cost":
            return await self.update_product_cost(args)
        return await self.update_product_price_only(args)

    async def update_product_price_only(self, args: dict[str, Any]) -> Any:
        """POST /values/update — ⚠️ Atualiza PREÇO DE VENDA. valueType='Price' injetado.

        Faz upsert: tenta UPDATE; se NotFound, faz CREATE.
        """
        return await self._upsert_product_value(args, value_type="Price")

    async def update_product_cost(self, args: dict[str, Any]) -> Any:
        """POST /values/update — ⚠️ Atualiza CUSTO. valueType='Cost' injetado.

        Faz upsert: tenta UPDATE; se NotFound, faz CREATE.
        """
        return await self._upsert_product_value(args, value_type="Cost")

    async def _upsert_product_value(self, args: dict[str, Any], value_type: str) -> Any:
        """Helper interno para upsert de Price ou Cost.

        Força valueType ao tipo passado (sobrescreve qualquer coisa que vier).
        """
        args = inject_branch_defaults(args)
        branch = args.get("branchCode")

        if args.get("products"):
            products = args["products"]
            for p in products:
                for v in p.get("values", []):
                    v["valueType"] = value_type
                    if "branchCode" not in v and branch is not None:
                        v["branchCode"] = branch
        else:
            if not all(k in args for k in ("productCode", "valueCode", "value")):
                raise ValueError(
                    "Modo simples requer productCode, valueCode e value. "
                    "Para lote use products=[{productCode, values:[...]}]"
                )
            products = [{
                "productCode": args["productCode"],
                "values": [{
                    "branchCode": branch,
                    "valueType": value_type,
                    "valueCode": args["valueCode"],
                    "value": args["value"],
                }]
            }]

        body = {"products": products}
        return await self.client.upsert(
            update_path=f"{BASE}/values/update",
            create_path=f"{BASE}/values/create",
            body=body,
        )

    async def update_promotion_price(self, args: dict[str, Any]) -> Any:
        """POST /promotion-values/update — ⚠️ Altera preço de promoção."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/promotion-values/update", body)

    async def update_product_data(self, args: dict[str, Any]) -> Any:
        """⚠️ Atualiza dados de produto (peso, NCM, CST, etc).

        Auto-roteamento:
        - Se passar productCode (singular) → PUT /products/{code}/{branchCode} (simples)
        - Se passar productCodeList ou outros filtros → PUT /data (lote)

        Endpoint simples valida em produção pela MOOUI (alterar_peso.py).
        """
        args = inject_branch_defaults(args)

        # Modo simples
        if args.get("productCode") and not args.get("productCodeList"):
            code = args["productCode"]
            branch = args["branchCode"]
            excluded = {"productCode", "branchCode", "productCodeList",
                       "barCodeList", "groupCode", "referenceCode"}
            body = {k: v for k, v in args.items()
                    if k not in excluded and v is not None}
            return await self.client.put(
                f"{BASE}/products/{code}/{branch}", body
            )

        # Modo batch
        filter_keys = {"productCodeList", "barCodeList",
                       "groupCode", "referenceCode"}
        flt = {}
        payload = {}
        for k, v in args.items():
            if v is None:
                continue
            if k == "branchCode":
                continue
            if k in filter_keys:
                flt[k] = v
            else:
                payload[k] = v

        if not flt:
            raise ValueError(
                "Modo batch requer pelo menos um filtro: "
                "productCodeList, barCodeList, groupCode ou referenceCode."
            )

        body = {"filter": flt, **payload}
        return await self.client.put(f"{BASE}/data", body)

    async def update_product_simple(self, args: dict[str, Any]) -> Any:
        """PUT /products/{code}/{branchCode} — ⚠️ Update unitário simples.

        Endpoint validado pela MOOUI em produção.
        """
        args = inject_branch_defaults(args)
        if not args.get("productCode"):
            raise ValueError("update_product_simple requer productCode.")

        code = args["productCode"]
        branch = args["branchCode"]
        excluded = {"productCode", "branchCode", "productCodeList"}
        body = {k: v for k, v in args.items()
                if k not in excluded and v is not None}

        return await self.client.put(f"{BASE}/products/{code}/{branch}", body)

    async def update_product_branch_info_batch(self, args: dict[str, Any]) -> Any:
        """PUT /branch-info/{branchCode} — ⚠️ Atualização em lote por filial."""
        args = inject_branch_defaults(args)
        branch = args["branchCode"]

        filter_keys = {"productCodeList", "barCodeList",
                       "groupCode", "referenceCode"}
        flt = {}
        payload = {}
        for k, v in args.items():
            if v is None:
                continue
            if k in ("branchCode",):
                continue
            if k in filter_keys:
                flt[k] = v
            else:
                payload[k] = v

        if not flt:
            raise ValueError(
                "update_product_branch_info_batch requer pelo menos um "
                "filtro: productCodeList, barCodeList, groupCode ou referenceCode."
            )

        body = {"filter": flt, **payload}
        return await self.client.put(f"{BASE}/branch-info/{branch}", body)

    async def create_barcode(self, args: dict[str, Any]) -> Any:
        """POST /barcodes — ⚠️ Inclui código de barras."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/barcodes", body)

    async def update_barcode(self, args: dict[str, Any]) -> Any:
        """POST /barcodes/update — ⚠️ Altera código de barras existente. NEW in v2.3."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/barcodes/update", body)

    async def create_batch(self, args: dict[str, Any]) -> Any:
        """POST /batch/create — ⚠️ Inclui lote e item de lote."""
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/batch/create", body)

    async def create_reference(self, args: dict[str, Any]) -> Any:
        """POST /references — ⚠️ Inclui nova referência de produto. NEW in v2.3.

        Body fields per InsertReferenceCommand — common ones:
        referenceCode, description, categoryCode, colorCode, grid, etc.
        """
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/references", body)

    async def create_classification_type(self, args: dict[str, Any]) -> Any:
        """POST /classifications — ⚠️ Cria tipo de classificação de produto. NEW in v2.3.

        Não confundir com GET /classifications (consulta). Este POST é para
        criar um novo TIPO de classificação (agrupador), não vincular produtos.
        """
        body = {k: v for k, v in args.items() if v is not None}
        return await self.client.post(f"{BASE}/classifications", body)

    async def create_classification_relationship(self, args: dict[str, Any]) -> Any:
        """POST /classification-relationship/create — ⚠️ Vincula classificações a produtos.
        Fallback automático para UPDATE se AlreadyExist."""
        type_code  = args["typeCode"]
        class_code = str(args["classificationCode"])
        ref_id     = args.get("referenceId", 0)

        def build_products(codes: list) -> list:
            return [
                {"productCode": int(pc), "referenceId": ref_id,
                 "classifications": [{"typeCode": type_code, "code": class_code}]}
                for pc in codes
            ]

        all_codes = list(args["productCodeList"])

        try:
            return await self.client.post(
                f"{BASE}/classification-relationship/create",
                {"products": build_products(all_codes)},
            )
        except Exception as create_err:
            err_str = str(create_err)
            import re
            already_codes = set(
                int(m) for m in re.findall(r"ProductCode (\d+) TypeCode \d+ already exist", err_str)
            )
            new_codes = [c for c in all_codes if int(c) not in already_codes]

            results: dict[str, Any] = {}
            if new_codes:
                try:
                    results["created"] = await self.client.post(
                        f"{BASE}/classification-relationship/create",
                        {"products": build_products(new_codes)},
                    )
                except Exception as e:
                    results["created_error"] = str(e)

            if already_codes:
                try:
                    results["updated"] = await self.client.post(
                        f"{BASE}/classification-relationship/update",
                        {"products": build_products(list(already_codes))},
                    )
                except Exception as e:
                    results["updated_error"] = str(e)

            results["summary"] = {
                "total": len(all_codes),
                "created": len(new_codes),
                "updated": len(already_codes),
            }
            return results

    async def create_product_value(self, args: dict[str, Any]) -> Any:
        """POST /values/create — ⚠️ Inclui preço/custo novo."""
        args = inject_branch_defaults(args)
        value_item: dict[str, Any] = {
            "branchCode": args["branchCode"],
            "valueCode": args["valueCode"],
            "value": args["value"],
        }
        if args.get("valueType") is not None:
            value_item["valueType"] = args["valueType"]
        body = {"products": [{"productCode": args["productCode"], "values": [value_item]}]}
        return await self.client.post(f"{BASE}/values/create", body)
