"""
Usage Analyzer
==============
Analyzes tool usage patterns from the tracker log.

Detects:
1. Most used tools (frequency ranking)
2. Common sequences (tool A → tool B)
3. Time-of-day patterns (peak usage hours)
4. Parameter patterns (common filters, default values)
5. Suggested optimizations (composite tools, pre-fetch candidates)

No company-specific logic — works for any TOTVS Moda installation.
"""
import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from usage_tracker import read_log

logger = logging.getLogger("totvs-moda-mcp.analyzer")

# Max gap (seconds) between calls to consider them part of the same session
SESSION_GAP = 600  # 10 minutes


def analyze(days: int = 30) -> dict[str, Any]:
    """Full analysis of usage patterns.

    Args:
        days: how many days back to analyze (default 30)

    Returns:
        {
          totalCalls, uniqueTools, period,
          topTools, sequences, peakHours,
          paramPatterns, suggestions
        }
    """
    entries = read_log()
    if not entries:
        return {"totalCalls": 0, "message": "No usage data yet. Use the MCP tools and insights will appear here."}

    # Filter by date range
    cutoff = datetime.utcnow().timestamp() - (days * 86400)
    filtered = []
    for e in entries:
        try:
            ts = datetime.fromisoformat(e["ts"].replace("Z", "+00:00")).timestamp()
            if ts >= cutoff:
                filtered.append(e)
        except (KeyError, ValueError):
            continue

    if not filtered:
        return {"totalCalls": 0, "message": f"No usage data in the last {days} days."}

    return {
        "period": {"days": days, "totalCalls": len(filtered)},
        "topTools": _top_tools(filtered),
        "sequences": _sequences(filtered),
        "peakHours": _peak_hours(filtered),
        "paramPatterns": _param_patterns(filtered),
        "suggestions": _suggestions(filtered),
        "performance": _performance(filtered),
    }


def _top_tools(entries: list[dict]) -> list[dict[str, Any]]:
    """Rank tools by usage frequency."""
    counter = Counter(e["tool"] for e in entries)
    total = len(entries)
    return [
        {
            "tool": tool,
            "count": count,
            "percentage": round(count / total * 100, 1),
        }
        for tool, count in counter.most_common(15)
    ]


def _sequences(entries: list[dict]) -> list[dict[str, Any]]:
    """Detect common tool sequences (A → B patterns).

    Groups entries into sessions (gap < SESSION_GAP), then counts
    consecutive pairs.
    """
    sessions = _split_sessions(entries)
    pair_counter: Counter[tuple[str, str]] = Counter()

    for session in sessions:
        tools = [e["tool"] for e in session]
        for i in range(len(tools) - 1):
            pair = (tools[i], tools[i + 1])
            pair_counter[pair] += 1

    # Only return sequences that happened 2+ times
    return [
        {"from": a, "to": b, "count": count}
        for (a, b), count in pair_counter.most_common(10)
        if count >= 2
    ]


def _peak_hours(entries: list[dict]) -> list[dict[str, Any]]:
    """Identify peak usage hours."""
    hour_counter: Counter[int] = Counter()
    for e in entries:
        try:
            ts = datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))
            hour_counter[ts.hour] += 1
        except (KeyError, ValueError):
            continue

    if not hour_counter:
        return []

    total = sum(hour_counter.values())
    return [
        {"hour": h, "calls": c, "percentage": round(c / total * 100, 1)}
        for h, c in sorted(hour_counter.items(), key=lambda x: x[1], reverse=True)[:5]
    ]


