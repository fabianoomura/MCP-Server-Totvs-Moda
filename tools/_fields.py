"""
Field Filter Utility
====================
Enables TOTVS tool results to be trimmed to just the fields the caller asked for.

Problem this solves:
  Default TOTVS responses include 40-60+ fields per record. Most of them are
  irrelevant for any given question. Full responses for 500 orders can exceed
  100KB, which wastes tokens and slows responses.

Solution:
  Any search tool can accept an optional `fields` parameter listing the fields
  to keep. Nested paths (e.g. "items.productCode") are supported.

Usage pattern in a tool:
  async def search_xxx(self, args):
      result = await self.client.post(...)
      if args.get("fields"):
          result = pick_fields(result, args["fields"])
      return result

The LLM learns to use this via tool descriptions (see server.py patches in
v2.5): "Use fields=['orderCode','customerName','totalValue'] to reduce response size."
"""
from __future__ import annotations
from typing import Any


def pick_fields(data: Any, fields: list[str]) -> Any:
    """Keep only requested fields from a response structure.

    Rules:
    - Top-level keys 'items', 'totalHits', 'page', 'pageSize', 'hasNext'
      are pagination metadata and ALWAYS preserved.
    - Field paths can use dot notation to descend into nested lists/dicts:
        'orderCode'          - top-level field
        'items.productCode'  - nested inside 'items[]' subrecords
    - If field list is empty or None, data is returned unchanged.
    - Fields not present in the data are silently skipped (no KeyError).

    Args:
        data: The response dict from a TOTVS search endpoint. Typically
              {"items": [...], "totalHits": N, "page": 1, "pageSize": 100}.
        fields: List of field paths to keep.

    Returns:
        A new dict with the same top-level structure but only the requested
        fields in each record.
    """
    if not fields:
        return data
    if not isinstance(data, dict):
        return data

    pagination_keys = {"totalHits", "page", "pageSize", "hasNext", "count"}

    result: dict[str, Any] = {}

    for k, v in data.items():
        if k in pagination_keys:
            result[k] = v

    items = data.get("items")
    if isinstance(items, list):
        result["items"] = [_pick_from_record(item, fields) for item in items]
    else:
        result = _pick_from_record(data, fields)
        for k in pagination_keys:
            if k in data:
                result[k] = data[k]

    return result


def _pick_from_record(record: Any, fields: list[str]) -> Any:
    """Extract requested fields from a single record."""
    if not isinstance(record, dict):
        return record

    nested: dict[str, list[str]] = {}
    top_level: list[str] = []

    for f in fields:
        if "." in f:
            prefix, rest = f.split(".", 1)
            nested.setdefault(prefix, []).append(rest)
        else:
            top_level.append(f)

    out: dict[str, Any] = {}

    for f in top_level:
        if f in record:
            out[f] = record[f]

    for prefix, sub_fields in nested.items():
        if prefix not in record:
            continue
        value = record[prefix]
        if isinstance(value, list):
            out[prefix] = [_pick_from_record(sub, sub_fields) for sub in value]
        elif isinstance(value, dict):
            out[prefix] = _pick_from_record(value, sub_fields)
        else:
            out[prefix] = value

    return out


def _field_present(record: Any, path: str) -> bool:
    """True if `path` (dot notation) resolves to an existing key in `record`."""
    if not isinstance(record, dict):
        return False
    head, _, rest = path.partition(".")
    if head not in record:
        return False
    if not rest:
        return True
    value = record[head]
    if isinstance(value, list):
        return any(_field_present(sub, rest) for sub in value)
    if isinstance(value, dict):
        return _field_present(value, rest)
    return False


def _records_for_validation(data: Any) -> list | None:
    """Records to validate field names against, or None when undecidable."""
    if not isinstance(data, dict):
        return None
    items = data.get("items")
    if isinstance(items, list):
        return items or None  # empty list -> can't tell if a field is valid
    return [data]


def unknown_fields(data: Any, fields: list[str]) -> list[str]:
    """Requested field paths that match nothing in any record.

    Returns [] when it can't decide (no records to compare against), so a
    warning is only emitted when we are sure the field is absent.
    """
    records = _records_for_validation(data)
    if not records:
        return []
    return [f for f in fields if not any(_field_present(r, f) for r in records)]


def apply_fields(result: Any, args: dict[str, Any]) -> Any:
    """Convenience wrapper: checks args for 'fields' and applies if present.

    Drop-in usage in any search tool:
        result = await self.client.post(...)
        return apply_fields(result, args)

    When a requested field matches nothing in the response, a non-intrusive
    `_fieldsWarning` is attached so the caller learns the real field name
    instead of silently getting an empty result.
    """
    fields = args.get("fields")
    if not fields:
        return result

    filtered = pick_fields(result, fields)
    missing = unknown_fields(result, fields)
    if missing and isinstance(filtered, dict):
        filtered = dict(filtered)
        filtered["_fieldsWarning"] = (
            "Campos não encontrados e ignorados: "
            + ", ".join(missing)
            + ". Confira o nome — a resposta pode usar outro (ex.: 'totalValue' "
            "em vez de 'value', ou item usa 'netValue'/'unitNetValue')."
        )
    return filtered
