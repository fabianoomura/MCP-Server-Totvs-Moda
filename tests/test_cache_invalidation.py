"""
Regression tests for response cache invalidation after writes.
"""
import pytest

import response_cache as cache
from tools.product import ProductTools
from tools.sales_order import SalesOrderTools
from totvs_client import TotvsApiError


class ProductWriteClient:
    async def upsert(self, update_path, create_path, body):
        return {"operation": "updated", "result": {"ok": True}}


class SalesOrderWriteClient:
    async def post(self, path, body):
        return {"ok": True}


class FailingSalesOrderClient:
    async def post(self, path, body):
        raise TotvsApiError(400, "bad write")


@pytest.mark.asyncio
async def test_update_product_price_invalidates_product_cache():
    params = {"productCode": 100}
    cache.put("product360_full", params, {"old": True})

    tools = ProductTools(ProductWriteClient())
    await tools.update_product_price(
        {"branchCode": 1, "productCode": 100, "valueCode": 1, "value": 20}
    )

    assert cache.get("product360_full", params, cache.STOCK) is None


@pytest.mark.asyncio
async def test_cancel_order_invalidates_orders_cache():
    params = {"orderCode": 123}
    cache.put("orders", params, {"cancelled": False})

    tools = SalesOrderTools(SalesOrderWriteClient())
    await tools.cancel_order(
        {"branchCode": 1, "orderCode": 123, "reasonCancellationCode": 99}
    )

    assert cache.get("orders", params, cache.SALES) is None


@pytest.mark.asyncio
async def test_failed_write_does_not_invalidate_cache():
    params = {"orderCode": 123}
    cached = {"cancelled": False}
    cache.put("orders", params, cached)

    tools = SalesOrderTools(FailingSalesOrderClient())
    with pytest.raises(TotvsApiError):
        await tools.cancel_order(
            {"branchCode": 1, "orderCode": 123, "reasonCancellationCode": 99}
        )

    assert cache.get("orders", params, cache.SALES) == cached
