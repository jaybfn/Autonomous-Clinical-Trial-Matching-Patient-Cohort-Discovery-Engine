"""Map Synthea CSV rows and clinical notes into Pub/Sub-oriented event dicts."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def read_synthea_csv(path: Path) -> Iterator[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield {key: (value or "") for key, value in row.items()}


def read_clinical_notes_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Expected object at {path}:{line_no}")
            yield record


def map_patient_row(row: dict[str, str]) -> dict[str, Any]:
    patient_id = (row.get("Id") or "").strip()
    if not patient_id:
        raise ValueError("Patient row missing required field: Id")
    return {
        "event_type": "clinical_record",
        "source": "synthea",
        "patient_id": patient_id,
        "payload": {
            "record_kind": "patient",
            "birthdate": row.get("BIRTHDATE", ""),
            "gender": row.get("GENDER", ""),
            "race": row.get("RACE", ""),
            "ethnicity": row.get("ETHNICITY", ""),
            "city": row.get("CITY", ""),
            "state": row.get("STATE", ""),
        },
    }


def map_lab_row(row: dict[str, str]) -> dict[str, Any]:
    patient_id = (row.get("PATIENT") or "").strip()
    if not patient_id:
        raise ValueError("Lab row missing required field: PATIENT")
    occurred_at = row.get("DATE", "")
    return {
        "event_type": "lab_update",
        "source": "synthea",
        "patient_id": patient_id,
        "occurred_at": occurred_at,
        "payload": {
            "record_kind": "lab",
            "loinc_code": row.get("CODE", ""),
            "description": row.get("DESCRIPTION", ""),
            "value": row.get("VALUE", ""),
            "units": row.get("UNITS", ""),
        },
    }


def map_condition_row(row: dict[str, str]) -> dict[str, Any]:
    patient_id = (row.get("PATIENT") or "").strip()
    if not patient_id:
        raise ValueError("Condition row missing required field: PATIENT")
    return {
        "event_type": "clinical_record",
        "source": "synthea",
        "patient_id": patient_id,
        "occurred_at": row.get("START", ""),
        "payload": {
            "record_kind": "condition",
            "condition_code": row.get("CODE", ""),
            "description": row.get("DESCRIPTION", ""),
            "start": row.get("START", ""),
            "stop": row.get("STOP", ""),
        },
    }


def map_note_record(note: dict[str, Any]) -> dict[str, Any]:
    patient_id = str(note.get("patient_id") or "").strip()
    if not patient_id:
        raise ValueError("Note record missing required field: patient_id")
    text = str(note.get("text") or "")
    return {
        "event_type": "clinical_record",
        "source": "synthea",
        "patient_id": patient_id,
        "occurred_at": str(note.get("authored_at") or ""),
        "payload": {
            "record_kind": "clinical_note",
            "note_id": str(note.get("note_id") or ""),
            "encounter_id": str(note.get("encounter_id") or ""),
            "text": text,
        },
    }
