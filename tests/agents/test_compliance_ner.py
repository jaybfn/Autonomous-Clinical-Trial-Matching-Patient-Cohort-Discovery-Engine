"""Unit tests for pluggable Compliance NER."""

from __future__ import annotations

from trialmatch.agents.compliance.ner import NullNer, RuleBasedPersonNer


def test_rule_based_ner_finds_patient_names() -> None:
    ner = RuleBasedPersonNer()
    spans = ner.find_entities("Patient Jane Doe presents with hyperglycemia.")
    assert any(s.entity_type == "person" for s in spans)
    assert any("Jane" in s.text or "Doe" in s.text for s in spans)


def test_null_ner_returns_empty() -> None:
    assert NullNer().find_entities("Jane Doe MRN 1") == []
