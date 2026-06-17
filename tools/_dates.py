"""
Date Range Normalization
========================
The TOTVS V2 search filters require `start < end` strictly. Passing the same
date for both ends — the natural way to ask "o que vence hoje?" — returns
`GeneralGreaterThan`. This helper expands a same-day date-only range into a full
day (00:00:00 → 23:59:59) so single-day queries just work.

Only acts when BOTH ends are present, equal and date-only (YYYY-MM-DD); any
other input (already has time, open-ended range, distinct dates) is left
untouched, so existing behavior is preserved.
"""
from __future__ import annotations

import re
from typing import Any

_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Common start/end date pairs used across TOTVS search filters.
DAY_RANGE_PAIRS: tuple[tuple[str, str], ...] = (
    ("startIssueDate", "endIssueDate"),
    ("startExpiredDate", "endExpiredDate"),
    ("startSettlementDate", "endSettlementDate"),
    ("startArrivalDate", "endArrivalDate"),
    ("startPaymentDate", "endPaymentDate"),
    ("startOrderDate", "endOrderDate"),
    ("startChangeDate", "endChangeDate"),
    ("startBillingForecastDate", "endBillingForecastDate"),
    ("startDeliveryForecastDate", "endDeliveryForecastDate"),
    ("startDeliveryDeadlineDate", "endDeliveryDeadlineDate"),
    ("startBasePaymentDate", "endBasePaymentDate"),
    ("startSuggestionDate", "endSuggestionDate"),
)


def expand_equal_day(start: Any, end: Any) -> tuple[Any, Any]:
    """Expand a same-day date-only range to cover the full day.

    ("2026-06-16", "2026-06-16") -> ("2026-06-16T00:00:00", "2026-06-16T23:59:59")
    Returns the inputs unchanged in any other case.
    """
    if (
        isinstance(start, str)
        and isinstance(end, str)
        and start == end
        and _DATE_ONLY.match(start)
    ):
        return f"{start}T00:00:00", f"{end}T23:59:59"
    return start, end


def normalize_day_ranges(
    args: dict[str, Any],
    pairs: tuple[tuple[str, str], ...] = DAY_RANGE_PAIRS,
) -> dict[str, Any]:
    """Expand same-day ranges in-place for the known start/end pairs in args."""
    for start_key, end_key in pairs:
        sv, ev = args.get(start_key), args.get(end_key)
        if sv is not None and ev is not None:
            ns, ne = expand_equal_day(sv, ev)
            if (ns, ne) != (sv, ev):
                args[start_key], args[end_key] = ns, ne
    return args
