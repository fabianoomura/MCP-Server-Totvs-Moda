"""
Guard tests for TOOLS <-> ROUTING parity.
"""
from tools.account_payable import AccountPayableTools
from tools.accounts_receivable import AccountsReceivableTools
from tools.aggregators import AggregatorTools
from tools.analytics import AnalyticsTools
from tools.data_package import DataPackageTools
from tools.fiscal import FiscalTools
from tools.general import GeneralTools
from tools.image import ImageTools
from tools.logistics import LogisticsTools
from tools.material_request import MaterialRequestTools
from tools.other_modules import GlobalTools, ManagementTools, ProductionOrderTools
from tools.person import PersonTools
from tools.product import ProductTools
from tools.product_engineering import ProductEngineeringTools
from tools.product_prototype import ProductPrototypeTools
from tools.purchase_order import PurchaseOrderTools
from tools.sales_order import SalesOrderTools
from tools.seller import SellerTools
from tools.voucher import VoucherTools

import server


SPECIAL_TOOLS = {
    "totvs_get_instructions",
    "totvs_get_context",
    "totvs_get_usage_insights",
}

ROUTES_WITHOUT_DEFAULT_TOOL = {
    # Gated by TOTVS_ENABLE_ANALYTICS.
    "totvs_analytics_call",
}

MODULE_CLASSES = {
    "sales_order": SalesOrderTools,
    "product": ProductTools,
    "person": PersonTools,
    "accounts_receivable": AccountsReceivableTools,
    "fiscal": FiscalTools,
    "general": GeneralTools,
    "account_payable": AccountPayableTools,
    "purchase_order": PurchaseOrderTools,
    "seller": SellerTools,
    "voucher": VoucherTools,
    "management": ManagementTools,
    "global": GlobalTools,
    "production_order": ProductionOrderTools,
    "data_package": DataPackageTools,
    "image": ImageTools,
    "logistics": LogisticsTools,
    "aggregators": AggregatorTools,
    "product_engineering": ProductEngineeringTools,
    "material_request": MaterialRequestTools,
    "product_prototype": ProductPrototypeTools,
    "analytics": AnalyticsTools,
}


def test_every_tool_has_route():
    tool_names = {tool.name for tool in server.TOOLS}
    missing = tool_names - set(server.ROUTING) - SPECIAL_TOOLS
    assert missing == set()


def test_every_route_resolves():
    tool_names = {tool.name for tool in server.TOOLS}
    extra_routes = set(server.ROUTING) - tool_names - ROUTES_WITHOUT_DEFAULT_TOOL
    assert extra_routes == set()

    missing_modules = []
    missing_methods = []
    for tool_name, (module_key, method_name) in server.ROUTING.items():
        module_class = MODULE_CLASSES.get(module_key)
        if module_class is None:
            missing_modules.append((tool_name, module_key))
            continue
        if not hasattr(module_class, method_name):
            missing_methods.append((tool_name, module_key, method_name))

    assert missing_modules == []
    assert missing_methods == []
