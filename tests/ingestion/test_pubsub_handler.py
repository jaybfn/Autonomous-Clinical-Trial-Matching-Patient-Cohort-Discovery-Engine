"""TDD contracts for Pub/Sub → LangGraph ingestion handler."""

from __future__ import annotations

import json
from typing import Any

from trialmatch.ingestion.handlers import (
    HandleDisposition,
    IngestionHandler,
    extract_note_text,
    parse_clinical_event,
)
from trialmatch.orchestrator.state import MatchState


class _FakeRunner:
    def __init__(self, result: MatchState | None = None, boom: Exception | None = None) -> None:
        self.result = result
        self.boom = boom
        self.calls: list[MatchState] = []

    def run(self, state: MatchState) -> MatchState:
        self.calls.append(state)
        if self.boom:
            raise self.boom
        if self.result is not None:
            return self.result
        return {
            **state,
            "status": "ok",
            "content_hash": "h1",
            "match_result": {"patient_id": state["patient_id"], "matches": []},
            "audit_record": {"justification_summary": "ok", "matched_nct_ids": []},
            "error": None,
        }


class _FakeDlq:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def publish_poison(self, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        return "dlq-1"


def _clinical_bytes(**overrides: Any) -> bytes:
    payload = {
        "event_type": "clinical_record",
        "source": "synthea",
        "patient_id": "p-001",
        "occurred_at": "2024-02-01T12:00:00Z",
        "payload": {
            "record_kind": "clinical_note",
            "note_id": "n-001",
            "text": "Patient with type 2 diabetes",
        },
    }
    payload.update(overrides)
    return json.dumps(payload).encode("utf-8")


def test_parse_and_extract_note() -> None:
    event = parse_clinical_event(_clinical_bytes())
    assert event.patient_id == "p-001"
    assert extract_note_text(event) == "Patient with type 2 diabetes"


def test_handler_acks_successful_clinical_match() -> None:
    runner = _FakeRunner()
    handler = IngestionHandler(runner=runner, dlq=_FakeDlq())
    result = handler.handle(
        data=_clinical_bytes(),
        message_id="m-1",
        attributes={},
        subscription="clinical-records-sub",
    )
    assert result.disposition == HandleDisposition.ACK
    assert result.status == "ok"
    assert runner.calls[0]["patient_id"] == "p-001"
    assert runner.calls[0]["correlation_id"] == "m-1"
    assert "diabetes" in runner.calls[0]["note_text"]


def test_handler_skips_lab_update_without_note() -> None:
    runner = _FakeRunner()
    handler = IngestionHandler(runner=runner, dlq=_FakeDlq())
    data = json.dumps(
        {
            "event_type": "lab_update",
            "source": "synthea",
            "patient_id": "p-001",
            "payload": {"record_kind": "lab", "loinc_code": "2339-0", "value": "110"},
        }
    ).encode("utf-8")
    result = handler.handle(
        data=data,
        message_id="m-lab",
        attributes={},
        subscription="lab-updates-sub",
    )
    assert result.disposition == HandleDisposition.ACK
    assert result.status == "skipped"
    assert runner.calls == []


def test_handler_poison_invalid_json_goes_to_dlq_and_acks() -> None:
    dlq = _FakeDlq()
    handler = IngestionHandler(runner=_FakeRunner(), dlq=dlq)
    result = handler.handle(
        data=b"not-json",
        message_id="m-bad",
        attributes={},
        subscription="clinical-records-sub",
    )
    assert result.disposition == HandleDisposition.ACK
    assert result.status == "poison"
    assert len(dlq.calls) == 1
    assert dlq.calls[0]["reason"] == "invalid_json"


def test_handler_nacks_transient_graph_errors() -> None:
    handler = IngestionHandler(
        runner=_FakeRunner(boom=TimeoutError("snowflake timeout")),
        dlq=_FakeDlq(),
    )
    result = handler.handle(
        data=_clinical_bytes(),
        message_id="m-retry",
        attributes={},
        subscription="clinical-records-sub",
    )
    assert result.disposition == HandleDisposition.NACK
    assert result.status == "retry"


def test_handler_poison_when_clinical_note_missing() -> None:
    dlq = _FakeDlq()
    handler = IngestionHandler(runner=_FakeRunner(), dlq=dlq)
    data = _clinical_bytes(payload={"record_kind": "clinical_note", "note_id": "n", "text": "   "})
    result = handler.handle(
        data=data,
        message_id="m-2",
        attributes={},
        subscription="clinical-records-sub",
    )
    assert result.disposition == HandleDisposition.ACK
    assert result.status == "poison"
    assert dlq.calls[0]["reason"] == "missing_note_text"


def test_handler_nacks_transient_graph_failed_status() -> None:
    handler = IngestionHandler(
        runner=_FakeRunner(
            result={
                "patient_id": "p-001",
                "note_text": "note",
                "correlation_id": "m-3",
                "status": "failed",
                "error": "Parser failed: llm down",
                "agent_versions": {},
            }
        ),
        dlq=_FakeDlq(),
    )
    result = handler.handle(
        data=_clinical_bytes(),
        message_id="m-3",
        attributes={},
        subscription="clinical-records-sub",
    )
    assert result.disposition == HandleDisposition.NACK
    assert result.status == "retry"


def test_handler_poison_when_graph_returns_permanent_failure() -> None:
    dlq = _FakeDlq()
    handler = IngestionHandler(
        runner=_FakeRunner(
            result={
                "patient_id": "p-001",
                "note_text": "note",
                "correlation_id": "m-4",
                "status": "failed",
                "error": "Feature schema validation failed",
                "agent_versions": {},
            }
        ),
        dlq=dlq,
    )
    result = handler.handle(
        data=_clinical_bytes(),
        message_id="m-4",
        attributes={},
        subscription="clinical-records-sub",
    )
    assert result.disposition == HandleDisposition.ACK
    assert result.status == "poison"
    assert dlq.calls[0]["reason"] == "graph_failed"
