"""Trial documents and ranked match results."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class TrialDocument(BaseModel):
    """ClinicalTrials.gov-shaped eligibility document for Qdrant indexing."""

    nct_id: str = Field(..., min_length=1)
    source: str = "clinicaltrials.gov"
    title: str = ""
    status: str = ""
    inclusion_criteria: str = ""
    exclusion_criteria: str = ""
    eligibility_text: str = ""

    @field_validator("nct_id")
    @classmethod
    def nct_id_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("nct_id must not be blank")
        return stripped


class TrialMatch(BaseModel):
    nct_id: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0, le=1.0)
    evidence: dict[str, Any] = Field(default_factory=dict)


class TrialMatchResult(BaseModel):
    patient_id: str = Field(..., min_length=1)
    matches: list[TrialMatch] = Field(default_factory=list)
    notes: Optional[str] = None
