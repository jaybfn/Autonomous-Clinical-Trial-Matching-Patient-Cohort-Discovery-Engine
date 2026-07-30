"""Hybrid scoring: vector similarity + structured feature overlap."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HybridWeights:
    vector: float = 0.6
    condition: float = 0.3
    lab: float = 0.1

    def normalized(self) -> HybridWeights:
        total = self.vector + self.condition + self.lab
        if total <= 0:
            raise ValueError("weights must sum to a positive value")
        return HybridWeights(
            vector=self.vector / total,
            condition=self.condition / total,
            lab=self.lab / total,
        )


DEFAULT_WEIGHTS = HybridWeights()


def normalize_vector_score(score: float) -> float:
    """Clamp cosine / similarity scores into [0, 1] for TrialMatch.score."""
    return max(0.0, min(1.0, float(score)))


def _label_overlap(
    patient_labels: list[str],
    eligibility_text: str,
) -> tuple[float, list[str], list[str]]:
    text = (eligibility_text or "").lower()
    hits: list[str] = []
    misses: list[str] = []
    for raw in patient_labels:
        label = (raw or "").strip()
        if not label:
            continue
        if label.lower() in text:
            hits.append(label)
        else:
            misses.append(label)
    total = len(hits) + len(misses)
    rate = (len(hits) / total) if total else 0.0
    return rate, hits, misses


def hybrid_score(
    *,
    vector_score: float,
    vector_neighbor_id: str,
    patient_conditions: list[str],
    patient_labs: list[str],
    eligibility_text: str,
    weights: HybridWeights | None = None,
) -> tuple[float, dict[str, Any]]:
    """Return (score in [0,1], evidence dict without PHI keys)."""
    w = (weights or DEFAULT_WEIGHTS).normalized()
    vector = normalize_vector_score(vector_score)
    condition_rate, condition_hits, condition_misses = _label_overlap(
        patient_conditions, eligibility_text
    )
    lab_rate, lab_hits, lab_misses = _label_overlap(patient_labs, eligibility_text)
    score = normalize_vector_score(
        w.vector * vector + w.condition * condition_rate + w.lab * lab_rate
    )
    evidence: dict[str, Any] = {
        "vector_score": vector,
        "vector_neighbor_id": vector_neighbor_id,
        "condition_hits": condition_hits,
        "condition_misses": condition_misses,
        "lab_hits": lab_hits,
        "lab_misses": lab_misses,
        "weights": {
            "vector": w.vector,
            "condition": w.condition,
            "lab": w.lab,
        },
    }
    return score, evidence
