"""TDD contracts for clinical / lab Pub/Sub event domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from trialmatch.data.synthea_mapper import map_lab_row, map_note_record, map_patient_row
from trialmatch.domain.events import ClinicalEvent, EventSource, EventType


def test_clinical_record_event_requires_patient_and_type() -> None:
    event = ClinicalEvent(
        event_type=EventType.CLINICAL_RECORD,
        source=EventSource.SYNTHEA,
        patient_id="p-001",
        payload={"record_kind": "patient", "gender": "F"},
    )
    assert event.event_type == EventType.CLINICAL_RECORD
    assert event.patient_id == "p-001"
    assert event.source == EventSource.SYNTHEA


def test_lab_update_event_includes_occurred_at() -> None:
    event = ClinicalEvent(
        event_type=EventType.LAB_UPDATE,
        source=EventSource.SYNTHEA,
        patient_id="p-001",
        occurred_at="2024-01-15T10:00:00Z",
        payload={"loinc_code": "2339-0", "value": "110"},
    )
    assert event.occurred_at == "2024-01-15T10:00:00Z"


def test_clinical_event_rejects_empty_patient_id() -> None:
    with pytest.raises(ValidationError):
        ClinicalEvent(
            event_type=EventType.CLINICAL_RECORD,
            source=EventSource.SYNTHEA,
            patient_id="",
            payload={},
        )


def test_clinical_event_rejects_unknown_event_type() -> None:
    with pytest.raises(ValidationError):
        ClinicalEvent.model_validate(
            {
                "event_type": "unknown",
                "source": "synthea",
                "patient_id": "p-001",
                "payload": {},
            }
        )


def test_synthea_mapper_output_validates_as_clinical_event() -> None:
    patient_event = ClinicalEvent.model_validate(map_patient_row({"Id": "p-001", "GENDER": "F"}))
    assert patient_event.event_type == EventType.CLINICAL_RECORD

    lab_event = ClinicalEvent.model_validate(
        map_lab_row(
            {
                "PATIENT": "p-001",
                "DATE": "2024-01-15T10:00:00Z",
                "CODE": "2339-0",
                "DESCRIPTION": "Glucose",
                "VALUE": "110",
                "UNITS": "mg/dL",
            }
        )
    )
    assert lab_event.event_type == EventType.LAB_UPDATE

    note_event = ClinicalEvent.model_validate(
        map_note_record(
            {
                "note_id": "n-1",
                "patient_id": "p-001",
                "text": "note",
                "authored_at": "2024-02-01T12:00:00Z",
            }
        )
    )
    assert note_event.payload["record_kind"] == "clinical_note"
