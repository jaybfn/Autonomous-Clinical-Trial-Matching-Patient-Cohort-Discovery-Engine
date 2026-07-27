"""Index ClinicalTrials.gov eligibility documents into Qdrant (clients injected)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Protocol

from trialmatch.data.clinicaltrials_mapper import map_eligibility_record, read_eligibility_jsonl


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class QdrantClient(Protocol):
    def upsert(self, collection: str, points: list[dict]) -> int: ...


def index_trials_to_qdrant(
    *,
    sample_path: Path,
    embedder: Embedder,
    qdrant: QdrantClient,
    collection: str = "trial_criteria",
    dry_run: bool = False,
) -> dict[str, int]:
    points: list[dict] = []
    for record in read_eligibility_jsonl(sample_path):
        doc = map_eligibility_record(record)
        vector = embedder.embed(doc["eligibility_text"])
        points.append(
            {
                "id": doc["nct_id"],
                "vector": vector,
                "payload": {
                    "nct_id": doc["nct_id"],
                    "title": doc["title"],
                    "status": doc["status"],
                    "eligibility_text": doc["eligibility_text"],
                    "source": doc["source"],
                },
            }
        )

    if not dry_run and points:
        qdrant.upsert(collection, points)
    return {"indexed": len(points)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample-path",
        type=Path,
        default=Path("data/clinicaltrials/samples/eligibility.jsonl"),
    )
    parser.add_argument("--collection", default="trial_criteria")
    parser.add_argument("--dry-run", action="store_true", default=True)
    args = parser.parse_args(argv)

    class _HashEmbedder:
        def embed(self, text: str) -> list[float]:
            return [float(len(text) % 7), 1.0, 0.0]

    class _NoopQdrant:
        def upsert(self, collection: str, points: list[dict]) -> int:
            raise RuntimeError("Live Qdrant upsert requires Phase 6 client")

    summary = index_trials_to_qdrant(
        sample_path=args.sample_path,
        embedder=_HashEmbedder(),
        qdrant=_NoopQdrant(),
        collection=args.collection,
        dry_run=True,
    )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
