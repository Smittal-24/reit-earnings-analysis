"""The analysis engine (section 7): orchestrates the deterministic trend
table plus the LLM-driven narrative synthesis (sections 8E/8F, 9, 10).

This is the single entry point the rest of the app calls — the dashboard,
manual run pipeline, and report generators should only ever call
AnalysisEngine.run, never touch prompts or the LLM client directly.
"""

from __future__ import annotations

import json

from .llm_client import LLMClient
from .models import AnalysisResult, GuidanceItem, QuarterlyMetrics, SixAreaAnalysis
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .trend import build_trend_table


class AnalysisEngine:
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    def run(
        self,
        reit_name: str,
        quarters: list[QuarterlyMetrics],
        prior_guidance: list[GuidanceItem] | None = None,
    ) -> AnalysisResult:
        prior_guidance = prior_guidance or []

        if not quarters:
            raise ValueError("At least one quarter of data is required")
        if any(q.reit_name != reit_name for q in quarters):
            raise ValueError("All quarters must belong to the same REIT")
        if len(quarters) > 5:
            raise ValueError("Analysis covers at most 5 quarters")

        ordered = sorted(quarters, key=lambda q: q.quarter_end_date)
        trend_table = build_trend_table(ordered)

        user_prompt = build_user_prompt(reit_name, trend_table, ordered, prior_guidance)
        raw = self._llm.generate_json(SYSTEM_PROMPT, user_prompt)
        parsed = _parse_llm_json(raw)

        return AnalysisResult(
            reit_name=reit_name,
            quarters_covered=[q.quarter_label for q in ordered],
            trend_table=trend_table,
            six_area=SixAreaAnalysis(**parsed["six_area"]),
            what_changed=parsed["what_changed"],
            risks=parsed["risks"],
            catalysts=parsed["catalysts"],
            investment_summary=parsed["investment_summary"],
            next_quarter_watchlist=parsed["next_quarter_watchlist"],
            guidance_updates=parsed.get("guidance_updates", []),
        )


def _parse_llm_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {e}\nRaw output:\n{raw}") from e