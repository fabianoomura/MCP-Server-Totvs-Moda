"""
Usage Tracker
=============
Logs every MCP tool call to a local JSONL file for pattern analysis.

Storage: ~/.totvs-moda-usage.jsonl (one JSON object per line)
Override path: TOTVS_USAGE_FILE env var
Disable: TOTVS_USAGE_ENABLED=false

Privacy: data stays local. No external calls. Each company has its own file.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("totvs-moda-mcp.usage")


def _enabled() -> bool:
    return os.environ.get("TOTVS_USAGE_ENABLED", "true").lower() not in ("false", "0", "no")


def _file_path() -> Path:
    custom = os.environ.get("TOTVS_USAGE_FILE")
    if custom:
        return Path(custom)
    return Path.home() / ".totvs-moda-usage.jsonl"


def track(tool_name: str, params: dict[str, Any], duration_ms: float | None = None) -> None:
    """Append a tool call entry to the usage log."""
    if not _enabled():
        return

    # Strip sensitive/large fields from params
    safe_params = _sanitize_params(params)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tool": tool_name,
        "params": safe_params,
    }
    if duration_ms is not None:
        entry["duration_ms"] = round(duration_ms, 1)

    try:
        path = _file_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        logger.debug(f"Usage track write failed: {e}")


def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive or overly large values from params."""
    skip_keys = {"password", "secret", "token", "body"}
    result = {}
    for k, v in params.items():
        if k.lower() in skip_keys:
            continue
        if isinstance(v, str) and len(v) > 200:
            result[k] = v[:50] + "...(truncated)"
        elif isinstance(v, list) and len(v) > 20:
            result[k] = v[:5]
            result[f"_{k}_count"] = len(v)
        else:
            result[k] = v
    return result


def read_log(max_entries: int = 5000) -> list[dict[str, Any]]:
    """Read the usage log. Returns list of entries, newest first."""
    path = _file_path()
    if not path.exists():
        return []

    entries = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.debug(f"Usage log read failed: {e}")
        return []

    return entries[-max_entries:]


def clear_log() -> int:
    """Delete the usage log. Returns number of entries removed."""
    path = _file_path()
    if not path.exists():
        return 0
    try:
        entries = sum(1 for _ in open(path, "r", encoding="utf-8"))
        path.unlink()
        return entries
    except Exception:
        return 0
