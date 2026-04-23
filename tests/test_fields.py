"""
Tests for tools._fields — the field projection utility.
"""
import pytest
from tools._fields import pick_fields, apply_fields


def test_empty_fields_returns_data_unchanged():
    data = {"items": [{"a": 1, "b": 2}]}
    assert pick_fields(data, []) == data
    assert pick_fields(data, None) == data


def test_top_level_fields_kept():
    data = {
        "items": [
            {"orderCode": 1, "customerCode": 10, "totalValue": 100, "orderDate": "2026-04-01"},
            {"orderCode": 2, "customerCode": 20, "totalValue": 200, "orderDate": "2026-04-02"},
        ],
        "totalHits": 2,
    }
    result = pick_fields(data, ["orderCode", "totalValue"])

    assert result["totalHits"] == 2
    assert len(result["items"]) == 2
    assert result["items"][0] == {"orderCode": 1, "totalValue": 100}
    assert result["items"][1] == {"orderCode": 2, "totalValue": 200}


def test_nested_field_with_dot_notation():
    data = {
        "items": [
            {
                "orderCode": 1,
                "items": [
                    {"productCode": 100, "name": "A", "quantity": 2, "price": 50.0},
                    {"productCode": 200, "name": "B", "quantity": 1, "price": 150.0},
                ],
            }
        ]
    }
    result = pick_fields(data, ["orderCode", "items.productCode", "items.quantity"])

    order = result["items"][0]
    assert order["orderCode"] == 1
    assert len(order["items"]) == 2
    assert order["items"][0] == {"productCode": 100, "quantity": 2}
    assert "name" not in order["items"][0]
    assert "price" not in order["items"][0]


def test_pagination_metadata_always_preserved():
    data = {
        "items": [{"a": 1, "b": 2}],
        "totalHits": 50,
        "page": 1,
        "pageSize": 100,
        "hasNext": False,
    }
    result = pick_fields(data, ["a"])
    assert result["totalHits"] == 50
    assert result["page"] == 1
    assert result["pageSize"] == 100
    assert result["hasNext"] is False


def test_missing_fields_silently_skipped():
    data = {"items": [{"a": 1}]}
    result = pick_fields(data, ["a", "nonexistent"])
    assert result["items"][0] == {"a": 1}


def test_apply_fields_shortcut_with_fields_arg():
    data = {"items": [{"a": 1, "b": 2, "c": 3}]}
    args = {"fields": ["a", "c"]}
    result = apply_fields(data, args)
    assert result["items"][0] == {"a": 1, "c": 3}


def test_apply_fields_shortcut_without_fields_arg():
    data = {"items": [{"a": 1, "b": 2, "c": 3}]}
    args = {}
    result = apply_fields(data, args)
    assert result == data


def test_response_shape_without_items():
    """Some endpoints return a single object, not a list of items."""
    data = {"orderCode": 1, "customerName": "Alice", "totalValue": 100}
    result = pick_fields(data, ["orderCode", "totalValue"])
    assert result == {"orderCode": 1, "totalValue": 100}


def test_nested_dict_field_not_list():
    """Support nested dict (not just list of dicts)."""
    data = {
        "items": [{
            "orderCode": 1,
            "customer": {"code": 100, "name": "Alice", "cpf": "123"},
        }]
    }
    result = pick_fields(data, ["orderCode", "customer.name"])
    assert result["items"][0] == {"orderCode": 1, "customer": {"name": "Alice"}}


def test_items_is_not_corrupted_when_empty():
    data = {"items": [], "totalHits": 0}
    result = pick_fields(data, ["anything"])
    assert result == {"items": [], "totalHits": 0}
