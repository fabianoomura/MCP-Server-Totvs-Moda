"""
Regression tests for bugs found in Phase 1 review + contract tests for tools.

Every bug we fixed has a test here — if someone reintroduces the bug,
CI catches it before it reaches production.
"""
import pytest
import respx
from httpx import Response

from tools.sales_order import SalesOrderTools
from tools.product import ProductTools
from tools.person import PersonTools
from tools.accounts_receivable import AccountsReceivableTools
from tools.voucher import VoucherTools
from tools.image import ImageTools
from tools.logistics import LogisticsTools
from tools.general import GeneralTools
from tools.seller import SellerTools
from tools.convenience import ConvenienceTools
from tools.account_payable import AccountPayableTools
from tools.purchase_order import PurchaseOrderTools
from tools.product_engineering import ProductEngineeringTools
from tools.material_request import MaterialRequestTools
from tools.product_prototype import ProductPrototypeTools
from tools.other_modules import ProductionOrderTools
from tools.analytics import AnalyticsTools

from conftest import TOTVS_BASE, TOKEN_URL


def _mock_token():
    return respx.post(TOKEN_URL).mock(
        return_value=Response(
            200,
            json={"access_token": "fake-token", "expires_in": 3600, "token_type": "Bearer"},
        )
    )


def _body(route):
    import json
    return json.loads(route.calls.last.request.content)


@pytest.mark.asyncio
@respx.mock
async def test_analytics_gateway_get_uses_registered_endpoint_and_params(client):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/analytics/v2/branch-sale").mock(
        return_value=Response(200, json={"items": [{"branchCode": 1, "value": 10, "ignored": True}]})
    )

    tools = AnalyticsTools(client)
    result = await tools.call_endpoint({
        "endpoint": "analytics_v2_branch_sale",
        "params": {"Page": 1, "PageSize": 10},
        "fields": ["branchCode", "value"],
    })

    assert route.called
    params = route.calls.last.request.url.params
    assert params["Page"] == "1"
    assert params["PageSize"] == "10"
    assert result == {"items": [{"branchCode": 1, "value": 10}]}


@pytest.mark.asyncio
@respx.mock
async def test_analytics_gateway_post_uses_registered_endpoint_and_body(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/financial-panel/v2/total-payable/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = AnalyticsTools(client)
    body = {"filter": {"branchCodeList": [1]}, "page": 1, "pageSize": 100}
    await tools.call_endpoint({"endpoint": "financial_panel_v2_total_payable_search", "body": body})

    assert route.called
    assert _body(route) == body


@pytest.mark.asyncio
async def test_analytics_gateway_rejects_unknown_endpoint(client):
    tools = AnalyticsTools(client)
    with pytest.raises(ValueError, match="Endpoint Analytics desconhecido"):
        await tools.call_endpoint({"endpoint": "nao_existe"})


@pytest.mark.asyncio
async def test_pending_material_consumption_requires_material_filter(client):
    tools = ProductionOrderTools(client)
    with pytest.raises(ValueError, match="rawMaterialCodeList"):
        await tools.get_pending_material_consumption({"branchCodeList": [1]})


@pytest.mark.asyncio
@respx.mock
async def test_group_duplicates_posts_contract_body(client):
    """Contract: group-duplicates is a write endpoint used for freight/logistics grouping."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/accounts-payable/v2/group-duplicates").mock(
        return_value=Response(200, json={"success": True})
    )

    tools = AccountPayableTools(client)
    args = {
        "branchCnpj": "21833409000169",
        "supplierCpfCnpj": "12345678000199",
        "duplicateCode": 10001,
        "document": 18,
        "dueDate": "2026-06-10T00:00:00",
        "groupInstallments": [
            {
                "branchCnpj": "21833409000169",
                "supplierCpfCnpj": "12345678000199",
                "duplicateCode": 90001,
                "installmentCode": 1,
            }
        ],
    }

    await tools.group_duplicates(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
async def test_create_receivable_invoice_posts_contract_body(client):
    """Contract: InsertInvoiceCommand is exposed as a guarded write tool."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/accounts-receivable/v2/invoices").mock(
        return_value=Response(200, json={"success": True})
    )

    tools = AccountsReceivableTools(client)
    args = {
        "branchCnpj": "21833409000169",
        "customerCpfCnpj": "12345678901",
        "receivableCode": 70001,
        "installments": [
            {
                "installmentCode": 1,
                "documentType": 1,
                "billingType": 2,
                "chargeType": 1,
                "bearerCode": 10,
                "issueDate": "2026-05-23T00:00:00",
                "expiredDate": "2026-06-23T00:00:00",
                "installmentValue": 199.9,
            }
        ],
    }

    await tools.create_invoice(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
async def test_product_classification_create_falls_back_to_update_when_all_exist(client):
    _mock_token()
    create_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/classification-relationship/create").mock(
        return_value=Response(
            400,
            json={"messages": [{"code": "AlreadyExist", "message": "ProductCode 10001 TypeCode 11 already exist"}]},
        )
    )
    update_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/classification-relationship/update").mock(
        return_value=Response(200, json={"updated": True})
    )

    tools = ProductTools(client)
    result = await tools.create_classification_relationship({
        "productCodeList": [10001],
        "typeCode": 11,
        "classificationCode": "7",
    })

    assert create_route.called
    assert update_route.called
    assert result["summary"] == {"total": 1, "created": 0, "updated": 1}
    assert _body(update_route) == {
        "products": [
            {"productCode": 10001, "referenceId": 0, "classifications": [{"typeCode": 11, "code": "7"}]}
        ]
    }