def _param_patterns(entries: list[dict]) -> list[dict[str, Any]]:
    """Detect common parameter values per tool.

    Finds values that appear in 70%+ of calls for a given tool+param.
    These are candidates for default values.
    """
    # tool → param → value → count
    tool_params: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    tool_counts: Counter[str] = Counter()

    for e in entries:
        tool = e.get("tool", "")
        params = e.get("params", {})
        tool_counts[tool] += 1
        for k, v in params.items():
            if k.startswith("_"):
                continue
            # Normalize value for counting
            val_key = str(v) if not isinstance(v, (list, dict)) else str(sorted(v) if isinstance(v, list) else v)
            tool_params[tool][k][val_key] += 1

    patterns = []
    for tool, params in tool_params.items():
        total = tool_counts[tool]
        if total < 3:  # Need enough data
            continue
        for param, values in params.items():
            top_val, top_count = values.most_common(1)[0]
            ratio = top_count / total
            if ratio >= 0.7:
                patterns.append({
                    "tool": tool,
                    "param": param,
                    "dominantValue": top_val,
                    "frequency": f"{ratio:.0%}",
                    "suggestion": f"Consider making '{top_val}' the default for {param} in {tool}",
                })

    return patterns[:10]


def _suggestions(entries: list[dict]) -> list[dict[str, Any]]:
    """Generate optimization suggestions based on patterns."""
    suggestions = []
    sequences = _sequences(entries)
    top_tools = _top_tools(entries)

    # Suggestion: frequent sequences → composite tool
    for seq in sequences[:3]:
        if seq["count"] >= 3:
            suggestions.append({
                "type": "composite_tool",
                "reason": f"'{seq['from']}' is followed by '{seq['to']}' {seq['count']} times",
                "suggestion": f"Consider a composite tool that combines {seq['from']} + {seq['to']} in one call",
                "impact": "high" if seq["count"] >= 5 else "medium",
            })

    # Suggestion: heavy tools that could benefit from cache
    for t in top_tools[:5]:
        if t["count"] >= 5 and "search" in t["tool"]:
            suggestions.append({
                "type": "cache_candidate",
                "reason": f"'{t['tool']}' called {t['count']} times ({t['percentage']}% of all calls)",
                "suggestion": f"Ensure response_cache covers {t['tool']} with appropriate TTL",
                "impact": "high" if t["count"] >= 10 else "medium",
            })

    # Suggestion: detect morning briefing pattern
    sessions = _split_sessions(entries)
    morning_tools: Counter[str] = Counter()
    for session in sessions:
        if not session:
            continue
        try:
            ts = datetime.fromisoformat(session[0]["ts"].replace("Z", "+00:00"))
            if 7 <= ts.hour <= 10:
                for e in session[:5]:  # first 5 tools of morning session
                    morning_tools[e["tool"]] += 1
        except (KeyError, ValueError):
            continue

    if morning_tools and sum(morning_tools.values()) >= 5:
        top_morning = morning_tools.most_common(3)
        suggestions.append({
            "type": "routine",
            "reason": f"Morning sessions frequently start with: {', '.join(t for t, _ in top_morning)}",
            "suggestion": "Consider a 'morning briefing' composite tool with these queries pre-bundled",
            "impact": "high",
        })

    return suggestions


def _performance(entries: list[dict]) -> dict[str, Any]:
    """Analyze response times by tool."""
    tool_times: dict[str, list[float]] = defaultdict(list)
    for e in entries:
        if "duration_ms" in e:
            tool_times[e["tool"]].append(e["duration_ms"])

    if not tool_times:
        return {"message": "No duration data available yet."}

    stats = []
    for tool, times in sorted(tool_times.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True):
        avg = sum(times) / len(times)
        stats.append({
            "tool": tool,
            "avgMs": round(avg),
            "maxMs": round(max(times)),
            "calls": len(times),
        })

    return {"byTool": stats[:10]}


def _split_sessions(entries: list[dict]) -> list[list[dict]]:
    """Split entries into sessions based on time gaps."""
    if not entries:
        return []

    sessions: list[list[dict]] = []
    current: list[dict] = [entries[0]]
    prev_ts = _parse_ts(entries[0])

    for e in entries[1:]:
        ts = _parse_ts(e)
        if ts and prev_ts and (ts - prev_ts) > SESSION_GAP:
            sessions.append(current)
            current = []
        current.append(e)
        if ts:
            prev_ts = ts

    if current:
        sessions.append(current)

    return sessions


def _parse_ts(entry: dict) -> float | None:
    try:
        return datetime.fromisoformat(entry["ts"].replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError):
        return None
