"""Prompt construction for the narrative synthesis (sections 8E/8F, 9, 10).
The trend table itself is built deterministically in trend.py and never
goes through the LLM."""

from __future__ import annotations

import json

from .models import GuidanceItem, QuarterlyMetrics

SYSTEM_PROMPT = """You are an equity research analyst producing an investment-committee-ready \
analysis of an Indian listed REIT's last five reported quarters.

Rules you must follow exactly (do not deviate):
- Do not provide five separate quarterly summaries. Compare all quarters and highlight only \
meaningful changes, trends, and inflection points.
- Do not repeat the same point in multiple sections.
- Use the latest quarter as the starting point; earlier quarters only establish the trend.
- Prefer numbers over generic commentary.
- Distinguish management guidance from actual performance.
- Distinguish organic growth from acquisition/development-led growth.
- Do not infer undisclosed information. If a metric or fact was not disclosed in the supplied \
documents, do not state or estimate it.
- Cite material numbers and management statements to the relevant presentation, transcript, or \
filing, using the source references supplied to you.
- Keep the analysis concise, analytical, and investment-committee ready.
- Core framework: Leasing -> Occupancy -> Rental Growth -> NOI -> NDCF -> Distribution -> Debt -> \
Future Growth. Ultimately answer: what changed over the last 5 quarters, why did it change, and \
what should be watched next.

Output counts (strict):
- "what_changed": exactly 5 to 8 items, the most significant changes only.
- "risks": exactly 5 to 7 items, supported only by the supplied documents.
- "catalysts": exactly 3 to 5 items, supported only by the supplied documents.
- "next_quarter_watchlist": exactly 5 to 7 metrics/events to monitor.

Respond with ONLY a single JSON object matching the schema you are given. No prose outside the \
JSON, no markdown code fences.
"""

RESPONSE_SCHEMA_HINT = """{
  "six_area": {
    "leasing_and_portfolio": "string",
    "financial_performance": "string",
    "growth": "string",
    "debt": "string",
    "management_commentary": "string",
    "guidance_vs_execution": "string"
  },
  "what_changed": [
    {"what_changed": "string", "why": "string", "current_position": "string", "why_it_matters": "string"}
  ],
  "risks": ["string"],
  "catalysts": ["string"],
  "investment_summary": "string",
  "next_quarter_watchlist": ["string"],
  "guidance_updates": [
    {"reit_name": "string", "quarter_given": "string", "guidance_text": "string",
     "status": "Delivered|On track|Delayed|Revised|Not achieved|Too early",
     "quarter_last_updated": "string"}
  ]
}"""


def build_user_prompt(
    reit_name: str,
    trend_table: list[dict],
    quarters: list[QuarterlyMetrics],
    prior_guidance: list[GuidanceItem],
) -> str:
    commentary_blocks = []
    for q in quarters:
        commentary_blocks.append({
            "quarter": q.quarter_label,
            "management_commentary": q.management_commentary,
            "guidance_statements": q.guidance_statements,
            "sources": [s.model_dump(mode="json") for s in q.sources],
        })

    payload = {
        "reit_name": reit_name,
        "trend_table": trend_table,
        "quarterly_commentary_and_sources": commentary_blocks,
        "prior_guidance_to_reassess": [g.model_dump(mode="json") for g in prior_guidance],
        "required_response_schema": json.loads(RESPONSE_SCHEMA_HINT),
    }
    return json.dumps(payload, indent=2, default=str)