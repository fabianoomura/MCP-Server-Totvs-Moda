"""
Value Type Helpers
==================
Normalização de tipos de valor (Price/Cost) com suporte a aliases.

A API TOTVS exige `valueType` com valores exatos `"Price"` ou `"Cost"`.
Mas scripts em produção MOOUI (e provavelmente outros usuários) usam `"P"`
e `"C"` por brevidade. Esta utility aceita os dois formatos e normaliza.

Uso:
    from tools._value_types import normalize_value_type
    
    normalize_value_type("P")       # → "Price"
    normalize_value_type("C")       # → "Cost"
    normalize_value_type("Price")   # → "Price"
    normalize_value_type("price")   # → "Price"
    normalize_value_type("Cost")    # → "Cost"
"""
from __future__ import annotations
from typing import Optional


VALID_VALUE_TYPES = {"Price", "Cost"}

ALIASES = {
    "P": "Price",
    "p": "Price",
    "PRICE": "Price",
    "price": "Price",
    "Price": "Price",
    "C": "Cost",
    "c": "Cost",
    "COST": "Cost",
    "cost": "Cost",
    "Cost": "Cost",
}


class InvalidValueTypeError(ValueError):
    """Raised when valueType cannot be normalized."""
    def __init__(self, raw_value: str) -> None:
        super().__init__(
            f"valueType {raw_value!r} is invalid. "
            f"Use 'Price' / 'Cost' (or aliases 'P' / 'C')."
        )


def normalize_value_type(raw: Optional[str]) -> Optional[str]:
    """Normaliza valueType para 'Price' ou 'Cost'.
    
    Aceita aliases ('P', 'p', 'C', 'c') e variações de caixa.
    Retorna None se o input for None (não levanta erro — quem chama decide).
    Levanta InvalidValueTypeError se o valor não puder ser normalizado.
    """
    if raw is None:
        return None
    
    if not isinstance(raw, str):
        raise InvalidValueTypeError(raw)
    
    normalized = ALIASES.get(raw.strip())
    if normalized is None:
        raise InvalidValueTypeError(raw)
    return normalized
