"""Canonical Pub/Sub / EPR clinical event contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    CLINICAL_RECORD = "clinical_record"
    LAB_UPDATE = "lab_update"


class EventSource(str, Enum):
    SYNTHEA = "synthea"
    EPR = "epr"
    MANUAL = "manual"


class ClinicalEvent(BaseModel):
    """Typed event consumed by ingestion and the LangGraph orchestrator."""

    event_type: EventType
    source: EventSource
    patient_id: str = Field(..., min_length=1)
    occurred_at: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("patient_id")
    @classmethod
    def patient_id_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("patient_id must not be blank")
        return stripped
