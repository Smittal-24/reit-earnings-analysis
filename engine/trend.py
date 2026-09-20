"""Deterministic trend-table construction (section 8) — no LLM involved."""

from __future__ import annotations

from .models import QuarterlyMetrics

TREND_METRICS = [
    "occupancy",
    "gross_leasing",
    "net_leasing",
    "leasing_spread",
    "rental_growth",
    "noi_growth",
    "ndcf",
    "ndcf_per_unit",
    "distribution_per_unit",
    "net_debt",
    "ltv",
    "cost_of_debt",
]


def build_trend_table(quarters: list[QuarterlyMetrics]) -> list[dict]:
    """One row per quarter (latest last), only columns disclosed by at
    least one quarter in the window (section 8: "covering only the
    metrics disclosed")."""
    if not quarters:
        return []
    if len(quarters) > 5:
        raise ValueError("Trend table covers at most 5 quarters")

    ordered = sorted(quarters, key=lambda q: q.quarter_end_date)

    disclosed_metrics = [
        m for m in TREND_METRICS
        if any(getattr(q, m) is not None for q in ordered)
    ]

    rows = []
    for q in ordered:
        row = {"quarter_label": q.quarter_label}
        for m in disclosed_metrics:
            row[m] = getattr(q, m)
        rows.append(row)
    return rows