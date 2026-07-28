"""Index ClinicalTrials.gov eligibility documents into Qdrant.

Dry-run (default) uses the deterministic embedder and does not contact Qdrant.
Live mode: set --live and configure QDRANT_URL / EMBEDDING_* env vars.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Protocol

from trialmatch.config.settings import Settings
from trialmatch.data.clinicaltrials_mapper import map_eligibility_record, read_eligibility_jsonl
from trialmatch.services.embeddings import Embedder, build_embedder
from trialmatch.services.trial_indexer import TrialIndexer


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
    """Legacy script helper used by Phase 0.5 tests — upserts via injected client."""
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
    parser.add_argument("--collection", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Embed + count only (default).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Ensure collection and upsert into Qdrant (requires qdrant-client).",
    )
    args = parser.parse_args(argv)

    dry_run = not args.live
    # Dry-run works without a full .env; live mode still requires real project ADC.
    import os

    os.environ.setdefault("GCP_PROJECT_ID", "autonomous-agent-503517")

    settings = Settings(_env_file=None)
    if args.collection:
        settings = settings.model_copy(update={"qdrant_collection": args.collection})

    embedder = build_embedder(settings)

    if dry_run:

        class _NoopStore:
            def ensure_collection(self, vector_size: int) -> None:
                return None

            def upsert(self, points: list[dict]) -> int:
                return 0

        store: object = _NoopStore()
    else:
        from trialmatch.adapters.qdrant_client import QdrantVectorStore

        store = QdrantVectorStore(settings=settings)

    indexer = TrialIndexer(
        embedder=embedder,
        store=store,  # type: ignore[arg-type]
        collection=settings.qdrant_collection,
    )
    summary = indexer.index_jsonl(args.sample_path, dry_run=dry_run)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
