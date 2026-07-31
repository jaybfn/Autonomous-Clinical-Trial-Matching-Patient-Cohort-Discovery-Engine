"""TDD contracts for append-only audit sink (AUDIT_WRITE_ROLE only)."""

from __future__ import annotations

from typing import Any

import pytest

from trialmatch.agents.auditor.sink import AuditSink, AuditSinkError, build_match_id
from trialmatch.domain.audit import AuditRecord


class _FakeClient:
    def __init__(self, role: str) -> None:
        self.role = role
        self.executions: list[tuple[str, Any]] = []

    def execute(self, sql: str, params: Any = None) -> None:
        self.executions.append((sql, params))


def _sample_record() -> AuditRecord:
    return AuditRecord(
        correlation_id="corr-1",
        patient_id="p-001",
        content_hash="hashabc",
        agent_versions={"auditor": "0.1.0"},
        redaction_tokens={"[REDACTED_EMAIL_x]": "email"},
        justification_summary="Matched NCT1 due to diabetes features.",
        matched_nct_ids=["NCT1", "NCT2"],
        extras={"match_count": 2},
    )


def test_sink_requires_audit_write_role() -> None:
    sink = AuditSink(client=_FakeClient(role="AGENT_READ_ROLE"))
    with pytest.raises(AuditSinkError, match="AUDIT_WRITE_ROLE"):
        sink.append(_sample_record())


def test_sink_inserts_one_row_per_nct() -> None:
    client = _FakeClient(role="AUDIT_WRITE_ROLE")
    sink = AuditSink(client=client, schema="AUDIT")
    match_ids = sink.append(_sample_record())
    assert len(match_ids) == 2
    assert len(client.executions) == 2
    sql, params = client.executions[0]
    assert "insert" in sql.lower()
    assert "audit_match_justifications" in sql.lower()
    assert "delete" not in sql.lower()
    assert params[1] == "p-001"
    assert params[2] == "NCT1"
    assert params[4] == "auditor"
    assert params[5] == "corr-1"


def test_match_id_is_deterministic() -> None:
    a = build_match_id(correlation_id="c", nct_id="NCT1", content_hash="h")
    b = build_match_id(correlation_id="c", nct_id="NCT1", content_hash="h")
    c = build_match_id(correlation_id="c", nct_id="NCT2", content_hash="h")
    assert a == b
    assert a != c
    assert len(a) == 32


def test_sink_rejects_unsafe_schema() -> None:
    sink = AuditSink(client=_FakeClient(role="AUDIT_WRITE_ROLE"), schema="AUDIT; DROP")
    with pytest.raises(AuditSinkError, match="schema"):
        sink.append(_sample_record())
