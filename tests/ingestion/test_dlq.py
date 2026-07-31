"""TDD contracts for poison-message DLQ publisher."""

from __future__ import annotations

import json
from typing import Any

import pytest

from trialmatch.ingestion.dlq import DeadLetterError, DeadLetterPublisher, is_poison_error


class _FakePublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def publish(self, topic: str, message: dict[str, Any]) -> str:
        self.calls.append((topic, message))
        return "dlq-msg-1"


def test_dead_letter_publishes_envelope_without_raw_note_body() -> None:
    pub = _FakePublisher()
    dlq = DeadLetterPublisher(publisher=pub, topic="clinical-records-dlq")
    message_id = dlq.publish_poison(
        original_data=b'{"patient_id":"p-1","payload":{"text":"SECRET NOTE"}}',
        reason="invalid_schema",
        correlation_id="corr-1",
        subscription="clinical-records-sub",
        attributes={"delivery_attempt": "3"},
    )
    assert message_id == "dlq-msg-1"
    assert len(pub.calls) == 1
    topic, payload = pub.calls[0]
    assert topic == "clinical-records-dlq"
    assert payload["reason"] == "invalid_schema"
    assert payload["correlation_id"] == "corr-1"
    assert payload["subscription"] == "clinical-records-sub"
    assert "SECRET NOTE" not in json.dumps(payload)
    assert "text" not in payload.get("payload_keys", [])
    assert payload["original_byte_length"] > 0


def test_dead_letter_requires_topic() -> None:
    with pytest.raises(DeadLetterError, match="topic"):
        DeadLetterPublisher(publisher=_FakePublisher(), topic="  ")


def test_poison_error_classification() -> None:
    assert is_poison_error(ValueError("bad json"))
    assert is_poison_error(KeyError("missing"))
    assert not is_poison_error(TimeoutError("snowflake timeout"))
    assert not is_poison_error(RuntimeError("qdrant down"))
