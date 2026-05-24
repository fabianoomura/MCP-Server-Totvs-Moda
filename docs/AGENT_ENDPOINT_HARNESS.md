# Agent Endpoint Harness

This project keeps a lightweight endpoint harness for future agents and
maintainers. It turns the Swagger files in `json/` into a matrix grouped by
area, endpoint type, read/write risk, and current MCP mapping status.

## Files

- `scripts/build_endpoint_harness.py`
  - Reads `json/*.json`.
  - Classifies endpoints by area and type.
  - Detects read/write risk, pagination, `filter`, `expand`, and `order`.
  - Compares Swagger paths with paths referenced by `tools/*.py`.

- `docs/API_ENDPOINT_MATRIX.md`
  - Human-readable endpoint matrix.
  - Useful during implementation reviews and planning.

- `docs/API_ENDPOINT_MATRIX.json`
  - Machine-readable endpoint matrix.
  - Useful for future agents, CI checks, dashboards, or coverage reports.

## Usage

```powershell
python scripts/build_endpoint_harness.py --write
```

Run this after adding or replacing Swagger JSON files.

## Classification

Endpoint types:

- `read_post_search`: POST endpoint with search/filter/page shape.
- `read_get_query`: GET endpoint with query parameters.
- `read_get_path`: GET endpoint with path parameters.
- `write_post`: POST endpoint that creates, changes, links, moves, or performs an action.
- `write_put`: PUT endpoint.
- `write_delete`: DELETE endpoint.

Risk levels:

- `read`: safe for smoke tests with small `pageSize`.
- `write`: requires explicit implementation care and should be clearly marked in the MCP tool description.
- `destructive`: cancel, remove, delete, movement, or similar operations. Do not test against the real API without explicit approval and a known safe target.

## Current Coverage

As of 2026-05-24:

- Total endpoints: 251
- Mapped endpoints: 162
- Current matrix files: `docs/API_ENDPOINT_MATRIX.md` and `docs/API_ENDPOINT_MATRIX.json`

High-coverage areas:

- Fiscal: 11/11
- Accounts payable: 4/4
- Accounts receivable: 14/14
- Material request: 9/9
- Product prototype: 3/3
- Logistics: 4/4
- Person: 19/20

## Implementation Order

Current priority:

1. Product auxiliary read endpoints
2. General read endpoints
3. Seller remaining read endpoint
4. Image read endpoints
5. Remaining writes with explicit contracts
6. Analytics only if the module works in the target environment

Within each area:

1. Map read-only endpoints first.
2. Preserve existing tool behavior and aliases.
3. Add official Swagger field names, enums, `expand`, `order`, and pagination.
4. Smoke test with small `pageSize`.
5. Add write endpoints only after reviewing the schema and marking risk clearly.

## Expand Policy

When an endpoint supports `expand`, use the Swagger description as the source
of truth. If the local JSON does not include enough schema detail, ask for the
specific Swagger section before implementing.

## Agent Notes

Agents should treat `docs/API_ENDPOINT_MATRIX.json` as the structured source
for planning. The `mapped` flag is path-based coverage, not a guarantee that
all fields, enums, expands, or edge cases are implemented.
