"""Data models for the REIT earnings analysis engine.

Define the input contract (per-quarter structured metrics, section 6) and
the output contract (analysis results, sections 8-10). The engine never
parses raw documents itself — extraction happens upstream and hands the
engine QuarterlyMetrics objects.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DocumentType(str, Enum):
    PRESENTATION = "Presentation"
    TRANSCRIPT = "Transcript"
    FILING = "Filing"
    OTHER = "Other"


class SourceRef(BaseModel):
    """Where a piece of data came from — required for citations (section 17)."""

    document_type: DocumentType
    source: str  # "fetched" or "user upload"
    reference: str  # URL, filing reference, or filename
    retrieved_on: Optional[date] = None


class QuarterlyMetrics(BaseModel):
    """Structured, per-quarter data for one REIT (section 6).

    Only fields the REIT actually disclosed should be populated — leave
    everything else None rather than estimating (section 17).
    """

    reit_name: str
    quarter_label: str  # e.g. "Q1 FY26"
    quarter_end_date: date

    occupancy: Optional[float] = None
    gross_leasing: Optional[float] = None
    net_leasing: Optional[float] = None
    leasing_spread: Optional[float] = None
    rental_growth: Optional[float] = None
    noi_growth: Optional[float] = None
    ndcf: Optional[float] = None
    ndcf_per_unit: Optional[float] = None
    distribution_per_unit: Optional[float] = None
    net_debt: Optional[float] = None
    ltv: Optional[float] = None
    cost_of_debt: Optional[float] = None

    management_commentary: list[str] = Field(default_factory=list)
    guidance_statements: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)


class GuidanceStatus(str, Enum):
    DELIVERED = "Delivered"
    ON_TRACK = "On track"
    DELAYED = "Delayed"
    REVISED = "Revised"
    NOT_ACHIEVED = "Not achieved"
    TOO_EARLY = "Too early"


class GuidanceItem(BaseModel):
    reit_name: str
    quarter_given: str
    guidance_text: str
    status: GuidanceStatus
    quarter_last_updated: str


class WhatChangedItem(BaseModel):
    what_changed: str
    why: str
    current_position: str
    why_it_matters: str


class SixAreaAnalysis(BaseModel):
    leasing_and_portfolio: str
    financial_performance: str
    growth: str
    debt: str
    management_commentary: str
    guidance_vs_execution: str


class AnalysisResult(BaseModel):
    reit_name: str
    quarters_covered: list[str]
    trend_table: list[dict]
    six_area: SixAreaAnalysis
    what_changed: list[WhatChangedItem]
    risks: list[str]
    catalysts: list[str]
    investment_summary: str
    next_quarter_watchlist: list[str]
    guidance_updates: list[GuidanceItem] = Field(default_factory=list)

    @field_validator("what_changed")
    @classmethod
    def _check_what_changed_count(cls, v):
        if not (5 <= len(v) <= 8):
            raise ValueError(f"what_changed must have 5-8 items, got {len(v)}")
        return v

    @field_validator("risks")
    @classmethod
    def _check_risks_count(cls, v):
        if not (5 <= len(v) <= 7):
            raise ValueError(f"risks must have 5-7 items, got {len(v)}")
        return v

    @field_validator("catalysts")
    @classmethod
    def _check_catalysts_count(cls, v):
        if not (3 <= len(v) <= 5):
            raise ValueError(f"catalysts must have 3-5 items, got {len(v)}")
        return v

    @field_validator("next_quarter_watchlist")
    @classmethod
    def _check_watchlist_count(cls, v):
        if not (5 <= len(v) <= 7):
            raise ValueError(f"next_quarter_watchlist must have 5-7 items, got {len(v)}")
        return v