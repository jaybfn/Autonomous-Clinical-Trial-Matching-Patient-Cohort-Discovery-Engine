"""HTTP request/response models for the match API (no raw note echo)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class MatchRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    note_text: str = Field(..., min_length=1)
    correlation_id: str | None = None

    @field_validator("patient_id", "note_text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class MatchItem(BaseModel):
    nct_id: str
    score: float
    evidence: dict[str, Any] = Field(default_factory=dict)


class MatchResponse(BaseModel):
    correlation_id: str
    patient_id: str
    status: str
    matches: list[MatchItem] = Field(default_factory=list)
    justification_summary: str | None = None
    content_hash: str | None = None
    written_match_ids: list[str] = Field(default_factory=list)
    agent_versions: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str = "trialmatch-api"
