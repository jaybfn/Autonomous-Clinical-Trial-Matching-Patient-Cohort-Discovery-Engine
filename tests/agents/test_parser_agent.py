"""TDD contracts for Parser agent — LLM mocked; Vertex never called."""

from __future__ import annotations

import json
import logging

import pytest

from trialmatch.agents.compliance.agent import ComplianceAgent
from trialmatch.agents.parser.agent import ParserAgent, ParserError
from trialmatch.agents.parser.prompts import SYSTEM_PROMPT, build_user_prompt
from trialmatch.agents.parser.schemas import ParsedClinicalFeatures


class FakeLlm:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    def complete_json(self, *, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        return json.dumps(self.payload)


def test_parser_returns_validated_features_from_scrubbed_note() -> None:
    raw = (
        "Patient Jane Doe MRN 1234567 presents with hyperglycemia. "
        "A1c 7.8%. Continue metformin. Email jane.doe@example.com."
    )
    scrubbed = ComplianceAgent().scrub(raw).scrubbed_text
    assert "jane.doe@example.com" not in scrubbed.lower()

    llm = FakeLlm(
        {
            "conditions": ["hyperglycemia", "type 2 diabetes mellitus"],
            "labs": [{"name": "HbA1c", "value": 7.8, "units": "%", "code": "4548-4"}],
            "medications": ["metformin"],
            "note_summary": "Hyperglycemia with elevated A1c; continue metformin.",
        }
    )
    agent = ParserAgent(llm=llm)
    result = agent.parse(scrubbed_text=scrubbed, patient_id="p-001", correlation_id="c-1")

    assert isinstance(result.features, ParsedClinicalFeatures)
    assert result.features.patient_id == "p-001"
    assert "metformin" in result.features.medications
    assert result.features.labs[0].value == 7.8
    assert llm.calls and "jane.doe@example.com" not in llm.calls[0]["user"].lower()
    assert "Jane Doe" not in llm.calls[0]["user"]


def test_system_prompt_has_no_patient_identifiers() -> None:
    lowered = SYSTEM_PROMPT.lower()
    assert "ssn" not in lowered or "do not" in lowered
    assert "mrn" not in lowered or "do not" in lowered
    # Prompt must instruct JSON-only structured extraction.
    assert "json" in lowered
    assert "phi" in lowered or "redacted" in lowered or "identifier" in lowered


def test_user_prompt_includes_scrubbed_note_only() -> None:
    note = "Patient [REDACTED_PERSON_ab12] with hypertension on lisinopril."
    user = build_user_prompt(note)
    assert note in user
    assert "patient_id" not in user.lower()


def test_parser_fails_closed_on_invalid_llm_json() -> None:
    class _Bad:
        def complete_json(self, *, system: str, user: str) -> str:
            return "not-json{"

    agent = ParserAgent(llm=_Bad())
    with pytest.raises(ParserError):
        agent.parse(scrubbed_text="cough resolved", patient_id="p-003")


def test_parser_fails_closed_on_schema_validation() -> None:
    llm = FakeLlm({"conditions": "not-a-list"})
    agent = ParserAgent(llm=llm)
    with pytest.raises(ParserError):
        agent.parse(scrubbed_text="note", patient_id="p-001")


def test_parser_logs_are_phi_safe(caplog: pytest.LogCaptureFixture) -> None:
    llm = FakeLlm(
        {
            "conditions": ["acute bronchitis"],
            "labs": [],
            "medications": [],
            "note_summary": "Resolved cough.",
        }
    )
    agent = ParserAgent(llm=llm)
    with caplog.at_level(logging.INFO):
        agent.parse(
            scrubbed_text="Follow-up for resolved acute bronchitis.",
            patient_id="p-003",
            correlation_id="corr-p",
        )
    joined = " ".join(r.getMessage() for r in caplog.records)
    # Message itself is a status string; extras are sanitized separately.
    assert "Follow-up for resolved" not in joined
