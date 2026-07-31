"""TDD contracts for Auditor justification report formatting."""

from __future__ import annotations

from trialmatch.agents.auditor.report import (
    build_justification_summary,
    build_per_match_justification,
    normalize_redaction_tokens,
)
from trialmatch.domain.trial import TrialMatch, TrialMatchResult


def test_per_match_justification_includes_score_and_hits() -> None:
    text = build_per_match_justification(
        TrialMatch(
            nct_id="NCT01234567",
            score=0.91,
            evidence={
                "vector_score": 0.8,
                "condition_hits": ["Type 2 diabetes mellitus"],
                "condition_misses": ["Asthma"],
                "lab_hits": ["HbA1c"],
                "lab_misses": [],
                "title": "Diabetes Study",
            },
        )
    )
    assert "NCT01234567" in text
    assert "0.91" in text
    assert "Type 2 diabetes mellitus" in text
    assert "HbA1c" in text
    assert "ssn" not in text.lower()


def test_summary_ranks_matches_and_handles_empty() -> None:
    empty = build_justification_summary(
        TrialMatchResult(patient_id="p-1", matches=[]),
    )
    assert "No trials matched" in empty

    summary = build_justification_summary(
        TrialMatchResult(
            patient_id="p-1",
            matches=[
                TrialMatch(
                    nct_id="NCT1",
                    score=0.9,
                    evidence={"condition_hits": ["Hypertension"], "lab_hits": []},
                ),
                TrialMatch(
                    nct_id="NCT2",
                    score=0.4,
                    evidence={"condition_hits": [], "lab_hits": []},
                ),
            ],
        ),
        max_matches=1,
    )
    assert "NCT1" in summary
    assert "NCT2" not in summary
    assert "Hypertension" in summary


def test_normalize_redaction_tokens_keeps_token_to_type_map() -> None:
    tokens = normalize_redaction_tokens(
        {"[REDACTED_EMAIL_abcd1234]": "email", "[REDACTED_PERSON_deadbeef]": "person"}
    )
    assert tokens["[REDACTED_EMAIL_abcd1234]"] == "email"
    assert "person" in tokens.values()
    # Values must not look like raw emails / SSNs
    for value in tokens.values():
        assert "@" not in value
        assert not any(ch.isdigit() for ch in value) or value.isalpha()
