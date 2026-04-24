"""
Tests for tools._defaults — the branch default injection utility.

Covers every scenario the LLM can throw at us:
- Nothing passed → inject from env
- branchCode passed → respected, branchCodeList derived
- branchCodeList passed → respected, branchCode derived
- Both passed → both respected
- Nothing passed and no default → clear error
"""
import sys
import types
import pytest

from tools._defaults import inject_branch_defaults, MissingBranchDefaultError, with_branch_defaults


@pytest.fixture(autouse=True)
def fake_context_cache(monkeypatch):
    """Provide a fake context_cache module for each test."""
    fake = types.ModuleType("context_cache")
    fake.CACHE = {"branches": [1]}
    monkeypatch.setitem(sys.modules, "context_cache", fake)
    yield fake


@pytest.fixture
def empty_cache(monkeypatch):
    """Replace cache with empty dict."""
    fake = types.ModuleType("context_cache")
    fake.CACHE = {}
    monkeypatch.setitem(sys.modules, "context_cache", fake)
    monkeypatch.delenv("TOTVS_BRANCH_CODES", raising=False)
    yield


# ── Defaults injection ──────────────────────────────────────────────────────

def test_empty_args_gets_default_branch():
    """Most common case: LLM forgot to pass branchCode."""
    result = inject_branch_defaults({})
    assert result == {"branchCode": 1, "branchCodeList": [1]}


def test_args_without_branch_gets_default(fake_context_cache):
    fake_context_cache.CACHE = {"branches": [1, 2, 5]}
    result = inject_branch_defaults({"customerCode": 100})
    assert result["branchCode"] == 1  # first branch
    assert result["branchCodeList"] == [1, 2, 5]
    assert result["customerCode"] == 100  # untouched


# ── Respect caller's choice ─────────────────────────────────────────────────

def test_explicit_branch_code_is_preserved():
    """If LLM explicitly passed branchCode, use it."""
    result = inject_branch_defaults({"branchCode": 99})
    assert result["branchCode"] == 99
    # derived branchCodeList for tools that need plural form
    assert result["branchCodeList"] == [99]


def test_explicit_branch_code_list_is_preserved():
    """If LLM explicitly passed branchCodeList, use it."""
    result = inject_branch_defaults({"branchCodeList": [7, 8]})
    assert result["branchCodeList"] == [7, 8]
    # derived branchCode for tools that need singular
    assert result["branchCode"] == 7  # first


def test_both_explicit_both_preserved():
    """If both passed, both respected (no magic)."""
    result = inject_branch_defaults({
        "branchCode": 99,
        "branchCodeList": [99, 100, 101],
    })
    assert result["branchCode"] == 99
    assert result["branchCodeList"] == [99, 100, 101]


def test_zero_is_falsy_but_should_be_respected():
    """Edge case: branchCode=0 shouldn't trigger injection.
    (Check None explicitly, not falsy.)"""
    result = inject_branch_defaults({"branchCode": 0})
    # 0 is a legitimate value, should not be overwritten
    # Our current logic uses `is not None` so this works
    assert result["branchCode"] == 0


# ── Error path ──────────────────────────────────────────────────────────────

def test_missing_default_raises_clear_error(empty_cache):
    """When nothing is passed and no default configured, error."""
    with pytest.raises(MissingBranchDefaultError) as exc:
        inject_branch_defaults({})

    # Error message must mention TOTVS_BRANCH_CODES to guide the user
    assert "TOTVS_BRANCH_CODES" in str(exc.value)


def test_missing_default_doesnt_break_if_caller_passed_it(empty_cache):
    """If caller passed branchCode, shouldn't need default."""
    result = inject_branch_defaults({"branchCode": 42})
    assert result["branchCode"] == 42


# ── Env var fallback ────────────────────────────────────────────────────────

def test_env_var_fallback_when_cache_empty(empty_cache, monkeypatch):
    """If context_cache is empty but TOTVS_BRANCH_CODES is set, use that."""
    monkeypatch.setenv("TOTVS_BRANCH_CODES", "3,4,5")
    result = inject_branch_defaults({})
    assert result["branchCode"] == 3
    assert result["branchCodeList"] == [3, 4, 5]


def test_env_var_single_branch(empty_cache, monkeypatch):
    monkeypatch.setenv("TOTVS_BRANCH_CODES", "7")
    result = inject_branch_defaults({})
    assert result == {"branchCode": 7, "branchCodeList": [7]}


def test_env_var_invalid_format_gracefully_fails(empty_cache, monkeypatch):
    """If TOTVS_BRANCH_CODES has garbage, treat as unset."""
    monkeypatch.setenv("TOTVS_BRANCH_CODES", "abc,xyz")
    with pytest.raises(MissingBranchDefaultError):
        inject_branch_defaults({})


# ── Immutability ────────────────────────────────────────────────────────────

def test_input_dict_is_not_mutated():
    """Caller's dict must not be modified — we return a new one."""
    original = {"customerCode": 100}
    _ = inject_branch_defaults(original)
    assert "branchCode" not in original
    assert original == {"customerCode": 100}


# ── Decorator form ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_decorator_injects_defaults():
    """@with_branch_defaults works as an alternative to explicit call."""
    captured = {}

    class FakeTool:
        @with_branch_defaults
        async def my_method(self, args):
            captured.update(args)
            return "ok"

    tool = FakeTool()
    result = await tool.my_method({"customerCode": 100})

    assert result == "ok"
    assert captured["branchCode"] == 1  # injected
    assert captured["customerCode"] == 100  # preserved


@pytest.mark.asyncio
async def test_decorator_respects_explicit_value():
    captured = {}

    class FakeTool:
        @with_branch_defaults
        async def my_method(self, args):
            captured.update(args)
            return "ok"

    await FakeTool().my_method({"branchCode": 999})
    assert captured["branchCode"] == 999
