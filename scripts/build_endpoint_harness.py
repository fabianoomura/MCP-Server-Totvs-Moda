"""Build an endpoint harness from TOTVS Moda Swagger JSON files.

The output is meant for future agents and maintainers:
- group endpoints by business area;
- classify endpoint type and write risk;
- detect pagination, expand, filter/order support;
- compare Swagger paths with paths currently referenced by the MCP tools.

Usage:
    python scripts/build_endpoint_harness.py
    python scripts/build_endpoint_harness.py --write
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = ROOT / "json"
TOOLS_DIR = ROOT / "tools"
DOCS_DIR = ROOT / "docs"

READ_METHODS = {"GET"}
WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

AREA_PRIORITY = {
    "pedido de venda": 1,
    "sales order": 1,
    "fiscal": 2,
    "contas a pagar": 3,
    "accounts payable": 3,
    "contas a receber": 4,
    "accounts receivable": 4,
    "produto": 5,
    "product": 5,
}

WRITE_HINTS = (
    "cancel",
    "create",
    "update",
    "change",
    "modify",
    "remove",
    "delete",
    "movement",
    "settle",
    "receive",
    "reactivate",
    "link",
    "suggest",
    "import",
)


@dataclass
class EndpointRecord:
    area: str
    source_file: str
    method: str
    path: str
    type: str
    risk: str
    priority: int
    mapped: bool
    has_filter: bool
    has_expand: bool
    has_order: bool
    has_pagination: bool
    expand_values: str
    summary: str


def normalize_path(path: str) -> str:
    path = re.sub(r"\{args\[[^/]*", "{}", path)
    return re.sub(r"\{[^}]+\}", "{}", path).rstrip("/")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_ref(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if ref and ref.startswith("#/components/schemas/"):
        return components.get(ref.rsplit("/", 1)[-1], {})
    return schema


def operation_schema(op: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    content = op.get("requestBody", {}).get("content", {})
    app_json = (
        content.get("application/json")
        or content.get("text/json")
        or content.get("application/*+json")
        or {}
    )
    schema = app_json.get("schema") or {}
    return schema_ref(schema, components)


def schema_props(schema: dict[str, Any]) -> dict[str, Any]:
    return schema.get("properties", {}) if isinstance(schema, dict) else {}


def extract_expand_values(schema: dict[str, Any]) -> str:
    props = schema_props(schema)
    expand = props.get("expand") or props.get("Expand")
    if not isinstance(expand, dict):
        return ""
    desc = expand.get("description", "")
    quoted = re.findall(r'"([^"]*)"', desc)
    values: list[str] = []
    for item in quoted:
        for value in item.split(","):
            clean = value.strip().strip(".")
            if clean and clean.lower() != "expand" and clean not in values:
                values.append(clean)
    if values:
        return ",".join(values)
    return ""


def classify_endpoint(method: str, path: str, op: dict[str, Any], schema: dict[str, Any]) -> tuple[str, str]:
    method = method.upper()
    lowered = path.lower()
    props = schema_props(schema)
    has_search_shape = bool({"filter", "page", "pageSize"} & set(props))

    if method == "GET":
        if "{" in path:
            return "read_get_path", "read"
        return "read_get_query", "read"

    if method == "POST" and (lowered.endswith("/search") or has_search_shape):
        return "read_post_search", "read"

    if method == "DELETE":
        return "write_delete", "destructive"

    if any(hint in lowered for hint in WRITE_HINTS):
        risk = "destructive" if any(x in lowered for x in ("cancel", "remove", "delete", "movement")) else "write"
        return f"write_{method.lower()}", risk

    return f"write_{method.lower()}", "write"


def area_priority(area: str, source_file: str) -> int:
    haystack = f"{area} {source_file}".lower()
    for key, priority in AREA_PRIORITY.items():
        if key in haystack:
            return priority
    if "analytics" in haystack:
        return 99
    return 50


def code_paths() -> set[str]:
    paths: set[str] = set()
    if not TOOLS_DIR.exists():
        return paths

    for file in TOOLS_DIR.glob("*.py"):
        text = file.read_text(encoding="utf-8")
        bases: dict[str, list[str]] = {}
        for name, value in re.findall(
            r"(?:self\.)?([A-Z][A-Z0-9_]*)\s*=\s*['\"]([^'\"]*/api/totvsmoda/[^'\"]*)['\"]",
            text,
        ):
            bases.setdefault(name, [])
            if value not in bases[name]:
                bases[name].append(value)

        for match in re.finditer(r"['\"](/api/totvsmoda/[^'\"]+)['\"]", text):
            paths.add(normalize_path(match.group(1)))

        for match in re.finditer(r"f['\"]\{(?:self\.)?([A-Z][A-Z0-9_]*)\}([^'\"]*)['\"]", text):
            base_name, suffix = match.groups()
            for base in bases.get(base_name, []):
                paths.add(normalize_path(base + suffix))

    return paths


def build_records() -> list[EndpointRecord]:
    mapped_paths = code_paths()
    records: list[EndpointRecord] = []

    for swagger_file in sorted(JSON_DIR.glob("*.json")):
        data = load_json(swagger_file)
        area = data.get("info", {}).get("title") or swagger_file.stem
        components = data.get("components", {}).get("schemas", {})

        for path, methods in sorted(data.get("paths", {}).items()):
            for method, op in sorted(methods.items()):
                method_upper = method.upper()
                schema = operation_schema(op, components) if method_upper not in READ_METHODS else {}
                props = schema_props(schema)
                params = op.get("parameters", [])
                param_names = {p.get("name") for p in params}

                endpoint_type, risk = classify_endpoint(method_upper, path, op, schema)
                has_filter = "filter" in props
                has_expand = "expand" in props or "Expand" in param_names
                has_order = "order" in props or "Order" in param_names
                has_pagination = bool({"page", "pageSize"} & set(props)) or bool({"Page", "PageSize"} & param_names)

                records.append(
                    EndpointRecord(
                        area=area,
                        source_file=swagger_file.name,
                        method=method_upper,
                        path=path,
                        type=endpoint_type,
                        risk=risk,
                        priority=area_priority(area, swagger_file.name),
                        mapped=normalize_path(path) in mapped_paths,
                        has_filter=has_filter,
                        has_expand=has_expand,
                        has_order=has_order,
                        has_pagination=has_pagination,
                        expand_values=extract_expand_values(schema),
                        summary=(op.get("summary") or "").replace("\n", " ").strip(),
                    )
                )

    return records


def markdown(records: list[EndpointRecord]) -> str:
    total = len(records)
    mapped = sum(1 for r in records if r.mapped)
    read = sum(1 for r in records if r.risk == "read")
    write = total - read

    lines = [
        "# API Endpoint Harness",
        "",
        "Generated from `json/*.json` by `scripts/build_endpoint_harness.py`.",
        "",
        f"- Total endpoints: {total}",
        f"- Mapped in MCP tools: {mapped}",
        f"- Read endpoints: {read}",
        f"- Write/destructive endpoints: {write}",
        "",
        "Priority follows the current implementation plan: sales order, fiscal, accounts payable, accounts receivable, product, then the remaining areas.",
        "",
    ]

    grouped: dict[str, list[EndpointRecord]] = {}
    for record in sorted(records, key=lambda r: (r.priority, r.area, r.path, r.method)):
        grouped.setdefault(record.area, []).append(record)

    for area, items in grouped.items():
        area_mapped = sum(1 for r in items if r.mapped)
        lines.extend(
            [
                f"## {area}",
                "",
                f"- Source files: {', '.join(sorted({r.source_file for r in items}))}",
                f"- Endpoints: {len(items)}",
                f"- Mapped: {area_mapped}",
                "",
                "| Method | Path | Type | Risk | Mapped | Flags | Expand |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for r in items:
            flags = ",".join(
                name
                for name, enabled in (
                    ("filter", r.has_filter),
                    ("expand", r.has_expand),
                    ("order", r.has_order),
                    ("page", r.has_pagination),
                )
                if enabled
            )
            lines.append(
                f"| {r.method} | `{r.path}` | {r.type} | {r.risk} | {'yes' if r.mapped else 'no'} | {flags or '-'} | {r.expand_values or '-'} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write docs/API_ENDPOINT_MATRIX.md and .json")
    args = parser.parse_args()

    records = build_records()
    payload = [asdict(record) for record in records]
    md = markdown(records)

    if args.write:
        DOCS_DIR.mkdir(exist_ok=True)
        (DOCS_DIR / "API_ENDPOINT_MATRIX.md").write_text(md, encoding="utf-8")
        (DOCS_DIR / "API_ENDPOINT_MATRIX.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("Wrote docs/API_ENDPOINT_MATRIX.md")
        print("Wrote docs/API_ENDPOINT_MATRIX.json")
    else:
        print(md)


if __name__ == "__main__":
    main()
