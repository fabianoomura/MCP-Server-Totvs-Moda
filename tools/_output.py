"""
Output File Utility
===================
Decodes large base64 payloads (DANFE PDF, product/person images) to a real
file on disk and returns the path, instead of returning the raw base64 inline.

Why this exists:
  Some endpoints return base64 blobs that are huge — a DANFE PDF can exceed
  1 MB. Returned inline, that easily blows past the token limits of MCP clients
  and is unusable for a model. Saving to a file and returning the path keeps the
  tool response small and gives the user something they can open directly.

Output directory resolution (generic — nothing company/user specific):
  1. TOTVS_OUTPUT_DIR env var, if set (expands ~ and creates the dir)
  2. The user's Downloads folder (~/Downloads), if it exists
  3. The user's home folder
  4. The OS temp dir (last resort)

This keeps the project portable: it works for any user on any machine without
hardcoded paths.
"""
from __future__ import annotations

import base64
import os
import re
import tempfile
from pathlib import Path
from typing import Any


def resolve_output_dir() -> Path:
    """Pick where decoded files are written. See module docstring for order."""
    env = os.environ.get("TOTVS_OUTPUT_DIR")
    if env:
        p = Path(env).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except OSError:
            pass

    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        return downloads

    home = Path.home()
    if home.is_dir():
        return home

    return Path(tempfile.gettempdir())


def safe_filename(name: str, default: str = "arquivo") -> str:
    """Sanitize a string into a filesystem-safe filename."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", (name or "")).strip("-._")
    return name or default


def save_base64(b64: str, filename: str) -> dict[str, Any]:
    """Decode a base64 string and write it to the resolved output dir.

    Returns metadata describing the saved file. Raises ValueError if the
    input is not valid base64.
    """
    try:
        data = base64.b64decode(b64, validate=False)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"conteúdo base64 inválido: {exc}") from exc

    out_dir = resolve_output_dir()
    path = out_dir / safe_filename(filename)
    path.write_bytes(data)
    return {
        "savedFile": str(path),
        "fileName": path.name,
        "sizeBytes": len(data),
        "sizeKb": round(len(data) / 1024, 1),
    }


def extract_access_key(text: str | None) -> str | None:
    """Best-effort: find a 44-digit NF-e access key in a string.

    The DANFE input may be raw XML or base64-encoded XML; we try the raw text
    first and, failing that, a base64 decode. Used only to name files nicely —
    never required.
    """
    if not text:
        return None
    m = re.search(r"\b(\d{44})\b", text)
    if m:
        return m.group(1)
    try:
        decoded = base64.b64decode(text, validate=False).decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r"\b(\d{44})\b", decoded)
    return m.group(1) if m else None
