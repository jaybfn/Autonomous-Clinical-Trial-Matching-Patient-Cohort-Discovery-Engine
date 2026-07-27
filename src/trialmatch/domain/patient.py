"""Patient demographics and extracted clinical features."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class PatientDemographics(BaseModel):
    patient_id: str = Field(..., min_length=1)
    birthdate: str | None = None
    gender: str | None = None
    race: str | None = None
    ethnicity: str | None = None
    city: str | None = None
    state: str | None = None

    @field_validator("patient_id")
    @classmethod
    def patient_id_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("patient_id must not be blank")
        return stripped


class PatientFeatures(BaseModel):
    """Structured features produced by the Parser agent for Matcher input."""

    patient_id: str = Field(..., min_length=1)
    demographics: PatientDemographics | None = None
    conditions: list[str] = Field(default_factory=list)
    labs: list[dict[str, Any]] = Field(default_factory=list)
    note_summary: str | None = None

    @field_validator("patient_id")
    @classmethod
    def patient_id_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("patient_id must not be blank")
        return stripped
