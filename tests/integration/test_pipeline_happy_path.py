"""Integration: full Compliance→Parser→Matcher→Auditor with mocked externals."""

from __future__ import annotations

import json
from typing import Any

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from trialmatch.agents.auditor.agent import AuditorAgent
from trialmatch.agents.auditor.sink import AuditSink
from trialmatch.agents.compliance.agent import ComplianceAgent
from trialmatch.agents.matcher.agent import MatcherAgent
from trialmatch.agents.parser.agent import ParserAgent
from trialmatch.observability.tracing import configure_tracing
from trialmatch.orchestrator.graph import AgentBundle, build_match_graph, run_match_graph
from trialmatch.orchestrator.state import initial_match_state
from trialmatch.services.embeddings import DeterministicEmbedder


class _FakeLlm:
    def complete_json(self, *, system: str, user: str) -> str:
        assert "REDACTED" in user or "diabetes" in user.lower()
        return json.dumps(
            {
                "conditions": ["Type 2 diabetes mellitus"],
                "labs": [{"name": "HbA1c", "value": 8.1, "units": "%", "code": "4548-4"}],
                "medications": ["metformin"],
                "note_summary": "Adult with diabetes",
            }
        )


class _FakeSnowflake:
    """AGENT_READ_ROLE stand-in — SELECT only."""

    role = "AGENT_READ_ROLE"

    def __init__(self) -> None:
        self.fetch_calls = 0
        self.execute_calls = 0

    def fetch_all(self, sql: str, params: Any = None) -> list[dict[str, Any]]:
        self.fetch_calls += 1
        assert "insert" not in sql.lower()
        return [
            {
                "feature_type": "condition",
                "feature_code": "44054006",
                "feature_label": "Type 2 diabetes mellitus",
                "feature_value": None,
                "feature_units": None,
            }
        ]

    def execute(self, sql: str, params: Any = None) -> None:
        self.execute_calls += 1
        raise AssertionError("Matcher read path must not call execute/INSERT")


class _FakeQdrant:
    def search(self, vector: list[float], limit: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "id": "vec-1",
                "score": 0.7,
                "payload": {
                    "nct_id": "NCT01234567",
                    "title": "T2DM Study",
                    "eligibility_text": (
                        "Inclusion: Adults with Type 2 diabetes mellitus. Labs: HbA1c."
                    ),
                },
            }
        ]


class _RecordingWriteClient:
    role = "AUDIT_WRITE_ROLE"

    def __init__(self) -> None:
        self.inserts: list[tuple[str, Any]] = []

    def execute(self, sql: str, params: Any = None) -> None:
        assert "insert" in sql.lower()
        assert "audit_match_justifications" in sql.lower()
        self.inserts.append((sql, params))


def test_pipeline_happy_path_end_to_end_with_mocked_backends() -> None:
    exporter = InMemorySpanExporter()
    configure_tracing(service_name="trialmatch-integration", memory_exporter=exporter, force=True)

    snowflake = _FakeSnowflake()
    write_client = _RecordingWriteClient()
    agents = AgentBundle(
        compliance=ComplianceAgent(),
        parser=ParserAgent(llm=_FakeLlm()),
        matcher=MatcherAgent(
            snowflake=snowflake,
            qdrant=_FakeQdrant(),
            embedder=DeterministicEmbedder(dimension=8),
            schema="MARTS",
            vector_limit=5,
        ),
        auditor=AuditorAgent(sink=AuditSink(client=write_client, schema="AUDIT")),
    )
    graph = build_match_graph(agents)
    note = (
        "Patient Jane Doe email secret@example.com presents with Type 2 diabetes mellitus. "
        "HbA1c elevated."
    )
    final = run_match_graph(
        graph,
        initial_match_state(
            patient_id="p-001",
            note_text=note,
            correlation_id="corr-int-1",
        ),
    )

    assert final["status"] == "ok"
    assert final.get("error") in (None, "")
    assert final["content_hash"]
    assert "[REDACTED_" in (final.get("scrubbed_text") or "")
    assert "secret@example.com" not in (final.get("scrubbed_text") or "")
    matches = final["match_result"]["matches"]
    assert matches
    assert matches[0]["nct_id"] == "NCT01234567"
    assert matches[0]["score"] > 0
    assert final["audit_record"]["matched_nct_ids"] == ["NCT01234567"]
    assert "ssn" not in final["audit_record"].get("extras", {})
    assert snowflake.fetch_calls >= 1
    assert snowflake.execute_calls == 0
    assert write_client.inserts
    assert final["agent_versions"]["compliance"]
    assert final["agent_versions"]["parser"]
    assert final["agent_versions"]["matcher"]
    assert final["agent_versions"]["auditor"]

    span_names = {span.name for span in exporter.get_finished_spans()}
    assert "orchestrator.compliance" in span_names
    assert "orchestrator.parser" in span_names
    assert "orchestrator.matcher" in span_names
    assert "orchestrator.auditor" in span_names
    for span in exporter.get_finished_spans():
        attrs = dict(span.attributes or {})
        assert "ssn" not in attrs
        assert "text" not in attrs
        assert "email" not in attrs
