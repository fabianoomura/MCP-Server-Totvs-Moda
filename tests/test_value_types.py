"""Tests for tools._value_types — normalização de Price/Cost."""
import pytest
from tools._value_types import normalize_value_type, InvalidValueTypeError


def test_canonical_values_pass_through():
    assert normalize_value_type("Price") == "Price"
    assert normalize_value_type("Cost") == "Cost"


def test_short_aliases():
    assert normalize_value_type("P") == "Price"
    assert normalize_value_type("C") == "Cost"
    assert normalize_value_type("p") == "Price"
    assert normalize_value_type("c") == "Cost"


def test_case_variations():
    assert normalize_value_type("price") == "Price"
    assert normalize_value_type("PRICE") == "Price"
    assert normalize_value_type("cost") == "Cost"
    assert normalize_value_type("COST") == "Cost"


def test_whitespace_tolerated():
    assert normalize_value_type("  P  ") == "Price"
    assert normalize_value_type("\tCost\n") == "Cost"


def test_none_returns_none():
    """Quem chama decide se None é erro ou não."""
    assert normalize_value_type(None) is None


def test_invalid_string_raises():
    with pytest.raises(InvalidValueTypeError) as exc:
        normalize_value_type("Foo")
    assert "Foo" in str(exc.value)
    assert "Price" in str(exc.value)
    assert "Cost" in str(exc.value)


def test_invalid_number_raises():
    with pytest.raises(InvalidValueTypeError):
        normalize_value_type(1)


def test_empty_string_raises():
    with pytest.raises(InvalidValueTypeError):
        normalize_value_type("")
