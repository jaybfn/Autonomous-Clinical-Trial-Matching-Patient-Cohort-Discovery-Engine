"""TDD contracts for trial / match result domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from trialmatch.data.clinicaltrials_mapper import map_eligibility_record
from trialmatch.domain.trial import TrialDocument, TrialMatch, TrialMatchResult


def test_trial_document_from_clinicaltrials_shape() -> None:
    doc = TrialDocument.model_validate(
        map_eligibility_record(
            {
                "nct_id": "NCT01234567",
                "title": "Study X",
                "status": "Recruiting",
                "inclusion_criteria": "Adults with T2DM",
                "exclusion_criteria": "Pregnancy",
            }
        )
    )
    assert doc.nct_id == "NCT01234567"
    assert doc.source == "clinicaltrials.gov"
    assert "Inclusion criteria" in doc.eligibility_text


def test_trial_match_result_ranks_matches() -> None:
    result = TrialMatchResult(
        patient_id="p-001",
        matches=[
            TrialMatch(nct_id="NCT01234567", score=0.91, evidence={"vector": 0.9}),
            TrialMatch(nct_id="NCT07654321", score=0.55, evidence={"rules": ["hypertension"]}),
        ],
    )
    assert result.matches[0].score > result.matches[1].score


def test_trial_match_rejects_score_out_of_range() -> None:
    with pytest.raises(ValidationError):
        TrialMatch(nct_id="NCT01234567", score=1.5)


def test_trial_document_requires_nct_id() -> None:
    with pytest.raises(ValidationError):
        TrialDocument(
            nct_id="",
            source="clinicaltrials.gov",
            title="x",
            status="Recruiting",
            inclusion_criteria="a",
            exclusion_criteria="b",
            eligibility_text="a",
        )
