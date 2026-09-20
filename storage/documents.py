"""Upload pipeline (sections 5-6): the sole data-ingestion path (automated
fetching is out of scope for this build). Stores the raw uploaded file,
records its metadata, runs extraction, and merges the result into that
REIT/quarter's structured QuarterlyMetrics — all through the DataStore
abstraction."""

from __future__ import annotations

from datetime import date, datetime

from engine.llm_client import LLMClient
from engine.models import DocumentType, QuarterlyMetrics, SourceRef
from extraction.extract import extract_from_document
from extraction.parsers import extract_text
from storage.data_store import DataStore

SCALAR_FIELDS = [
    "occupancy", "gross_leasing", "net_leasing", "leasing_spread",
    "rental_growth", "noi_growth", "ndcf", "ndcf_per_unit",
    "distribution_per_unit", "net_debt", "ltv", "cost_of_debt",
]


def _safe(name: str) -> str:
    return name.replace(" ", "_")


def _doc_path(reit_name: str, quarter_label: str, document_type: DocumentType, filename: str) -> str:
    return f"data/documents/{_safe(reit_name)}/{_safe(quarter_label)}/{document_type.value}/{filename}"


def _structured_path(reit_name: str, quarter_label: str) -> str:
    return f"data/structured/{_safe(reit_name)}/{_safe(quarter_label)}.json"


def upload_document(
    store: DataStore,
    llm_client: LLMClient,
    reit_name: str,
    quarter_label: str,
    quarter_end_date: date,
    document_type: DocumentType,
    filename: str,
    file_bytes: bytes,
) -> QuarterlyMetrics:
    doc_path = _doc_path(reit_name, quarter_label, document_type, filename)
    store.write_bytes(
        doc_path, file_bytes,
        commit_message=f"Upload {document_type.value} for {reit_name} {quarter_label}",
    )

    source = SourceRef(
        document_type=document_type,
        source="user upload",
        reference=filename,
        retrieved_on=datetime.utcnow().date(),
    )

    raw_text = extract_text(file_bytes, filename)
    extracted = extract_from_document(llm_client, document_type, raw_text)

    structured_path = _structured_path(reit_name, quarter_label)
    if store.exists(structured_path):
        prior = QuarterlyMetrics(**store.read_json(structured_path))
    else:
        prior = QuarterlyMetrics(
            reit_name=reit_name, quarter_label=quarter_label, quarter_end_date=quarter_end_date,
        )

    merged = _merge(prior, extracted, source)

    store.write_json(
        structured_path, merged.model_dump(mode="json"),
        commit_message=f"Update structured data for {reit_name} {quarter_label}",
    )
    return merged


def _merge(prior: QuarterlyMetrics, extracted: dict, source: SourceRef) -> QuarterlyMetrics:
    data = prior.model_dump(mode="json")
    for field in SCALAR_FIELDS:
        value = extracted.get(field)
        if value is not None:
            data[field] = value
    data["management_commentary"] = prior.management_commentary + (extracted.get("management_commentary") or [])
    data["guidance_statements"] = prior.guidance_statements + (extracted.get("guidance_statements") or [])
    data["sources"] = [s.model_dump(mode="json") for s in prior.sources] + [source.model_dump(mode="json")]
    return QuarterlyMetrics(**data)