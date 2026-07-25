"""TDD contracts for indexing ClinicalTrials.gov docs into Qdrant (mocked)."""

from __future__ import annotations

from pathlib import Path

from scripts.index_trials_to_qdrant import index_trials_to_qdrant

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "clinicaltrials"


class FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        # Deterministic tiny vector from length for tests
        return [float(len(text) % 7), 1.0, 0.0]


class FakeQdrant:
    def __init__(self) -> None:
        self.points: list[dict] = []

    def upsert(self, collection: str, points: list[dict]) -> int:
        assert collection
        self.points.extend(points)
        return len(points)


def test_index_trials_upserts_embedded_points() -> None:
    qdrant = FakeQdrant()
    summary = index_trials_to_qdrant(
        sample_path=FIXTURES / "eligibility.jsonl",
        embedder=FakeEmbedder(),
        qdrant=qdrant,
        collection="trial_criteria",
    )
    assert summary["indexed"] >= 1
    assert len(qdrant.points) == summary["indexed"]
    point = qdrant.points[0]
    assert point["id"].startswith("NCT")
    assert isinstance(point["vector"], list)
    assert point["payload"]["nct_id"].startswith("NCT")
    assert "eligibility_text" in point["payload"]


def test_index_trials_dry_run_skips_upsert() -> None:
    qdrant = FakeQdrant()
    summary = index_trials_to_qdrant(
        sample_path=FIXTURES / "eligibility.jsonl",
        embedder=FakeEmbedder(),
        qdrant=qdrant,
        dry_run=True,
    )
    assert summary["indexed"] >= 1
    assert qdrant.points == []