@pytest.mark.asyncio
@respx.mock
async def test_product_classification_create_splits_mixed_existing_and_new(client):
    _mock_token()
    create_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/classification-relationship/create").mock(
        side_effect=[
            Response(
                400,
                json={"messages": [{"code": "AlreadyExist", "message": "ProductCode 10001 TypeCode 11 already exist"}]},
            ),
            Response(201, json={"created": True}),
        ]
    )
    update_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/classification-relationship/update").mock(
        return_value=Response(200, json={"updated": True})
    )

    tools = ProductTools(client)
    result = await tools.create_classification_relationship({
        "productCodeList": [10001, 10002],
        "typeCode": 11,
        "classificationCode": "7",
    })

    assert create_route.call_count == 2
    assert update_route.called
    assert result["summary"] == {"total": 2, "created": 1, "updated": 1}
    assert _body(create_route) == {
        "products": [
            {"productCode": 10002, "referenceId": 0, "classifications": [{"typeCode": 11, "code": "7"}]}
        ]
    }
    assert _body(update_route) == {
        "products": [
            {"productCode": 10001, "referenceId": 0, "classifications": [{"typeCode": 11, "code": "7"}]}
        ]
    }


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("method_name", "path", "args", "expected"),
    [
        (
            "get_additional_field_types",
            "/api/totvsmoda/product/v2/additional-fields-types",
            {"codeList": [1, 2], "description": "COR", "order": "-code", "page": 2, "pageSize": 50},
            {"CodeList": ["1", "2"], "Description": "COR", "Order": "-code", "Page": "2", "PageSize": "50"},
        ),
        (
            "get_classification_types",
            "/api/totvsmoda/product/v2/classificationType",
            {"classificationTypeList": [11], "isGroup": True, "order": "code", "page": 1, "pageSize": 10},
            {"ClassificationTypeList": ["11"], "IsGroup": "true", "Order": "code", "Page": "1", "PageSize": "10"},
        ),
        (
            "get_product_grouper_configurations",
            "/api/totvsmoda/product/v2/product-grouper-configuration",
            {"grouperCodeList": [7], "order": "-grouperCode", "page": 1, "pageSize": 10},
            {"GrouperCodeList": ["7"], "Order": "-grouperCode", "Page": "1", "PageSize": "10"},
        ),
        (
            "get_instruction_items",
            "/api/totvsmoda/product/v2/instruction-items",
            {"codeList": [5], "grouperCodeList": [7], "description": "lavar", "expand": "image,globalImage"},
            {"CodeList": ["5"], "GrouperCodeList": ["7"], "Description": "lavar", "Expand": "image,globalImage"},
        ),
        (
            "get_price_table_scales",
            "/api/totvsmoda/product/v2/price-table-scales",
            {"scaleCodeList": [1], "priceTableCodeList": [2], "page": 1, "pageSize": 10},
            {"ScaleCodeList": ["1"], "PriceTableCodeList": ["2"], "Page": "1", "PageSize": "10"},
        ),
        (
            "get_composition_product",
            "/api/totvsmoda/product/v2/composition-product",
            {"productCodeList": [14679], "page": 1, "pageSize": 10},
            {"ProductCodeList": ["14679"], "Page": "1", "PageSize": "10"},
        ),
        (
            "get_composition_group_product",
            "/api/totvsmoda/product/v2/composition-group-product",
            {"referenceCodeList": ["REF-1"], "page": 1, "pageSize": 10},
            {"ReferenceCodeList": ["REF-1"], "Page": "1", "PageSize": "10"},
        ),
    ],
)
async def test_product_auxiliary_get_endpoints_use_pascal_query(client, method_name, path, args, expected):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}{path}").mock(return_value=Response(200, json={"items": []}))

    tools = ProductTools(client)
    await getattr(tools, method_name)(args)

    assert route.called
    params = route.calls.last.request.url.params
    for key, value in expected.items():
        if isinstance(value, list):
            assert params.get_list(key) == value
        else:
            assert params[key] == value


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["get_composition_product", "get_composition_group_product"])
async def test_product_composition_get_requires_filter(client, method_name):
    tools = ProductTools(client)
    with pytest.raises(ValueError, match="productCodeList"):
        await getattr(tools, method_name)({})


@pytest.mark.asyncio
@respx.mock
async def test_general_search_transactions_uses_official_query_params(client):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/general/v2/transactions/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = GeneralTools(client)
    await tools.search_transactions({
        "branchCode": 1,
        "transactionCodeList": [9001],
        "customerCpfCnpjList": ["12345678000199"],
        "expand": "originDestination,additionalInformation",
        "order": "-transactionCode",
        "page": 2,
        "pageSize": 50,
        "fields": ["transactionCode"],
    })

    assert route.called
    query = route.calls.last.request.url.params
    assert query.get_list("BranchCodeList") == ["1"]
    assert query.get_list("TransactionCodeList") == ["9001"]
    assert query.get_list("CustomerCPFCNPJList") == ["12345678000199"]
    assert query["Expand"] == "originDestination,additionalInformation"
    assert query["Order"] == "-transactionCode"
    assert query["Page"] == "2"
    assert query["PageSize"] == "50"
    assert "Fields" not in dict(query)


