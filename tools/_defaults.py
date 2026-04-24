"""
Default Injection Utility
=========================
Injects default values into tool arguments when the LLM forgets to pass them.

The TOTVS API requires `branchCode` or `branchCodeList` in many endpoints.
The LLM often forgets to include it, resulting in HTTP 400 errors and wasted
tokens in retry loops.

This utility silently fills those defaults from `context_cache.branches`
(loaded from the TOTVS_BRANCH_CODES env var at startup). The LLM doesn't
need to know the field is required — we just fill it.

Usage in any tool:
    from tools._defaults import inject_branch_defaults

    async def my_tool(self, args):
        args = inject_branch_defaults(args)
        # ... rest of tool logic
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("totvs-moda-mcp.defaults")


class MissingBranchDefaultError(ValueError):
    """Raised when branch default is needed but not configured.

    Explains exactly what the user needs to do to fix it.
    """

    def __init__(self) -> None:
        super().__init__(
            "branchCode/branchCodeList is required by TOTVS API but not provided, "
            "and no default is configured. Set TOTVS_BRANCH_CODES in your .env or "
            "mcp.json env block (e.g. TOTVS_BRANCH_CODES=1 for a single branch, "
            "or TOTVS_BRANCH_CODES=1,2,5 for multiple)."
        )


def _get_default_branches() -> list[int]:
    """Fetch the configured default branches from context_cache.

    Import is lazy to avoid circular imports and to handle the case where
    context_cache hasn't been loaded yet.
    """
    try:
        import context_cache
        cache = getattr(context_cache, "CACHE", None) or getattr(context_cache, "_cache", None) or {}
        branches = cache.get("branches") or []
        if branches:
            return list(branches)
    except Exception as exc:
        logger.debug(f"context_cache unavailable: {exc}")

    # Fallback: read env var directly
    import os
    raw = os.environ.get("TOTVS_BRANCH_CODES", "").strip()
    if raw:
        try:
            return [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            logger.warning(f"TOTVS_BRANCH_CODES has invalid format: {raw!r}")

    return []


def inject_branch_defaults(args: dict[str, Any]) -> dict[str, Any]:
    """Fill branchCode / branchCodeList from context_cache if absent.

    Returns a NEW dict (doesn't mutate the input). Safe to call repeatedly.

    Rules:
    - If args already contains `branchCode` (not None): preserved as-is.
    - If args already contains `branchCodeList` (not None, not empty): preserved.
    - If neither: both are injected using the cached default branches.
      - `branchCode` gets the FIRST branch from the list.
      - `branchCodeList` gets the FULL list.
    - If no default is configured (cache empty AND env var not set):
      raises MissingBranchDefaultError with actionable message.

    This design lets tools that need `branchCode` (singular) and tools that
    need `branchCodeList` (plural) both work correctly from the same call.
    """
    out = dict(args)  # shallow copy — don't mutate caller's dict

    has_branch_code = out.get("branchCode") is not None
    has_branch_list = bool(out.get("branchCodeList"))

    if has_branch_code or has_branch_list:
        # LLM specified something — respect it.
        # But if it specified ONE but not the OTHER, derive the missing one:
        if has_branch_code and not has_branch_list:
            # tool might need branchCodeList — derive from branchCode
            out["branchCodeList"] = [out["branchCode"]]
        elif has_branch_list and not has_branch_code:
            # tool might need branchCode — take first from list
            out["branchCode"] = out["branchCodeList"][0]
        return out

    # Neither was provided → inject from defaults
    branches = _get_default_branches()
    if not branches:
        raise MissingBranchDefaultError()

    out["branchCode"] = branches[0]
    out["branchCodeList"] = list(branches)
    logger.debug(f"injected branch defaults: branchCode={branches[0]}, branchCodeList={branches}")
    return out


def with_branch_defaults(tool_method):
    """Decorator alternative to explicit call.

    @with_branch_defaults
    async def my_tool(self, args):
        ...

    The decorator calls inject_branch_defaults(args) before passing to the tool.
    Useful when you want a declarative marker at the method definition.
    """
    async def wrapper(self, args: dict[str, Any]) -> Any:
        args = inject_branch_defaults(args)
        return await tool_method(self, args)
    wrapper.__name__ = tool_method.__name__
    wrapper.__doc__ = tool_method.__doc__
    return wrapper
