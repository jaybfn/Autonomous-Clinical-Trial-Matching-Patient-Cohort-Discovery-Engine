"""TDD contracts for hybrid Matcher scoring."""

from __future__ import annotations

from trialmatch.agents.matcher.scoring import HybridWeights, hybrid_score, normalize_vector_score


def test_normalize_vector_score_clamps() -> None:
    assert normalize_vector_score(1.2) == 1.0
    assert normalize_vector_score(-0.5) == 0.0
    assert normalize_vector_score(0.75) == 0.75


def test_hybrid_score_prefers_condition_hits_in_eligibility() -> None:
    score_hit, evidence_hit = hybrid_score(
        vector_score=0.5,
        vector_neighbor_id="vec-1",
        patient_conditions=["Type 2 diabetes mellitus"],
        patient_labs=["HbA1c"],
        eligibility_text="Inclusion: Adults with Type 2 diabetes mellitus. Labs may include HbA1c.",
    )
    score_miss, evidence_miss = hybrid_score(
        vector_score=0.5,
        vector_neighbor_id="vec-2",
        patient_conditions=["Type 2 diabetes mellitus"],
        patient_labs=["HbA1c"],
        eligibility_text="Inclusion: Healthy volunteers only.",
    )
    assert score_hit > score_miss
    assert "Type 2 diabetes mellitus" in evidence_hit["condition_hits"]
    assert "Type 2 diabetes mellitus" in evidence_miss["condition_misses"]
    assert 0.0 <= score_hit <= 1.0


def test_hybrid_score_uses_custom_weights() -> None:
    weights = HybridWeights(vector=1.0, condition=0.0, lab=0.0)
    score, evidence = hybrid_score(
        vector_score=0.42,
        vector_neighbor_id="n1",
        patient_conditions=["ignored"],
        patient_labs=["ignored"],
        eligibility_text="nothing matches",
        weights=weights,
    )
    assert score == 0.42
    assert evidence["weights"]["vector"] == 1.0


def test_hybrid_evidence_has_no_phi_keys() -> None:
    _, evidence = hybrid_score(
        vector_score=0.9,
        vector_neighbor_id="abc",
        patient_conditions=["Hypertension"],
        patient_labs=["Creatinine"],
        eligibility_text="Hypertension allowed",
    )
    forbidden = {"ssn", "mrn", "email", "phone", "address", "dob", "birthdate", "name", "raw_note"}
    assert forbidden.isdisjoint({k.lower() for k in evidence})
