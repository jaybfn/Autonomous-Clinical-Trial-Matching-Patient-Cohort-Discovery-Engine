"""Schema edge cases for Parser extracted features."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from trialmatch.agents.parser.schemas import ExtractedLab, ParsedClinicalFeatures


def test_parsed_features_accept_missing_labs_and_empty_conditions() -> None:
    features = ParsedClinicalFeatures(
        patient_id="p-001",
        conditions=[],
        labs=[],
        medications=["metformin"],
        note_summary="Follow-up for hyperglycemia.",
    )
    assert features.labs == []
    assert features.conditions == []
    assert features.medications == ["metformin"]


def test_extracted_lab_allows_optional_units() -> None:
    lab = ExtractedLab(name="Glucose", value=110.0, units=None, code="2339-0")
    assert lab.units is None
    assert lab.value == 110.0


def test_parsed_features_require_patient_id() -> None:
    with pytest.raises(ValidationError):
        ParsedClinicalFeatures(patient_id="  ", conditions=["diabetes"])


def test_to_patient_features_maps_domain_model() -> None:
    parsed = ParsedClinicalFeatures(
        patient_id="p-001",
        conditions=["type 2 diabetes mellitus"],
        labs=[ExtractedLab(name="HbA1c", value=7.8, units="%", code="4548-4")],
        medications=["metformin"],
        note_summary="A1c elevated; continue metformin.",
    )
    domain = parsed.to_patient_features()
    assert domain.patient_id == "p-001"
    assert "type 2 diabetes mellitus" in domain.conditions
    assert domain.labs[0]["name"] == "HbA1c"
    assert domain.note_summary is not None
