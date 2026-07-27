"""TDD contracts for Synthea CSV/note → domain event mapping."""

from __future__ import annotations

from pathlib import Path

import pytest

from trialmatch.data.synthea_mapper import (
    map_condition_row,
    map_lab_row,
    map_note_record,
    map_patient_row,
    read_clinical_notes_jsonl,
    read_synthea_csv,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "synthea"


def test_map_patient_row_produces_clinical_record_event_shape() -> None:
    row = {
        "Id": "p-001",
        "BIRTHDATE": "1980-05-12",
        "GENDER": "F",
        "RACE": "white",
        "ETHNICITY": "nonhispanic",
        "CITY": "Boston",
        "STATE": "Massachusetts",
    }
    event = map_patient_row(row)
    assert event["event_type"] == "clinical_record"
    assert event["source"] == "synthea"
    assert event["patient_id"] == "p-001"
    assert event["payload"]["birthdate"] == "1980-05-12"
    assert event["payload"]["gender"] == "F"
    assert "Id" not in event["payload"]


def test_map_lab_row_produces_lab_update_event_shape() -> None:
    row = {
        "PATIENT": "p-001",
        "DATE": "2024-01-15T10:00:00Z",
        "CODE": "2339-0",
        "DESCRIPTION": "Glucose",
        "VALUE": "110",
        "UNITS": "mg/dL",
    }
    event = map_lab_row(row)
    assert event["event_type"] == "lab_update"
    assert event["source"] == "synthea"
    assert event["patient_id"] == "p-001"
    assert event["payload"]["loinc_code"] == "2339-0"
    assert event["payload"]["value"] == "110"
    assert event["occurred_at"] == "2024-01-15T10:00:00Z"


def test_map_condition_row_includes_snomed_code() -> None:
    row = {
        "PATIENT": "p-001",
        "START": "2020-03-01",
        "STOP": "",
        "CODE": "44054006",
        "DESCRIPTION": "Diabetes mellitus type 2",
    }
    event = map_condition_row(row)
    assert event["event_type"] == "clinical_record"
    assert event["payload"]["condition_code"] == "44054006"
    assert event["payload"]["description"] == "Diabetes mellitus type 2"


def test_map_note_record_preserves_text_and_planted_pii_markers() -> None:
    note = {
        "note_id": "n-001",
        "patient_id": "p-001",
        "encounter_id": "e-001",
        "authored_at": "2024-02-01T12:00:00Z",
        "text": "Patient Jane Doe MRN 1234567 presents with hyperglycemia.",
    }
    event = map_note_record(note)
    assert event["event_type"] == "clinical_record"
    assert event["patient_id"] == "p-001"
    assert "Jane Doe" in event["payload"]["text"]
    assert "1234567" in event["payload"]["text"]
    assert event["payload"]["note_id"] == "n-001"


def test_read_synthea_csv_from_fixture() -> None:
    path = FIXTURES / "patients.csv"
    rows = list(read_synthea_csv(path))
    assert len(rows) >= 1
    assert "Id" in rows[0]


def test_read_clinical_notes_jsonl_from_fixture() -> None:
    path = FIXTURES / "clinical_notes.jsonl"
    notes = list(read_clinical_notes_jsonl(path))
    assert len(notes) >= 1
    assert "text" in notes[0]


def test_map_patient_row_requires_id() -> None:
    with pytest.raises(ValueError, match="Id"):
        map_patient_row({"BIRTHDATE": "1980-01-01"})
