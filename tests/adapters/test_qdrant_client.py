"""TDD contracts for Qdrant adapter (mocked HTTP / injected client)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trialmatch.adapters.qdrant_client import QdrantVectorStore
from trialmatch.config.settings import Settings


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("GCP_PROJECT_ID", "autonomous-agent-503517")
    monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("QDRANT_COLLECTION", "trial_criteria")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "8")
    return Settings(_env_file=None)


def test_ensure_collection_creates_when_missing(settings: Settings) -> None:
    http = MagicMock()
    http.collection_exists.return_value = False
    store = QdrantVectorStore(settings=settings, http=http)
    store.ensure_collection(vector_size=8)
    http.create_collection.assert_called_once()
    args, kwargs = http.create_collection.call_args
    assert kwargs.get("collection") == "trial_criteria" or (args and args[0] == "trial_criteria")
    assert kwargs.get("vector_size") == 8 or (len(args) > 1 and args[1] == 8)


def test_upsert_and_search_roundtrip_via_http_mock(settings: Settings) -> None:
    http = MagicMock()
    http.collection_exists.return_value = True
    http.search.return_value = [
        {
            "id": "uuid-1",
            "score": 0.91,
            "payload": {"nct_id": "NCT00000001", "title": "Demo"},
        }
    ]
    store = QdrantVectorStore(settings=settings, http=http)
    n = store.upsert(
        [
            {
                "id": "NCT00000001",
                "vector": [0.1] * 8,
                "payload": {"nct_id": "NCT00000001", "title": "Demo"},
            }
        ]
    )
    assert n == 1
    http.upsert_points.assert_called_once()
    hits = store.search([0.1] * 8, limit=3)
    assert hits[0]["payload"]["nct_id"] == "NCT00000001"
    assert hits[0]["score"] == 0.91


def test_search_returns_empty_when_collection_missing(settings: Settings) -> None:
    http = MagicMock()
    http.collection_exists.return_value = False
    store = QdrantVectorStore(settings=settings, http=http)
    assert store.search([0.1] * 8, limit=3) == []
    http.search.assert_not_called()


def test_point_id_is_stable_uuid_derived_from_nct(settings: Settings) -> None:
    from trialmatch.adapters.qdrant_client import point_id_for_nct

    a = point_id_for_nct("NCT00000001")
    b = point_id_for_nct("NCT00000001")
    c = point_id_for_nct("NCT00000002")
    assert a == b
    assert a != c
