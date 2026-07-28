"""TDD contracts for ClinicalTrials.gov → Qdrant indexer service."""

from __future__ import annotations

from pathlib import Path

from trialmatch.services.embeddings import DeterministicEmbedder
from trialmatch.services.trial_indexer import TrialIndexer

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "clinicaltrials"


class FakeStore:
    def __init__(self) -> None:
        self.points: list[dict] = []
        self.ensured_size: int | None = None

    def ensure_collection(self, vector_size: int) -> None:
        self.ensured_size = vector_size

    def upsert(self, points: list[dict]) -> int:
        self.points.extend(points)
        return len(points)


def test_trial_indexer_indexes_fixture_jsonl() -> None:
    store = FakeStore()
    indexer = TrialIndexer(
        embedder=DeterministicEmbedder(dimension=8),
        store=store,
        collection="trial_criteria",
    )
    summary = indexer.index_jsonl(FIXTURES / "eligibility.jsonl")
    assert summary["indexed"] >= 1
    assert store.ensured_size == 8
    assert len(store.points) == summary["indexed"]
    point = store.points[0]
    assert point["payload"]["nct_id"].startswith("NCT")
    assert "eligibility_text" in point["payload"]
    assert len(point["vector"]) == 8


def test_trial_indexer_dry_run_skips_upsert() -> None:
    store = FakeStore()
    indexer = TrialIndexer(
        embedder=DeterministicEmbedder(dimension=8),
        store=store,
        collection="trial_criteria",
    )
    summary = indexer.index_jsonl(FIXTURES / "eligibility.jsonl", dry_run=True)
    assert summary["indexed"] >= 1
    assert store.points == []
    assert store.ensured_size is None
