import json

from engine.models import DocumentType
from extraction.extract import extract_from_document


class FakeLLMClient:
    def __init__(self, response: dict):
        self._response = response

    def generate_json(self, system_prompt, user_prompt):
        return json.dumps(self._response)


def test_extract_from_document_presentation():
    fake = FakeLLMClient({
        "occupancy": 91.2, "gross_leasing": None, "net_leasing": 1.3, "leasing_spread": None,
        "rental_growth": 7.4, "noi_growth": 6.1, "ndcf": None, "ndcf_per_unit": 6.3,
        "distribution_per_unit": 6.2, "net_debt": 13600.0, "ltv": 33.6, "cost_of_debt": 7.7,
        "management_commentary": [], "guidance_statements": [],
    })
    result = extract_from_document(fake, DocumentType.PRESENTATION, "Some presentation text...")
    assert result["occupancy"] == 91.2
    assert result["gross_leasing"] is None