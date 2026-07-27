"""Immutable audit record contracts for the Auditor agent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

FORBIDDEN_AUDIT_EXTRA_KEYS = frozenset(
    {
        "ssn",
        "mrn",
        "email",
        "phone",
        "address",
        "dob",
        "birthdate",
        "name",
        "full_name",
        "text",
        "raw_note",
    }
)


class AuditRecord(BaseModel):
    """Append-only audit payload — PII-free justification + provenance."""

    correlation_id: str = Field(..., min_length=1)
    patient_id: str = Field(..., min_length=1)
    content_hash: str = Field(..., min_length=1)
    agent_versions: dict[str, str] = Field(default_factory=dict)
    redaction_tokens: dict[str, str] = Field(default_factory=dict)
    justification_summary: str = Field(..., min_length=1)
    matched_nct_ids: list[str] = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None

    @field_validator("correlation_id", "patient_id", "content_hash", "justification_summary")
    @classmethod
    def not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field must not be blank")
        return stripped

    @model_validator(mode="after")
    def extras_must_not_contain_phi_keys(self) -> AuditRecord:
        banned = FORBIDDEN_AUDIT_EXTRA_KEYS.intersection({k.lower() for k in self.extras})
        if banned:
            raise ValueError(f"extras contain forbidden PHI keys: {sorted(banned)}")
        return self
