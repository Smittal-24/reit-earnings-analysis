import json
from datetime import date

from engine.models import DocumentType
from storage.data_store import LocalFileStore
from storage.documents import upload_document


class FakeLLMClient:
    def __init__(self, responses):
        self._responses = list(responses)

    def generate_json(self, system_prompt, user_prompt):
        return json.dumps(self._responses.pop(0))


def test_upload_document_creates_structured_record(tmp_path):
    store = LocalFileStore(tmp_path)
    fake = FakeLLMClient([
        {"occupancy": 90.9, "net_leasing": 1.2, "rental_growth": 7.1, "noi_growth": 6.0,
         "ndcf_per_unit": 6.3, "distribution_per_unit": 6.2, "net_debt": 13600.0,
         "ltv": 33.6, "cost_of_debt": 7.7, "management_commentary": ["Strong quarter"],
         "guidance_statements": []}
    ])

    result = upload_document(
        store, fake,
        reit_name="Embassy Office Parks REIT",
        quarter_label="Q2 FY26",
        quarter_end_date=date(2025, 9, 30),
        document_type=DocumentType.PRESENTATION,
        filename="q2fy26_presentation.txt",
        file_bytes=b"Some presentation text",
    )

    assert result.occupancy == 90.9
    assert len(result.sources) == 1
    assert result.sources[0].source == "user upload"
    assert store.exists("data/structured/Embassy_Office_Parks_REIT/Q2_FY26.json")


def test_upload_document_merges_across_two_uploads(tmp_path):
    store = LocalFileStore(tmp_path)
    fake = FakeLLMClient([
        {"occupancy": 90.9, "management_commentary": [], "guidance_statements": []},
        {"cost_of_debt": 7.7, "management_commentary": ["Guidance reiterated"], "guidance_statements": ["Two completions in FY27"]},
    ])

    upload_document(
        store, fake, "Embassy Office Parks REIT", "Q2 FY26", date(2025, 9, 30),
        DocumentType.PRESENTATION, "presentation.txt", b"presentation text",
    )
    result = upload_document(
        store, fake, "Embassy Office Parks REIT", "Q2 FY26", date(2025, 9, 30),
        DocumentType.TRANSCRIPT, "transcript.txt", b"transcript text",
    )

    assert result.occupancy == 90.9
    assert result.cost_of_debt == 7.7
    assert result.guidance_statements == ["Two completions in FY27"]
    assert len(result.sources) == 2