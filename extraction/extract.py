"""Structured field extraction (section 6): turns raw document text into
fields for the QuarterlyMetrics input contract.

Rules enforced here (sections 6/17): extract only what the document
actually discloses — leave a field null rather than estimate it. Which
fields a document type can populate follows section 4's "source usage"
rule: Presentation/Filing -> quantitative metrics; Transcript ->
management commentary and guidance; Other -> supplementary commentary
only, unless it clearly contains the structured disclosures too."""

from __future__ import annotations

import json

from engine.llm_client import LLMClient
from engine.models import DocumentType

EXTRACTION_SYSTEM_PROMPT = """You extract structured data from a single Indian REIT \
disclosure document (investor presentation, earnings-call transcript, exchange filing, or \
other report) for one specific reported quarter.

Rules:
- Extract ONLY figures and statements the document actually states. If a metric is not \
disclosed in this document, leave it as null. Never estimate, infer, or carry over a number \
from your own general knowledge.
- Numbers should be plain numbers (e.g. 88.5, not "88.5%") in the units the document uses.
- "management_commentary" is a list of short, specific management statements/explanations, \
not numbers already captured in the metrics fields.
- "guidance_statements" is a list of forward-looking statements management made in this \
document (targets, expected timelines, expected completions, etc).
- Respond with ONLY a single JSON object, no prose, no markdown fences.
"""

METRICS_SCHEMA_HINT = """{
  "occupancy": null, "gross_leasing": null, "net_leasing": null, "leasing_spread": null,
  "rental_growth": null, "noi_growth": null, "ndcf": null, "ndcf_per_unit": null,
  "distribution_per_unit": null, "net_debt": null, "ltv": null, "cost_of_debt": null,
  "management_commentary": [], "guidance_statements": []
}"""


def extract_from_document(
    llm_client: LLMClient,
    document_type: DocumentType,
    raw_text: str,
) -> dict:
    user_prompt = json.dumps({
        "document_type": document_type.value,
        "instructions_by_document_type": {
            "Presentation": "Focus on quantitative metrics; commentary/guidance only if explicitly stated here.",
            "Filing": "Focus on quantitative metrics; commentary/guidance only if explicitly stated here.",
            "Transcript": "Focus on management_commentary and guidance_statements; only fill metrics fields if a number is explicitly stated.",
            "Other": "Treat as supplementary context; only fill metrics fields if this document clearly and explicitly discloses them.",
        },
        "required_response_schema": json.loads(METRICS_SCHEMA_HINT),
        "document_text": raw_text[:120_000],
    })

    raw = llm_client.generate_json(EXTRACTION_SYSTEM_PROMPT, user_prompt)
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)