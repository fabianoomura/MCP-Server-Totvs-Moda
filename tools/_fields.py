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


def apply_fields(result: Any, args: dict[str, Any]) -> Any:
    """Convenience wrapper: checks args for 'fields' and applies if present.

    Drop-in usage in any search tool:
        result = await self.client.post(...)
        return apply_fields(result, args)
    """
    if args.get("fields"):
        return pick_fields(result, args["fields"])
    return result