@pytest.mark.asyncio
@respx.mock
async def test_seller_operational_area_state_uses_pascal_query(client):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/seller/v2/operational-area-state").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = SellerTools(client)
    await tools.get_operational_area_state({
        "operationalAreaCode": 7,
        "startChangeDate": "2026-05-01T00:00:00",
        "order": "-operationalAreaCode,maxChangeFilterDate",
        "page": 1,
        "pageSize": 100,
        "fields": ["stateCode"],
    })

    assert route.called
    query = route.calls.last.request.url.params
    assert query["OperationalAreaCode"] == "7"
    assert query["StartChangeDate"] == "2026-05-01T00:00:00"
    assert query["Order"] == "-operationalAreaCode,maxChangeFilterDate"
    assert query["Page"] == "1"
    assert query["PageSize"] == "100"
    assert "Fields" not in dict(query)


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("method_name", "path", "args"),
    [
        (
            "create_financial_compensation",
            "/api/totvsmoda/general/v2/financial-compensations",
            {"branchCode": 1, "items": [{"value": 10.5}]},
        ),
        (
            "add_product_count_additional_count",
            "/api/totvsmoda/general/v2/product-counts/additional-count",
            {"branchCode": 1, "countNumber": 99, "items": [{"productCode": 10001, "quantity": 2}]},
        ),
        (
            "create_relationship_counts",
            "/api/totvsmoda/general/v2/relationship-counts",
            {"branchCode": 1, "transactionCode": 123, "transactionDate": "2026-05-24", "counts": [{"countNumber": 99}]},
        ),
        (
            "create_transaction_classification_relationship",
            "/api/totvsmoda/general/v2/transaction-classification-relationship/create",
            {
                "branchCode": 1,
                "transactionCode": 123,
                "transactionDate": "2026-05-24",
                "classifications": [{"typeCode": 11, "code": "7"}],
            },
        ),
    ],
)
async def test_general_write_contracts_post_exact_body(client, method_name, path, args):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}{path}").mock(return_value=Response(200, json={"ok": True}))

    tools = GeneralTools(client)
    await getattr(tools, method_name)(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("method_name", "path", "args"),
    [
        (
            "link_purchase_order_batch",
            "/api/totvsmoda/purchase-order/v2/purchase-order/batch-link",
            {
                "branchCode": 1,
                "batchCode": 700,
                "sequence": 1,
                "orderCode": 120040,
                "invoice": {"branchCode": 1, "invoiceSequence": 143218},
            },
        ),
        (
            "update_purchase_order_item_quantities",
            "/api/totvsmoda/purchase-order/v2/quantity-items",
            {
                "branchCode": 1,
                "orderCode": 120040,
                "items": [{"productCode": 1000258, "quantity": 12.5}],
            },
        ),
    ],
)
async def test_purchase_order_write_contracts_post_exact_body(client, method_name, path, args):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}{path}").mock(return_value=Response(200, json={"ok": True}))

    tools = PurchaseOrderTools(client)
    await getattr(tools, method_name)(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("method_name", "method", "path", "args"),
    [
        (
            "update_batch_info",
            "put",
            "/api/totvsmoda/product/v2/batch-info",
            {"branchCode": 1, "batchCode": 700, "sequence": 1, "weight": 12.5},
        ),
        (
            "create_batch_preferential_sales_order",
            "post",
            "/api/totvsmoda/product/v2/batch-preferentialsalesorder",
            {"branchCode": 1, "batchCode": 700, "sequence": 1, "orderCode": 120358},
        ),
        (
            "upsert_color",
            "post",
            "/api/totvsmoda/product/v2/colors",
            {"code": "AZUL", "description": "Azul"},
        ),
        (
            "create_grid",
            "post",
            "/api/totvsmoda/product/v2/grids",
            {"gridCode": 10, "description": "Grade teste", "sizes": [{"sequence": 1, "sizeName": "P"}]},
        ),
    ],
)
async def test_product_remaining_write_contracts_use_exact_body(client, method_name, method, path, args):
    _mock_token()
    route = getattr(respx, method)(f"{TOTVS_BASE}{path}").mock(return_value=Response(200, json={"ok": True}))

    tools = ProductTools(client)
    await getattr(tools, method_name)(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("method_name", "path", "args"),
    [
        (
            "create_pdv_transaction",
            "/api/totvsmoda/sales-order/v2/pdv-transactions",
            {"branchCode": 1, "orderCode": 120358, "transactions": [{"transactionCode": 99}]},
        ),
        (
            "create_relationship_batch_items",
            "/api/totvsmoda/sales-order/v2/relationship-batch-items",
            {"branchCode": 1, "orderCode": 120358, "items": [{"productCode": 14679, "batchCode": 700}]},
        ),
        (
            "suggest_batch_items_by_nuance",
            "/api/totvsmoda/sales-order/v2/suggest-batch-items-nuance",
            {"branchCode": 1, "orderCode": 120358, "items": [{"productCode": 14679}]},
        ),
    ],
)
async def test_sales_order_remaining_write_contracts_post_exact_body(client, method_name, path, args):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}{path}").mock(return_value=Response(200, json={"ok": True}))

    tools = SalesOrderTools(client)
    await getattr(tools, method_name)(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
async def test_product_engineering_references_posts_exact_body(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product-engineering/v2/references").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = ProductEngineeringTools(client)
    args = {"branchCode": 1, "references": [{"referenceCode": "REF-TESTE"}]}
    await tools.create_references_from_engineering(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
async def test_person_remove_classification_relationship_posts_exact_body(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/classification-relationship/remove").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = PersonTools(client)
    args = {"personCode": 5066, "classifications": [{"typeCode": 11, "code": "7"}]}
    await tools.remove_classification_relationship(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
async def test_pay_invoices_accepts_numeric_paid_type(client):
    """Contract: InvoicesPaymentCommand uses numeric paidType values 1-5."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/accounts-receivable/v2/invoices-payment").mock(
        return_value=Response(200, json={"success": True})
    )

    tools = AccountsReceivableTools(client)
    args = {
        "branchCode": 1,
        "settlementDate": "2026-05-23T00:00:00",
        "invoices": [
            {
                "branchCode": 1,
                "customerCode": 5066,
                "receivableCode": 70001,
                "installmentCode": 1,
                "paidValue": 199.9,
            }
        ],
        "payments": [{"value": 199.9, "paidType": 3}],
    }

    await tools.pay_invoices(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
async def test_product_engineering_services_wraps_filter(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product-engineering/v2/services/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = ProductEngineeringTools(client)
    await tools.search_services({
        "serviceCodeList": [10],
        "expand": "dataProviders,dataLevelGroup",
        "page": 2,
        "pageSize": 50,
    })

    assert route.called
    body = _body(route)
    assert body["filter"]["serviceCodeList"] == [10]
    assert body["expand"] == "dataProviders,dataLevelGroup"
    assert body["page"] == 2
    assert body["pageSize"] == 50


@pytest.mark.asyncio
@respx.mock
async def test_product_engineering_services_requires_filter(client):
    tools = ProductEngineeringTools(client)
    with pytest.raises(ValueError, match="ao menos um filtro"):
        await tools.search_services({"page": 1, "pageSize": 1})


@pytest.mark.asyncio
@respx.mock
async def test_product_engineering_get_operations_uses_pascal_query(client):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/product-engineering/v2/operations").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = ProductEngineeringTools(client)
    await tools.get_operations({"operationCodeList": [7], "page": 3, "pageSize": 20})

    assert route.called
    params = dict(route.calls.last.request.url.params)
    assert params["OperationCodeList"] == "7"
    assert params["Page"] == "3"
    assert params["PageSize"] == "20"


@pytest.mark.asyncio
@respx.mock
async def test_product_engineering_applications_uses_pascal_query(client):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/product-engineering/v2/applications/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = ProductEngineeringTools(client)
    await tools.search_applications({"applicationCodeList": [2], "order": "applicationCode"})

    assert route.called
    params = dict(route.calls.last.request.url.params)
    assert params["ApplicationCodeList"] == "2"
    assert params["Order"] == "applicationCode"


@pytest.mark.asyncio
@respx.mock
async def test_product_engineering_default_posts_contract_body(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product-engineering/v2/engineering-default/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = ProductEngineeringTools(client)
    args = {"productCodeList": [14679], "page": 1, "pageSize": 10}
    await tools.search_engineering_default(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
async def test_product_engineering_configurations_uses_pascal_query(client):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/product-engineering/v2/engineering-configurations").mock(
        return_value=Response(200, json=[])
    )

    tools = ProductEngineeringTools(client)
    await tools.get_engineering_configurations({
        "branchCode": 1,
        "purposeType": 1,
        "classificationCodeList": ["A"],
        "classificationType": 11,
    })

    assert route.called
    params = dict(route.calls.last.request.url.params)
    assert params["BranchCode"] == "1"
    assert params["PurposeType"] == "1"
    assert params["ClassificationCodeList"] == "A"
    assert params["ClassificationType"] == "11"


@pytest.mark.asyncio
@respx.mock
async def test_search_material_requests_wraps_filter(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/material-request/v2/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = MaterialRequestTools(client)
    await tools.search_material_requests({
        "branchCodeList": [1],
        "statusTypeList": [0, 1, 3],
        "expand": "items,classifications,observations",
        "order": "-requestDate,requestCode",
        "page": 2,
        "pageSize": 50,
    })

    assert route.called
    body = _body(route)
    assert body["filter"]["branchCodeList"] == [1]
    assert body["filter"]["statusTypeList"] == [0, 1, 3]
    assert body["expand"] == "items,classifications,observations"
    assert body["order"] == "-requestDate,requestCode"
    assert body["page"] == 2
    assert body["pageSize"] == 50


@pytest.mark.asyncio
@respx.mock
async def test_search_material_requests_accepts_filter_object(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/material-request/v2/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = MaterialRequestTools(client)
    await tools.search_material_requests({
        "filter": {"branchCodeList": [1], "requestCodeList": [123]},
        "page": 1,
        "pageSize": 10,
    })

    assert route.called
    body = _body(route)
    assert body["filter"] == {"branchCodeList": [1], "requestCodeList": [123]}


@pytest.mark.asyncio
@respx.mock
async def test_create_material_request_posts_contract_body(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/material-request/v2/requests").mock(
        return_value=Response(201, json={"materialRequestCode": "1-2026-05-24-9001"})
    )

    tools = MaterialRequestTools(client)
    args = {
        "branchCode": 1,
        "requestDate": "2026-05-24",
        "purposeCode": 10,
        "requester": 123456,
        "costCenter": 987,
        "bridgeCode": "MCP-REQ-001",
        "items": [
            {
                "sequence": 1,
                "productCode": 1000258,
                "requestQuantity": 12.5,
                "costCenter": 987,
                "expense": 55,
                "cost": 3.1415,
            }
        ],
        "observations": [{"observation": "Criada via teste mock MCP"}],
    }

    await tools.create_material_request(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("method_name", "path", "args"),
    [
        (
            "add_items",
            "/api/totvsmoda/material-request/v2/items",
            {
                "branchCode": 1,
                "requestDate": "2026-05-24",
                "requestCode": 9001,
                "items": [{"sequence": 2, "productCode": 1000258, "requestQuantity": 3}],
            },
        ),
        (
            "modify_header",
            "/api/totvsmoda/material-request/v2/headers/modify",
            {"branchCode": 1, "requestDate": "2026-05-24", "requestCode": 9001, "purposeCode": 11, "costCenter": 987},
        ),
        (
            "modify_items",
            "/api/totvsmoda/material-request/v2/items/modify",
            {
                "branchCode": 1,
                "requestDate": "2026-05-24",
                "requestCode": 9001,
                "items": [{"sequence": 1, "productCode": 1000258, "requestQuantity": 5}],
            },
        ),
        (
            "remove_items",
            "/api/totvsmoda/material-request/v2/items/remove",
            {"integrationCode": "1-2026-05-24-9001", "items": [{"sequence": 1}]},
        ),
        (
            "cancel_items",
            "/api/totvsmoda/material-request/v2/items/cancel",
            {
                "branchCode": 1,
                "requestDate": "2026-05-24",
                "requestCode": 9001,
                "items": [{"sequence": 1, "cancelQuantity": 2, "reason": 7, "descriptions": [{"description": "Cancelado via teste"}]}],
            },
        ),
        (
            "approve",
            "/api/totvsmoda/material-request/v2/approve",
            {
                "branchCode": 1,
                "requestDate": "2026-05-24",
                "requestCode": 9001,
                "approverUser": 321,
                "approved": True,
                "reportDescription": "Aprovado via teste",
            },
        ),
        (
            "move_items",
            "/api/totvsmoda/material-request/v2/items/movement",
            {
                "integrationCode": "1-2026-05-24-9001",
                "operationCode": 101,
                "items": [{"sequence": 1, "movementQuantity": 1.5, "batchItems": [{"barCode": "ABC", "movementQuantity": 1.5}]}],
                "descriptions": [{"description": "Baixa via teste"}],
            },
        ),
    ],
)
async def test_material_request_write_contracts_post_exact_body(client, method_name, path, args):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}{path}").mock(return_value=Response(200, json={"success": True}))

    tools = MaterialRequestTools(client)
    await getattr(tools, method_name)(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
async def test_search_product_prototypes_posts_contract_body(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product-prototype/v2/prototypes/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = ProductPrototypeTools(client)
    await tools.search_prototypes({
        "branchCode": 1,
        "prototypeCodeList": [100, 101],
        "expand": "Destiny",
        "page": 2,
        "pageSize": 50,
    })

    assert route.called
    assert _body(route) == {
        "branchCode": 1,
        "prototypeCodeList": [100, 101],
        "expand": "Destiny",
        "page": 2,
        "pageSize": 50,
    }


@pytest.mark.asyncio
async def test_search_product_prototypes_requires_code_list(client):
    tools = ProductPrototypeTools(client)
    with pytest.raises(ValueError, match="prototypeCodeList"):
        await tools.search_prototypes({"branchCode": 1, "page": 1, "pageSize": 1})


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("method_name", "path"),
    [
        ("create_prototype", "/api/totvsmoda/product-prototype/v2/prototypes"),
        ("update_prototype", "/api/totvsmoda/product-prototype/v2/prototypes/update"),
    ],
)
async def test_product_prototype_write_contracts_post_exact_body(client, method_name, path):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}{path}").mock(return_value=Response(200, json={"success": True}))

    tools = ProductPrototypeTools(client)
    args = {
        "branchCode": 1,
        "code": 9001,
        "prototypeDescription": "Protótipo MCP",
        "customerCode": 5066,
        "estimatedStart": "2026-05-24",
        "estimatedDeliveryDate": "2026-06-15",
        "gridCode": 10,
        "services": [{"serviceCode": 1, "applicationCode": 2, "quantity": 1, "value": 12.3}],
        "rawMaterials": [{"productCode": 1000258, "applicationCode": 1, "quantity": 2.5}],
        "classifications": [{"typeCode": 11, "code": "7"}],
        "additionalProductFields": [{"code": 1, "value": "MCP"}],
        "compositions": [{"code": 123}],
    }

    await getattr(tools, method_name)(args)

    assert route.called
    assert _body(route) == args


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 BUG #1 — update_product_data must use PUT, not POST
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_person_contact_types_uses_pascal_query(client):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/person/v2/contact-types").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = PersonTools(client)
    await tools.get_contact_types({
        "typeCodeList": [1, 2],
        "startChangeDate": "2026-05-01T00:00:00",
        "order": "-code",
        "page": 2,
        "pageSize": 50,
    })

    assert route.called
    query = route.calls.last.request.url.params
    params = dict(query)
    assert query.get_list("TypeCodeList") == ["1", "2"]
    assert params["StartChangeDate"] == "2026-05-01T00:00:00"
    assert params["Order"] == "-code"
    assert params["Page"] == "2"
    assert params["PageSize"] == "50"


@pytest.mark.asyncio
@respx.mock
async def test_person_reception_sale_uses_pascal_query(client):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/person/v2/reception-sale/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = PersonTools(client)
    await tools.search_reception_sale({
        "startMovementDate": "2026-05-24T00:00:00",
        "endMovementDate": "2026-05-24T23:59:59",
        "receptionTypeList": ["L", "P"],
        "page": 1,
        "pageSize": 100,
    })

    assert route.called
    query = route.calls.last.request.url.params
    params = dict(query)
    assert params["StartMovementDate"] == "2026-05-24T00:00:00"
    assert params["EndMovementDate"] == "2026-05-24T23:59:59"
    assert query.get_list("ReceptionTypeList") == ["L", "P"]
    assert params["Page"] == "1"
    assert params["PageSize"] == "100"


@pytest.mark.asyncio
@respx.mock
async def test_person_relate_customer_representatives_posts_contract_body(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/customer-representatives").mock(
        return_value=Response(201, json={"success": True})
    )

    tools = PersonTools(client)
    args = {"representativeCode": 77, "customerCodeList": [5066, 5067]}
    await tools.relate_customer_representatives(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
async def test_person_relate_customer_representatives_requires_identifiers(client):
    tools = PersonTools(client)
    with pytest.raises(ValueError, match="representativeCode"):
        await tools.relate_customer_representatives({"customerCodeList": [5066]})
    with pytest.raises(ValueError, match="customerCodeList"):
        await tools.relate_customer_representatives({"representativeCode": 77})


@pytest.mark.asyncio
@respx.mock
async def test_person_change_message_puts_contract_body(client):
    _mock_token()
    route = respx.put(f"{TOTVS_BASE}/api/totvsmoda/person/v2/messages/change").mock(
        return_value=Response(200, json={"success": True})
    )

    tools = PersonTools(client)
    args = {
        "filter": {"personCode": 5066, "sequence": 1},
        "description": "Cliente prefere contato por WhatsApp",
        "status": "Read",
        "priority": 2,
    }
    await tools.change_message(args)

    assert route.called
    assert _body(route) == args


@pytest.mark.asyncio
@respx.mock
async def test_person_individual_search_keeps_expand_and_option_outside_filter(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/individuals/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = PersonTools(client)
    await tools.search_individuals({
        "cpfList": ["12345678900"],
        "isCustomer": True,
        "change": {"startDate": "2026-05-01T00:00:00", "inCustomer": True},
        "expand": "phones,addresses,statistics",
        "option": {"branchStaticDataList": [1], "QuantityOcurrenceCustomerObservation": 5},
        "order": "-maxChangeFilterDate,personCode",
        "page": 2,
        "pageSize": 500,
        "fields": ["personCode"],
    })

    assert route.called
    body = _body(route)
    assert body["filter"] == {
        "cpfList": ["12345678900"],
        "isCustomer": True,
        "change": {"startDate": "2026-05-01T00:00:00", "inCustomer": True},
    }
    assert body["expand"] == "phones,addresses,statistics"
    assert body["option"] == {"branchStaticDataList": [1], "QuantityOcurrenceCustomerObservation": 5}
    assert body["order"] == "-maxChangeFilterDate,personCode"
    assert body["page"] == 2
    assert body["pageSize"] == 500


@pytest.mark.asyncio
@respx.mock
async def test_person_legal_search_accepts_official_filter_object(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/legal-entities/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = PersonTools(client)
    await tools.search_legal_entities({
        "filter": {
            "cnpjList": ["12345678000199"],
            "isSupplier": True,
            "classifications": [{"type": 10, "codeList": ["A"]}],
        },
        "expand": "contacts,representatives",
        "option": {"classificationTypeCodeList": [10]},
    })

    assert route.called
    body = _body(route)
    assert body["filter"] == {
        "cnpjList": ["12345678000199"],
        "isSupplier": True,
        "classifications": [{"type": 10, "codeList": ["A"]}],
    }
    assert body["expand"] == "contacts,representatives"
    assert body["option"] == {"classificationTypeCodeList": [10]}
    assert "fields" not in body["filter"]


@pytest.mark.asyncio
@respx.mock
async def test_update_product_data_uses_PUT_not_POST(client):
    """Regression: swagger specifies PUT — POST returns 405.
    v3.1: productCode simples roteia para PUT /products/{code}/{branchCode}."""
    _mock_token()
    # v3.1: modo simples (productCode sem productCodeList) usa endpoint unitário
    put_route = respx.put(f"{TOTVS_BASE}/api/totvsmoda/product/v2/products/123/1").mock(
        return_value=Response(200, json={"updated": True})
    )
    post_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/data")

    tools = ProductTools(client)
    await tools.update_product_data({"productCode": 123, "branchCode": 1, "description": "x"})

    assert put_route.called, "Must use PUT"
    assert not post_route.called, "Must NOT use POST"


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 BUG #2 — image endpoints must match swagger
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_search_product_images_uses_product_search_endpoint(client):
    """Regression: old code used /product-images which doesn't exist.
    Real endpoint is /product/search."""
    _mock_token()
    wrong_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/image/v2/product-images")
    right_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/image/v2/product/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = ImageTools(client)
    await tools.search_product_images({"referenceCode": "REF-1"})

    assert right_route.called
    assert not wrong_route.called


@pytest.mark.asyncio
@respx.mock
async def test_upload_product_image_uses_product_endpoint(client):
    """Regression: real endpoint is POST /image/v2/product, not /product-images."""
    _mock_token()
    right_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/image/v2/product").mock(
        return_value=Response(201, json={"ok": True})
    )

    tools = ImageTools(client)
    await tools.upload_product_image({"imageBase64": "abc123"})

    assert right_route.called


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 BUG #3 — voucher search uses GET, not POST
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_import_image_no_link_uses_imports_endpoint_and_aliases_body(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/image/V2/imports").mock(
        return_value=Response(201, json={"ok": True})
    )

    tools = ImageTools(client)
    await tools.import_image_no_link({"imageBase64": "abc123", "fileName": "foto.jpg"})

    assert route.called
    assert _body(route) == {"base64": "abc123", "name": "foto.jpg"}


@pytest.mark.asyncio
@respx.mock
async def test_upload_person_image_posts_persons_endpoint_and_aliases_body(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/image/v2/persons").mock(
        return_value=Response(201, json={"ok": True})
    )

    tools = ImageTools(client)
    await tools.upload_person_image({
        "imageBase64": "abc123",
        "fileName": "cliente.jpg",
        "personCode": 5066,
        "defaultImage": True,
    })

    assert route.called
    assert _body(route) == {
        "base64": "abc123",
        "name": "cliente.jpg",
        "personCode": 5066,
        "defaultImage": True,
    }


@pytest.mark.asyncio
@respx.mock
async def test_list_person_images_uses_persons_get_query(client):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/image/v2/persons").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = ImageTools(client)
    await tools.list_person_images({"personCode": 5066, "personCpfCnpj": "12345678900", "page": 1, "pageSize": 20})

    assert route.called
    query = route.calls.last.request.url.params
    assert query["PersonCode"] == "5066"
    assert query["CpfCnpj"] == "12345678900"
    assert query["Page"] == "1"
    assert query["PageSize"] == "20"


@pytest.mark.asyncio
@respx.mock
async def test_get_person_image_base64_uses_person_images_endpoint(client):
    _mock_token()
    route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/image/v2/person-images").mock(
        return_value=Response(200, json={"base64": "abc123"})
    )

    tools = ImageTools(client)
    await tools.get_person_image_base64({"imageId": 42})

    assert route.called
    assert route.calls.last.request.url.params["ImageCode"] == "42"


@pytest.mark.asyncio
@respx.mock
async def test_search_voucher_uses_GET_not_POST(client):
    """Regression: swagger says GET /voucher/v2/search with query params."""
    _mock_token()
    post_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/voucher/v2/search")
    get_route = respx.get(f"{TOTVS_BASE}/api/totvsmoda/voucher/v2/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = VoucherTools(client)
    await tools.search_voucher({"voucherCode": "ABC123"})

    assert get_route.called
    assert not post_route.called


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 BUG #4 — change_order_status uses statusOrder field + valid enum
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_change_order_status_sends_statusOrder_field(client):
    """Regression: old code sent 'newStatus' but swagger expects 'statusOrder'."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/change-status").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.change_order_status({
        "branchCode": 1,
        "orderCode": 12345,
        "statusOrder": "BillingReleased",
    })

    assert route.called
    sent_body = route.calls.last.request.content
    import json
    body = json.loads(sent_body)
    assert body.get("statusOrder") == "BillingReleased"
    assert "newStatus" not in body, "Field 'newStatus' must not be in the request"


@pytest.mark.asyncio
@respx.mock
async def test_change_order_status_accepts_legacy_newStatus_alias(client):
    """Backwards-compat: if caller passes old 'newStatus' key, it still works."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/change-status").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.change_order_status({
        "branchCode": 1,
        "orderCode": 12345,
        "newStatus": "Blocked",
    })

    import json
    body = json.loads(route.calls.last.request.content)
    assert body["statusOrder"] == "Blocked", "newStatus should be translated to statusOrder"


@pytest.mark.asyncio
async def test_change_order_status_requires_status(client):
    """If neither statusOrder nor newStatus provided, raise ValueError."""
    tools = SalesOrderTools(client)
    with pytest.raises(ValueError, match="statusOrder"):
        await tools.change_order_status({"branchCode": 1, "orderCode": 12345})


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 BUG #5 — change_charge_type requires customer identifier
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_change_charge_type_requires_customer_identifier(client):
    """If neither customerCode nor customerCpfCnpj provided, raise ValueError."""
    tools = AccountsReceivableTools(client)
    with pytest.raises(ValueError, match="customerCode OU customerCpfCnpj"):
        await tools.change_charge_type({
            "branchCode": 1,
            "receivableCode": 100,
            "installmentCode": 1,
            "chargeType": 2,
        })


@pytest.mark.asyncio
@respx.mock
async def test_change_charge_type_accepts_customer_code(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/accounts-receivable/v2/documents/change-charge-type").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = AccountsReceivableTools(client)
    await tools.change_charge_type({
        "branchCode": 1,
        "receivableCode": 100,
        "installmentCode": 1,
        "chargeType": 2,
        "customerCode": 999,
    })

    import json
    body = json.loads(route.calls.last.request.content)
    assert body["customerCode"] == 999
    assert "customerCpfCnpj" not in body


# ════════════════════════════════════════════════════════════════════════════
# NEW v2.1 — Logistics module
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_search_product_storage_endpoint(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/logistics/v2/product-storages/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = LogisticsTools(client)
    await tools.search_product_storage({"branchCode": 1, "productCodeList": [10001]})

    assert route.called
    import json
    body = json.loads(route.calls.last.request.content)
    assert body["filter"]["branchCode"] == 1
    assert body["filter"]["productCodeList"] == [10001]
    assert body["page"] == 1
    assert body["pageSize"] == 100


@pytest.mark.asyncio
@respx.mock
async def test_add_product_packaging_endpoint(client):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/logistics/v2/product-packagings/add-quantity").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = LogisticsTools(client)
    await tools.add_product_packaging({
        "branchCode": 1, "productCode": 10001, "packagingNumber": 5, "quantity": 10
    })

    assert route.called
    assert _body(route) == {"branchCode": 1, "productCode": 10001, "packagingNumber": 5, "quantity": 10}


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    ("method_name", "path"),
    [
        ("upsert_product_packaging", "/api/totvsmoda/logistics/v2/product-packagings"),
        ("add_product_packaging", "/api/totvsmoda/logistics/v2/product-packagings/add-quantity"),
        ("subtract_product_packaging", "/api/totvsmoda/logistics/v2/product-packagings/subtract-quantity"),
    ],
)
async def test_product_packaging_contracts_post_exact_body(client, method_name, path):
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}{path}").mock(return_value=Response(200, json={"ok": True}))

    tools = LogisticsTools(client)
    args = {"branchCode": 1, "packagingNumber": 5, "productCode": 10001, "quantity": 10}
    await getattr(tools, method_name)(args)

    assert route.called
    assert _body(route) == args


# ════════════════════════════════════════════════════════════════════════════
# NEW v2.1 — Convenience tools
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_search_customer_by_document_detects_CPF(client):
    """11 digits → route to /individuals/search."""
    _mock_token()
    pf_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/individuals/search").mock(
        return_value=Response(200, json={"items": []})
    )
    pj_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/legal-entities/search")

    tools = ConvenienceTools(client)
    result = await tools.search_customer_by_document({"document": "123.456.789-00"})

    assert pf_route.called
    assert not pj_route.called
    assert result["_documentType"] == "CPF"
    assert result["_documentClean"] == "12345678900"


@pytest.mark.asyncio
@respx.mock
async def test_search_customer_by_document_detects_CNPJ(client):
    """14 digits → route to /legal-entities/search."""
    _mock_token()
    pf_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/individuals/search")
    pj_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/person/v2/legal-entities/search").mock(
        return_value=Response(200, json={"items": []})
    )

    tools = ConvenienceTools(client)
    result = await tools.search_customer_by_document({"document": "12.345.678/0001-99"})

    assert not pf_route.called
    assert pj_route.called
    assert result["_documentType"] == "CNPJ"
    assert result["_documentClean"] == "12345678000199"


@pytest.mark.asyncio
async def test_search_customer_by_document_rejects_empty(client):
    tools = ConvenienceTools(client)
    with pytest.raises(ValueError, match="Documento inválido"):
        await tools.search_customer_by_document({"document": "abc/def"})


@pytest.mark.asyncio
@respx.mock
async def test_upsert_product_value_tries_update_first(client):
    _mock_token()
    update_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/update").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = ConvenienceTools(client)
    result = await tools.upsert_product_value({
        "branchCode": 1, "productCode": 10001, "valueCode": 1, "value": 99.90
    })

    assert result["operation"] == "updated"
    assert update_route.called


@pytest.mark.asyncio
@respx.mock
async def test_upsert_product_value_falls_back_to_create(client):
    _mock_token()
    respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/update").mock(
        return_value=Response(400, json={"messages": [{"code": "NotFound", "message": "no such product value"}]})
    )
    create_route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/product/v2/values/create").mock(
        return_value=Response(201, json={"created": True})
    )

    tools = ConvenienceTools(client)
    result = await tools.upsert_product_value({
        "branchCode": 1, "productCode": 99999, "valueCode": 1, "value": 199.99
    })

    assert result["operation"] == "created"
    assert create_route.called


# ════════════════════════════════════════════════════════════════════════════
# CONTRACT — ensure request body matches TOTVS swagger expectations
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@respx.mock
async def test_search_orders_wraps_filter_in_body(client):
    """TOTVS expects {filter: {...}, page, pageSize} — flat args must be wrapped."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/search").mock(
        return_value=Response(200, json={"items": [], "totalHits": 0})
    )

    tools = SalesOrderTools(client)
    await tools.search_orders({
        "startOrderDate": "2026-04-01T00:00:00",
        "endOrderDate": "2026-04-30T23:59:59",
        "orderStatusList": ["Confirmado"],
        "page": 2,
        "pageSize": 50,
    })

    import json
    body = json.loads(route.calls.last.request.content)
    assert "filter" in body
    assert body["filter"]["startOrderDate"] == "2026-04-01T00:00:00"
    assert body["filter"]["orderStatusList"] == ["Confirmado"]
    assert body["page"] == 2
    assert body["pageSize"] == 50


@pytest.mark.asyncio
@respx.mock
async def test_cancel_order_sends_required_reason_code(client):
    """reasonCancellationCode is required per swagger."""
    _mock_token()
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/sales-order/v2/orders/cancel").mock(
        return_value=Response(200, json={"ok": True})
    )

    tools = SalesOrderTools(client)
    await tools.cancel_order({
        "branchCode": 1,
        "orderCode": 12345,
        "reasonCancellationCode": 99,
    })

    import json
    body = json.loads(route.calls.last.request.content)
    assert body["reasonCancellationCode"] == 99


@pytest.mark.asyncio
@respx.mock
async def test_product_search_prices_requires_priceCodeList(client):
    """prices/search requires priceCodeList — ValueError if missing."""
    tools = ProductTools(client)
    with pytest.raises(ValueError, match="priceCodeList"):
        await tools.search_prices({"branchCode": 1, "productCodeList": [10001]})


@pytest.mark.asyncio
@respx.mock
async def test_product_search_price_tables_requires_table_code(client):
    """price-tables/search requires priceTableCode — ValueError if missing."""
    tools = ProductTools(client)
    with pytest.raises(ValueError, match="priceTableCode"):
        await tools.search_price_tables({"branchCode": 1})
