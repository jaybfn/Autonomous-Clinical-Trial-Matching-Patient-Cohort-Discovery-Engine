"""TDD contracts for ClinicalTrials.gov eligibility → trial document mapping."""

from __future__ import annotations

from pathlib import Path

import pytest

from trialmatch.data.clinicaltrials_mapper import (
    map_eligibility_record,
    read_eligibility_jsonl,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "clinicaltrials"


def test_map_eligibility_record_produces_trial_document() -> None:
    record = {
        "nct_id": "NCT01234567",
        "title": "Study of Drug X in Type 2 Diabetes",
        "status": "Recruiting",
        "inclusion_criteria": "Adults 18-75 with type 2 diabetes mellitus.",
        "exclusion_criteria": "Pregnant patients; eGFR < 30.",
    }
    doc = map_eligibility_record(record)
    assert doc["nct_id"] == "NCT01234567"
    assert doc["source"] == "clinicaltrials.gov"
    assert "type 2 diabetes" in doc["eligibility_text"].lower()
    assert "Pregnant" in doc["eligibility_text"]
    assert doc["title"] == "Study of Drug X in Type 2 Diabetes"
    assert doc["status"] == "Recruiting"


def test_map_eligibility_record_requires_nct_id() -> None:
    with pytest.raises(ValueError, match="nct_id"):
        map_eligibility_record(
            {
                "title": "No ID",
                "inclusion_criteria": "Adults",
                "exclusion_criteria": "None",
            }
        )


def test_read_eligibility_jsonl_from_fixture() -> None:
    path = FIXTURES / "eligibility.jsonl"
    docs = [map_eligibility_record(r) for r in read_eligibility_jsonl(path)]
    assert len(docs) >= 1
    assert docs[0]["nct_id"].startswith("NCT")
    assert "eligibility_text" in docs[0]
