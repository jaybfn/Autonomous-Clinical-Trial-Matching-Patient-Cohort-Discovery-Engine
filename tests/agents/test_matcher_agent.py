"""TDD contracts for Matcher agent (hybrid Snowflake + Qdrant)."""

from __future__ import annotations

from typing import Any

import pytest

from trialmatch.agents.matcher.agent import MatcherAgent, MatcherError, MatchResult
from trialmatch.domain.patient import PatientFeatures
from trialmatch.services.embeddings import DeterministicEmbedder


class _FakeSnowflake:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.calls: list[tuple[str, Any]] = []

    def fetch_all(self, sql: str, params: Any = None) -> list[dict[str, Any]]:
        self.calls.append((sql, params))
        return list(self.rows)


class _FakeQdrant:
    def __init__(self, hits: list[dict[str, Any]] | None = None) -> None:
        self.hits = hits or []
        self.last_vector: list[float] | None = None
        self.last_limit: int | None = None

    def search(self, vector: list[float], limit: int = 10) -> list[dict[str, Any]]:
        self.last_vector = vector
        self.last_limit = limit
        return list(self.hits)


def test_matcher_ranks_hybrid_matches() -> None:
    snowflake = _FakeSnowflake(
        rows=[
            {
                "feature_type": "condition",
                "feature_code": "44054006",
                "feature_label": "Type 2 diabetes mellitus",
                "feature_value": None,
                "feature_units": None,
            }
        ]
    )
    qdrant = _FakeQdrant(
        hits=[
            {
                "id": "uuid-nct-a",
                "score": 0.55,
                "payload": {
                    "nct_id": "NCT00000001",
                    "title": "Diabetes Study",
                    "eligibility_text": "Inclusion: Type 2 diabetes mellitus adults",
                },
            },
            {
                "id": "uuid-nct-b",
                "score": 0.95,
                "payload": {
                    "nct_id": "NCT00000002",
                    "title": "Allergy Study",
                    "eligibility_text": "Inclusion: Seasonal allergies only",
                },
            },
        ]
    )
    agent = MatcherAgent(
        snowflake=snowflake,
        qdrant=qdrant,
        embedder=DeterministicEmbedder(dimension=8),
        schema="MARTS",
        vector_limit=5,
    )
    features = PatientFeatures(
        patient_id="p-001",
        conditions=["Type 2 diabetes mellitus"],
        labs=[{"name": "HbA1c", "value": 8.0}],
        note_summary="Patient with diabetes [REDACTED_PERSON_1]",
    )
    result = agent.match(features, correlation_id="corr-1")
    assert isinstance(result, MatchResult)
    assert result.result.patient_id == "p-001"
    assert len(result.result.matches) == 2
    # Diabetes trial should outrank allergy trial despite lower raw vector score.
    assert result.result.matches[0].nct_id == "NCT00000001"
    assert result.result.matches[0].score >= result.result.matches[1].score
    evidence = result.result.matches[0].evidence
    assert evidence["vector_neighbor_id"] == "uuid-nct-a"
    assert "Type 2 diabetes mellitus" in evidence["condition_hits"]
    assert snowflake.calls and "dim_trial_eligibility_features" in snowflake.calls[0][0].lower()
    assert snowflake.calls[0][1] == ("p-001",)
    assert qdrant.last_limit == 5
    assert qdrant.last_vector is not None


def test_matcher_rejects_blank_patient() -> None:
    agent = MatcherAgent(
        snowflake=_FakeSnowflake(),
        qdrant=_FakeQdrant(),
        embedder=DeterministicEmbedder(dimension=8),
    )
    # Bypass domain validator to assert agent fail-closed guard.
    features = PatientFeatures.model_construct(patient_id="  ", conditions=["x"])
    with pytest.raises(MatcherError, match="patient_id"):
        agent.match(features)


def test_matcher_fails_closed_on_qdrant_error() -> None:
    class _Boom:
        def search(self, vector: list[float], limit: int = 10) -> list[dict[str, Any]]:
            raise RuntimeError("qdrant down")

    agent = MatcherAgent(
        snowflake=_FakeSnowflake(),
        qdrant=_Boom(),  # type: ignore[arg-type]
        embedder=DeterministicEmbedder(dimension=8),
    )
    with pytest.raises(MatcherError, match="Qdrant"):
        agent.match(PatientFeatures(patient_id="p-1", conditions=["Asthma"]))


def test_matcher_evidence_omits_note_summary_and_phi_keys() -> None:
    qdrant = _FakeQdrant(
        hits=[
            {
                "id": "1",
                "score": 0.8,
                "payload": {"nct_id": "NCT9", "eligibility_text": "Asthma"},
            }
        ]
    )
    agent = MatcherAgent(
        snowflake=_FakeSnowflake(),
        qdrant=qdrant,
        embedder=DeterministicEmbedder(dimension=8),
    )
    result = agent.match(
        PatientFeatures(
            patient_id="p-2",
            conditions=["Asthma"],
            note_summary="Secret clinical prose",
        )
    )
    evidence = result.result.matches[0].evidence
    assert "note_summary" not in evidence
    assert "raw_note" not in evidence
    assert "ssn" not in evidence
