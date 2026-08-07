"""Qdrant vector store adapter — injectable HTTP layer for unit tests.

Live use may install ``qdrant-client`` (optional extra ``[qdrant]``).
Point IDs are UUID5 derived from NCT IDs (Qdrant does not accept raw NCT strings).
"""

from __future__ import annotations

import uuid
from typing import Any, Protocol
from uuid import UUID

from trialmatch.config.settings import Settings

_NCT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # URL namespace


def point_id_for_nct(nct_id: str) -> str:
    """Stable UUID string for a ClinicalTrials.gov NCT identifier."""
    return str(uuid.uuid5(_NCT_NAMESPACE, nct_id.strip().upper()))


class QdrantHttp(Protocol):
    def collection_exists(self, collection: str) -> bool: ...

    def create_collection(self, collection: str, vector_size: int) -> None: ...

    def upsert_points(self, collection: str, points: list[dict[str, Any]]) -> int: ...

    def search(self, collection: str, vector: list[float], limit: int) -> list[dict[str, Any]]: ...


class _SdkHttp:
    """Thin wrapper around the official qdrant-client SDK."""

    def __init__(self, url: str) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models as rest
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "qdrant-client is required for live Qdrant access. "
                "Install with: pip install 'trialmatch[qdrant]'"
            ) from exc
        self._client = QdrantClient(url=url)
        self._rest = rest

    def collection_exists(self, collection: str) -> bool:
        names = {c.name for c in self._client.get_collections().collections}
        return collection in names

    def create_collection(self, collection: str, vector_size: int) -> None:
        self._client.create_collection(
            collection_name=collection,
            vectors_config=self._rest.VectorParams(
                size=vector_size, distance=self._rest.Distance.COSINE
            ),
        )

    def upsert_points(self, collection: str, points: list[dict[str, Any]]) -> int:
        payload = [
            self._rest.PointStruct(
                id=UUID(p["id"]) if _looks_like_uuid(p["id"]) else p["id"],
                vector=p["vector"],
                payload=p.get("payload") or {},
            )
            for p in points
        ]
        self._client.upsert(collection_name=collection, points=payload)
        return len(payload)

    def search(self, collection: str, vector: list[float], limit: int) -> list[dict[str, Any]]:
        # qdrant-client >=1.16 uses query_points; older SDKs expose search().
        if hasattr(self._client, "query_points"):
            result = self._client.query_points(
                collection_name=collection, query=vector, limit=limit
            )
            hits = getattr(result, "points", result)
        else:
            hits = self._client.search(collection_name=collection, query_vector=vector, limit=limit)
        return [
            {"id": str(h.id), "score": float(h.score), "payload": dict(h.payload or {})}
            for h in hits
        ]


def _looks_like_uuid(value: Any) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


class QdrantVectorStore:
    def __init__(
        self,
        *,
        settings: Settings,
        http: QdrantHttp | None = None,
    ) -> None:
        self.settings = settings
        self.collection = settings.qdrant_collection
        self._http = http or _SdkHttp(settings.qdrant_url)

    def ensure_collection(self, vector_size: int) -> None:
        if not self._http.collection_exists(self.collection):
            self._http.create_collection(self.collection, vector_size)

    def upsert(self, points: list[dict[str, Any]], *, batch_size: int = 50) -> int:
        """Upsert points in batches to stay under Qdrant's request body limit (~32MB)."""
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        prepared: list[dict[str, Any]] = []
        for point in points:
            raw_id = str(point["id"])
            point_id = raw_id if _looks_like_uuid(raw_id) else point_id_for_nct(raw_id)
            payload = dict(point.get("payload") or {})
            if "nct_id" not in payload:
                payload["nct_id"] = raw_id
            prepared.append({"id": point_id, "vector": point["vector"], "payload": payload})

        total = 0
        for start in range(0, len(prepared), batch_size):
            chunk = prepared[start : start + batch_size]
            total += self._http.upsert_points(self.collection, chunk)
        return total

    def search(self, vector: list[float], limit: int = 10) -> list[dict[str, Any]]:
        if not self._http.collection_exists(self.collection):
            return []
        return self._http.search(self.collection, vector, limit)
