"""Index ClinicalTrials.gov eligibility documents into Qdrant."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from trialmatch.data.clinicaltrials_mapper import map_eligibility_record, read_eligibility_jsonl
from trialmatch.services.embeddings import Embedder


class VectorStore(Protocol):
    def ensure_collection(self, vector_size: int) -> None: ...

    def upsert(self, points: list[dict]) -> int: ...


class TrialIndexer:
    def __init__(
        self,
        *,
        embedder: Embedder,
        store: VectorStore,
        collection: str = "trial_criteria",
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.collection = collection

    def index_jsonl(self, sample_path: Path, *, dry_run: bool = False) -> dict[str, int]:
        points: list[dict] = []
        vector_size: int | None = None
        for record in read_eligibility_jsonl(sample_path):
            doc = map_eligibility_record(record)
            vector = self.embedder.embed(doc["eligibility_text"])
            vector_size = len(vector)
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
                        "collection": self.collection,
                    },
                }
            )

        if not dry_run and points and vector_size is not None:
            self.store.ensure_collection(vector_size)
            self.store.upsert(points)
        return {"indexed": len(points)}
