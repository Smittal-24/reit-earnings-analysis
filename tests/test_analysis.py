"""Unit tests for the analysis engine — fixture data + a fake LLM client,
so these never make a real API call."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.analysis import AnalysisEngine
from engine.models import AnalysisResult, GuidanceStatus, QuarterlyMetrics
from engine.trend import build_trend_table

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "embassy_5q.json"


def load_fixture_quarters() -> list[QuarterlyMetrics]:
    raw = json.loads(FIXTURE_PATH.read_text())
    return [QuarterlyMetrics(**q) for q in raw]


class FakeLLMClient:
    def __init__(self, response: dict):
        self._response = response
        self.last_system_prompt = None
        self.last_user_prompt = None

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return json.dumps(self._response)


def _valid_llm_response() -> dict:
    return {
        "six_area": {
            "leasing_and_portfolio": "Occupancy rose steadily from 88.5% to 90.9% over five quarters.",
            "financial_performance": "NOI growth held in the 5-6% range with NDCF/unit up from 5.8 to 6.3.",
            "growth": "No acquisitions disclosed; growth has been organic leasing-led, with two development completions guided for FY27.",
            "debt": "LTV drifted up from 32.1% to 33.6% while cost of debt eased from 7.9% to 7.7%.",
            "management_commentary": "Tone shifted from cautious to confident on GCC-led demand by Q1 FY26.",
            "guidance_vs_execution": "The 90% occupancy target for FY26 was delivered a year early in Q1 FY26.",
        },
        "what_changed": [
            {"what_changed": "Occupancy crossed 90%", "why": "GCC-led leasing demand", "current_position": "90.9% in Q2 FY26", "why_it_matters": "Ahead of prior guidance"},
            {"what_changed": "Cost of debt declined", "why": "Refinancing at lower rates", "current_position": "7.7%", "why_it_matters": "Supports NDCF"},
            {"what_changed": "LTV drifted higher", "why": "Debt-funded capex", "current_position": "33.6%", "why_it_matters": "Reduces headroom"},
            {"what_changed": "Occupancy guidance achieved early", "why": "Faster-than-expected leasing", "current_position": "Delivered in Q1 FY26 vs FY26 target", "why_it_matters": "Signals management credibility"},
            {"what_changed": "Construction cost inflation flagged", "why": "Broader input cost pressure", "current_position": "Flagged in Q2 FY26 commentary", "why_it_matters": "Risk to development returns"},
        ],
        "risks": [
            "Rising construction costs on the development pipeline",
            "LTV trending upward toward the higher end of its recent range",
            "Concentration in GCC tenant demand",
            "No disclosed leasing spread data limits visibility into re-leasing economics",
            "Development completions in FY27 are not yet locked in",
        ],
        "catalysts": [
            "Continued GCC-led leasing demand",
            "Further cost-of-debt reduction via refinancing",
            "Two new development completions guided for FY27",
        ],
        "investment_summary": "Operating trend is positive with occupancy ahead of guidance and NDCF/unit rising steadily; leverage bears watching.",
        "next_quarter_watchlist": [
            "Occupancy trajectory beyond 91%",
            "Leasing spread disclosure",
            "LTV direction",
            "Cost of debt trend",
            "Progress on FY27 development completions",
        ],
        "guidance_updates": [
            {"reit_name": "Embassy Office Parks REIT", "quarter_given": "Q2 FY25",
             "guidance_text": "Targeting occupancy above 90% by FY26.", "status": "Delivered",
             "quarter_last_updated": "Q1 FY26"}
        ],
    }


def test_build_trend_table_only_includes_disclosed_metrics():
    quarters = load_fixture_quarters()
    table = build_trend_table(quarters)

    assert len(table) == 5
    assert "gross_leasing" not in table[0]
    assert "leasing_spread" not in table[0]
    assert "ndcf" not in table[0]
    assert "occupancy" in table[0]
    assert table[0]["quarter_label"] == "Q2 FY25"
    assert table[-1]["quarter_label"] == "Q2 FY26"


def test_build_trend_table_rejects_more_than_5_quarters():
    quarters = load_fixture_quarters() * 2
    with pytest.raises(ValueError):
        build_trend_table(quarters)


def test_build_trend_table_empty_input():
    assert build_trend_table([]) == []


def test_analysis_engine_runs_with_fake_llm():
    quarters = load_fixture_quarters()
    fake = FakeLLMClient(_valid_llm_response())
    engine = AnalysisEngine(llm_client=fake)

    result = engine.run("Embassy Office Parks REIT", quarters)

    assert result.reit_name == "Embassy Office Parks REIT"
    assert len(result.quarters_covered) == 5
    assert 5 <= len(result.what_changed) <= 8
    assert 5 <= len(result.risks) <= 7
    assert 3 <= len(result.catalysts) <= 5
    assert result.guidance_updates[0].status == GuidanceStatus.DELIVERED
    assert "Embassy Office Parks REIT" in fake.last_user_prompt
    assert "Do not infer undisclosed information" in fake.last_system_prompt


def test_analysis_engine_rejects_mixed_reits():
    quarters = load_fixture_quarters()
    quarters[0].reit_name = "Mindspace Business Parks REIT"
    fake = FakeLLMClient(_valid_llm_response())
    engine = AnalysisEngine(llm_client=fake)

    with pytest.raises(ValueError):
        engine.run("Embassy Office Parks REIT", quarters)


def test_result_model_rejects_wrong_what_changed_count():
    bad = _valid_llm_response()
    bad["what_changed"] = bad["what_changed"][:2]

    with pytest.raises(Exception):
        AnalysisResult(
            reit_name="Embassy Office Parks REIT",
            quarters_covered=["Q2 FY26"],
            trend_table=[],
            six_area=bad["six_area"],
            what_changed=bad["what_changed"],
            risks=bad["risks"],
            catalysts=bad["catalysts"],
            investment_summary=bad["investment_summary"],
            next_quarter_watchlist=bad["next_quarter_watchlist"],
        )