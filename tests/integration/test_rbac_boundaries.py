"""Integration: Snowflake role boundaries for Matcher vs Auditor."""

from __future__ import annotations

from typing import Any

import pytest

from trialmatch.agents.auditor.agent import AuditorAgent
from trialmatch.agents.auditor.sink import AuditSink, AuditSinkError
from trialmatch.agents.matcher.agent import MatcherAgent
from trialmatch.agents.matcher.queries import build_patient_features_sql
from trialmatch.domain.audit import AuditRecord
from trialmatch.domain.patient import PatientFeatures
from trialmatch.domain.trial import TrialMatch, TrialMatchResult
from trialmatch.services.embeddings import DeterministicEmbedder


class _RoleClient:
    def __init__(self, role: str) -> None:
        self.role = role
        self.executed: list[str] = []
        self.fetched: list[str] = []

    def execute(self, sql: str, params: Any = None) -> None:
        self.executed.append(sql)

    def fetch_all(self, sql: str, params: Any = None) -> list[dict[str, Any]]:
        self.fetched.append(sql)
        return []


class _QdrantEmpty:
    def search(self, vector: list[float], limit: int = 10) -> list[dict[str, Any]]:
        return []


def _sample_record() -> AuditRecord:
    return AuditRecord(
        correlation_id="corr-rbac",
        patient_id="p-1",
        content_hash="hash",
        agent_versions={"auditor": "0.1.0"},
        redaction_tokens={},
        justification_summary="No trials matched.",
        matched_nct_ids=[],
        extras={"match_count": 0},
    )


def test_audit_sink_rejects_agent_read_role() -> None:
    sink = AuditSink(client=_RoleClient(role="AGENT_READ_ROLE"))
    with pytest.raises(AuditSinkError, match="AUDIT_WRITE_ROLE"):
        sink.append(_sample_record())


def test_audit_sink_accepts_audit_write_role_only() -> None:
    client = _RoleClient(role="AUDIT_WRITE_ROLE")
    sink = AuditSink(client=client, schema="AUDIT")
    ids = sink.append(_sample_record())
    assert ids
    assert client.executed
    assert all("audit_match_justifications" in sql.lower() for sql in client.executed)
    assert all("marts" not in sql.lower() for sql in client.executed)
    assert all("fct_patient" not in sql.lower() for sql in client.executed)


def test_matcher_sql_is_select_only_and_targets_marts() -> None:
    sql = build_patient_features_sql(schema="MARTS").lower()
    assert sql.strip().startswith("select")
    assert "dim_trial_eligibility_features" in sql
    for verb in ("insert", "update", "delete", "merge", "truncate"):
        assert verb not in sql


def test_matcher_agent_never_calls_execute_on_snowflake() -> None:
    client = _RoleClient(role="AGENT_READ_ROLE")

    def _fetch(sql: str, params: Any = None) -> list[dict[str, Any]]:
        client.fetched.append(sql)
        if "insert" in sql.lower():
            raise AssertionError("read path issued write SQL")
        return []

    client.fetch_all = _fetch  # type: ignore[method-assign]

    agent = MatcherAgent(
        snowflake=client,
        qdrant=_QdrantEmpty(),
        embedder=DeterministicEmbedder(dimension=8),
    )
    result = agent.match(
        PatientFeatures(patient_id="p-9", conditions=["Asthma"]),
        correlation_id="c-9",
    )
    assert result.result.patient_id == "p-9"
    assert client.fetched
    assert client.executed == []


def test_auditor_does_not_require_clinical_mart_reads() -> None:
    """Auditor writes audit rows from Matcher evidence only — no mart SELECT."""
    client = _RoleClient(role="AUDIT_WRITE_ROLE")
    agent = AuditorAgent(sink=AuditSink(client=client))
    agent.audit(
        match_result=TrialMatchResult(
            patient_id="p-2",
            matches=[TrialMatch(nct_id="NCT1", score=0.5, evidence={})],
        ),
        content_hash="h2",
        redaction_tokens={"[REDACTED_EMAIL_x]": "email"},
        correlation_id="corr-2",
    )
    assert client.executed
    assert client.fetched == []
