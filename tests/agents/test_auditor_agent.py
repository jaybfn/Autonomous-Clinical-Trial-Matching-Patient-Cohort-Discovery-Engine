"""TDD contracts for Auditor agent (justifications + append-only sink)."""

from __future__ import annotations

import pytest

from trialmatch.agents.auditor.agent import AuditorAgent, AuditorError, AuditResult
from trialmatch.domain.audit import AuditRecord
from trialmatch.domain.trial import TrialMatch, TrialMatchResult


class _FakeSink:
    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> list[str]:
        self.records.append(record)
        return [f"mid-{nct}" for nct in record.matched_nct_ids]


def test_auditor_builds_record_and_writes_sink() -> None:
    sink = _FakeSink()
    agent = AuditorAgent(sink=sink)
    match_result = TrialMatchResult(
        patient_id="p-001",
        matches=[
            TrialMatch(
                nct_id="NCT01234567",
                score=0.88,
                evidence={
                    "vector_score": 0.7,
                    "vector_neighbor_id": "v1",
                    "condition_hits": ["Type 2 diabetes mellitus"],
                    "condition_misses": [],
                    "lab_hits": ["HbA1c"],
                    "lab_misses": [],
                    "title": "T2DM Study",
                },
            )
        ],
    )
    result = agent.audit(
        match_result=match_result,
        content_hash="deadbeef",
        redaction_tokens={"[REDACTED_EMAIL_ab12]": "email"},
        correlation_id="corr-42",
        agent_versions={"compliance": "0.1.0", "parser": "0.1.0", "matcher": "0.1.0"},
    )
    assert isinstance(result, AuditResult)
    assert result.record.patient_id == "p-001"
    assert result.record.content_hash == "deadbeef"
    assert result.record.matched_nct_ids == ["NCT01234567"]
    assert "NCT01234567" in result.record.justification_summary
    assert result.record.agent_versions["auditor"] == "0.1.0"
    assert result.record.agent_versions["matcher"] == "0.1.0"
    assert result.written_match_ids == ["mid-NCT01234567"]
    assert len(sink.records) == 1
    assert "ssn" not in result.record.extras
    assert "raw_note" not in result.record.extras
    assert result.record.extras.get("match_count") == 1


def test_auditor_rejects_blank_inputs() -> None:
    agent = AuditorAgent(sink=_FakeSink())
    match_result = TrialMatchResult(patient_id="p-1", matches=[])
    with pytest.raises(AuditorError, match="correlation_id"):
        agent.audit(
            match_result=match_result,
            content_hash="h",
            redaction_tokens={},
            correlation_id="  ",
        )
    with pytest.raises(AuditorError, match="content_hash"):
        agent.audit(
            match_result=match_result,
            content_hash="",
            redaction_tokens={},
            correlation_id="c1",
        )


def test_auditor_fails_closed_on_sink_error() -> None:
    class _Boom:
        def append(self, record: AuditRecord) -> list[str]:
            raise RuntimeError("warehouse down")

    agent = AuditorAgent(sink=_Boom())  # type: ignore[arg-type]
    with pytest.raises(AuditorError, match="sink"):
        agent.audit(
            match_result=TrialMatchResult(
                patient_id="p-1",
                matches=[TrialMatch(nct_id="NCT1", score=0.5, evidence={})],
            ),
            content_hash="h1",
            redaction_tokens={},
            correlation_id="c1",
        )


def test_auditor_record_survives_domain_phi_guard() -> None:
    agent = AuditorAgent(sink=_FakeSink())
    result = agent.audit(
        match_result=TrialMatchResult(patient_id="p-9", matches=[]),
        content_hash="hash9",
        redaction_tokens={"[REDACTED_PERSON_aa]": "person"},
        correlation_id="corr-9",
    )
    # Re-validate through domain model (extras must remain PHI-key free).
    again = AuditRecord.model_validate(result.record.model_dump())
    assert again.justification_summary
    assert again.extras.get("match_count") == 0
