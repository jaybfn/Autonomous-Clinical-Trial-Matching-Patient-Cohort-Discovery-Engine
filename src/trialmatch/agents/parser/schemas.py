"""Pydantic schemas for Parser LLM extraction output."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from trialmatch.domain.patient import PatientFeatures


class ExtractedLab(BaseModel):
    name: str = Field(..., min_length=1)
    value: float | None = None
    units: str | None = None
    code: str | None = None


class ParsedClinicalFeatures(BaseModel):
    """Structured extraction from a scrubbed clinical note."""

    patient_id: str = Field(..., min_length=1)
    conditions: list[str] = Field(default_factory=list)
    labs: list[ExtractedLab] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    note_summary: str | None = None

    @field_validator("patient_id")
    @classmethod
    def patient_id_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("patient_id must not be blank")
        return stripped

    def to_patient_features(self) -> PatientFeatures:
        labs: list[dict[str, Any]] = [lab.model_dump() for lab in self.labs]
        return PatientFeatures(
            patient_id=self.patient_id,
            conditions=list(self.conditions),
            labs=labs,
            note_summary=self.note_summary,
        )
