"""Unit tests for Compliance PHI regex patterns."""

from __future__ import annotations

from trialmatch.agents.compliance.patterns import find_phi_spans


def test_patterns_detect_email_phone_ssn_mrn() -> None:
    text = "MRN 1234567 call 617-555-0100 email jane.doe@example.com SSN 078-05-1120"
    spans = find_phi_spans(text)
    types = {s.entity_type for s in spans}
    assert "email" in types
    assert "phone" in types
    assert "ssn" in types
    assert "mrn" in types


def test_patterns_detect_dob_like_dates() -> None:
    spans = find_phi_spans("Patient DOB 05/12/1980 admitted yesterday.")
    assert any(s.entity_type == "dob" for s in spans)


def test_patterns_ignore_clinical_lab_numbers() -> None:
    # A1c 7.8 should not be classified as SSN/MRN/phone
    spans = find_phi_spans("A1c 7.8% and glucose 110 mg/dL.")
    assert all(s.entity_type not in {"ssn", "phone", "mrn"} for s in spans)
