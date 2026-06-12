"""
Response Cache
==============
Cache TTL genérico para respostas da API TOTVS.

Funciona com qualquer empresa — nada é hardcoded.
Cache por chave (hash dos parâmetros), expira por TTL.

TTLs padrão (segundos):
- REFERENCE = 86400 (24h) — filiais, operações, composições
- CATALOG   = 3600  (1h)  — produtos, clientes
- FINANCIAL = 900   (15m) — contas a receber/pagar
- STOCK     = 300   (5m)  — saldos de estoque
- SALES     = 120   (2m)  — pedidos de venda

Override global via env: TOTVS_CACHE_TTL=300 (aplica a tudo)
Desativar: TOTVS_CACHE_ENABLED=false
"""
import hashlib
import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger("totvs-moda-mcp.cache")

# ── TTL tiers (seconds) ──────────────────────────────────────────────
REFERENCE = 86400   # 24h
CATALOG = 3600      # 1h
FINANCIAL = 900     # 15min
STOCK = 300         # 5min
SALES = 120         # 2min

# ── Internal store ────────────────────────────────────────────────────
_store: dict[str, tuple[float, Any]] = {}
_hits = 0
_misses = 0


def _enabled() -> bool:
    return os.environ.get("TOTVS_CACHE_ENABLED", "true").lower() not in ("false", "0", "no")


def _global_ttl() -> int | None:
    val = os.environ.get("TOTVS_CACHE_TTL")
    return int(val) if val else None


def _make_key(prefix: str, params: Any) -> str:
    raw = json.dumps(params, sort_keys=True, default=str)
    h = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]
    return f"{prefix}:{h}"


def get(prefix: str, params: Any, ttl: int) -> Any | None:
    """Return cached value or None if miss/expired."""
    global _hits, _misses
    if not _enabled():
        return None

    effective_ttl = _global_ttl() or ttl
    key = _make_key(prefix, params)

    entry = _store.get(key)
    if entry is not None:
        ts, data = entry
        if time.time() - ts < effective_ttl:
            _hits += 1
            logger.debug(f"CACHE HIT: {key} (age={(time.time() - ts):.0f}s)")
            return data

    _misses += 1
    return None


def put(prefix: str, params: Any, data: Any) -> None:
    """Store value in cache."""
    if not _enabled():
        return
    key = _make_key(prefix, params)
    _store[key] = (time.time(), data)
    logger.debug(f"CACHE PUT: {key}")


def invalidate(prefix: str | None = None) -> int:
    """Remove entries. If prefix given, only matching keys. Returns count removed."""
    global _store
    if prefix is None:
        count = len(_store)
        _store = {}
        return count

    to_remove = [k for k in _store if k.startswith(f"{prefix}:")]
    for k in to_remove:
        del _store[k]
    return len(to_remove)


def stats() -> dict[str, Any]:
    """Return cache statistics."""
    return {
        "enabled": _enabled(),
        "entries": len(_store),
        "hits": _hits,
        "misses": _misses,
        "hitRate": f"{_hits / (_hits + _misses) * 100:.0f}%" if (_hits + _misses) > 0 else "0%",
    }
