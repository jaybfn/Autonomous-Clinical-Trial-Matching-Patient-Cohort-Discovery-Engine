"""TDD contracts for immutable audit record domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from trialmatch.domain.audit import AuditRecord


def test_audit_record_requires_provenance_fields() -> None:
    record = AuditRecord(
        correlation_id="corr-001",
        patient_id="p-001",
        content_hash="abc123",
        agent_versions={"compliance": "0.1.0", "matcher": "0.1.0", "auditor": "0.1.0"},
        redaction_tokens={"PERSON_1": "[REDACTED_PERSON_1]"},
        justification_summary="Matched NCT01234567 due to T2DM + A1c range.",
        matched_nct_ids=["NCT01234567"],
    )
    assert record.correlation_id == "corr-001"
    assert "PERSON_1" in record.redaction_tokens
    assert record.matched_nct_ids == ["NCT01234567"]


def test_audit_record_forbids_raw_phi_keys_in_justification_extras() -> None:
    with pytest.raises(ValidationError):
        AuditRecord(
            correlation_id="corr-001",
            patient_id="p-001",
            content_hash="abc123",
            agent_versions={"auditor": "0.1.0"},
            redaction_tokens={},
            justification_summary="ok",
            matched_nct_ids=[],
            extras={"ssn": "078-05-1120"},
        )


def test_audit_record_rejects_empty_content_hash() -> None:
    with pytest.raises(ValidationError):
        AuditRecord(
            correlation_id="corr-001",
            patient_id="p-001",
            content_hash="",
            agent_versions={},
            redaction_tokens={},
            justification_summary="x",
            matched_nct_ids=[],
        )
