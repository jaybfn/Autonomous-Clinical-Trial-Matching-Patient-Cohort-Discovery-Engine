"""TDD contracts for publishing Synthea events to Pub/Sub (mocked publisher)."""

from __future__ import annotations

from pathlib import Path

from scripts.publish_synthea_events import publish_synthea_events

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "synthea"


class FakePublisher:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict]] = []

    def publish(self, topic: str, message: dict) -> str:
        self.messages.append((topic, message))
        return f"msg-{len(self.messages)}"


def test_publish_emits_note_and_lab_events() -> None:
    publisher = FakePublisher()
    summary = publish_synthea_events(
        sample_dir=FIXTURES,
        publisher=publisher,
        clinical_topic="clinical-records",
        lab_topic="lab-updates",
    )
    assert summary["clinical_records"] >= 1
    assert summary["lab_updates"] >= 1
    topics = {t for t, _ in publisher.messages}
    assert "clinical-records" in topics
    assert "lab-updates" in topics
    for topic, message in publisher.messages:
        assert "event_type" in message
        assert message["source"] == "synthea"
        if topic == "lab-updates":
            assert message["event_type"] == "lab_update"


def test_publish_dry_run_does_not_call_publisher() -> None:
    publisher = FakePublisher()
    summary = publish_synthea_events(
        sample_dir=FIXTURES,
        publisher=publisher,
        dry_run=True,
    )
    assert summary["clinical_records"] >= 1
    assert publisher.messages == []
