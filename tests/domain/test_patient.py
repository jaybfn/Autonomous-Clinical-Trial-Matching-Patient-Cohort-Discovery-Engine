"""TDD contracts for patient feature domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from trialmatch.domain.patient import PatientDemographics, PatientFeatures


def test_patient_demographics_minimal() -> None:
    demo = PatientDemographics(patient_id="p-001", birthdate="1980-05-12", gender="F")
    assert demo.patient_id == "p-001"
    assert demo.gender == "F"


def test_patient_features_holds_conditions_and_labs() -> None:
    features = PatientFeatures(
        patient_id="p-001",
        demographics=PatientDemographics(patient_id="p-001", gender="F"),
        conditions=["Diabetes mellitus type 2"],
        labs=[{"loinc_code": "4548-4", "value": "7.8", "units": "%"}],
        note_summary="Hyperglycemia on metformin",
    )
    assert len(features.conditions) == 1
    assert features.labs[0]["loinc_code"] == "4548-4"


def test_patient_features_rejects_blank_patient_id() -> None:
    with pytest.raises(ValidationError):
        PatientFeatures(patient_id="   ", conditions=[], labs=[])
