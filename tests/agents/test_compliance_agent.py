"""TDD end-to-end contracts for the Compliance agent."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from trialmatch.agents.compliance.agent import ComplianceAgent, ComplianceError
from trialmatch.domain.events import ClinicalEvent, EventSource, EventType

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "notes_with_pii.txt"


@pytest.fixture
def note_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_compliance_agent_scrubs_planted_phi(note_text: str) -> None:
    agent = ComplianceAgent()
    result = agent.scrub(note_text, correlation_id="corr-1")

    assert "jane.doe@example.com" not in result.scrubbed_text.lower()
    assert "617-555-0100" not in result.scrubbed_text
    assert "078-05-1120" not in result.scrubbed_text
    assert "1234567" not in result.scrubbed_text
    assert "Jane Doe" not in result.scrubbed_text
    assert result.redaction_count >= 4
    assert result.content_hash
    # Tokens appear in scrubbed text and map to entity types (not raw PHI).
    assert result.redaction_map
    for token, entity_type in result.redaction_map.items():
        assert token.startswith("[REDACTED_")
        assert entity_type in {"email", "phone", "ssn", "mrn", "dob", "person", "address"}
        assert token in result.scrubbed_text


def test_redaction_tokens_are_stable_for_same_value(note_text: str) -> None:
    agent = ComplianceAgent()
    a = agent.scrub(note_text)
    b = agent.scrub(note_text)
    assert a.redaction_map == b.redaction_map
    assert a.scrubbed_text == b.scrubbed_text
    assert a.content_hash == b.content_hash


def test_scrubbed_output_never_logged_as_raw_note(
    note_text: str, caplog: pytest.LogCaptureFixture
) -> None:
    agent = ComplianceAgent()
    with caplog.at_level(logging.INFO):
        result = agent.scrub(note_text, correlation_id="corr-log")
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "jane.doe@example.com" not in joined.lower()
    assert "078-05-1120" not in joined
    assert result.scrubbed_text  # still produced


def test_scrub_event_replaces_payload_note_text(note_text: str) -> None:
    agent = ComplianceAgent()
    event = ClinicalEvent(
        event_type=EventType.CLINICAL_RECORD,
        source=EventSource.SYNTHEA,
        patient_id="p-001",
        payload={"note_text": note_text, "note_id": "n-001"},
    )
    scrubbed_event, result = agent.scrub_event(event)
    assert "jane.doe@example.com" not in scrubbed_event.payload["note_text"].lower()
    assert scrubbed_event.payload["note_id"] == "n-001"
    assert result.redaction_count >= 1


def test_compliance_fails_closed_on_ner_failure() -> None:
    class _Boom:
        def find_entities(self, text: str):  # noqa: ANN001
            raise RuntimeError("ner backend down")

    agent = ComplianceAgent(ner=_Boom())
    with pytest.raises(ComplianceError):
        agent.scrub("Patient Jane Doe has diabetes.")
