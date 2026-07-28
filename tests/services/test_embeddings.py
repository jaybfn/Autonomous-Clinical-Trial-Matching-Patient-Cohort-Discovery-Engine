"""TDD contracts for embedding providers (deterministic / mocked)."""

from __future__ import annotations

import pytest

from trialmatch.config.settings import Settings
from trialmatch.services.embeddings import (
    DeterministicEmbedder,
    EmbeddingService,
    build_embedder,
)


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("GCP_PROJECT_ID", "autonomous-agent-503517")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "16")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "deterministic")
    monkeypatch.setenv("EMBEDDING_MODEL", "local-hash-v1")
    return Settings(_env_file=None)


def test_deterministic_embedder_fixed_dimension(settings: Settings) -> None:
    embedder = DeterministicEmbedder(dimension=settings.embedding_dimension)
    v1 = embedder.embed("Inclusion criteria: diabetes")
    v2 = embedder.embed("Inclusion criteria: diabetes")
    v3 = embedder.embed("different text")
    assert len(v1) == 16
    assert v1 == v2
    assert v1 != v3
    assert all(isinstance(x, float) for x in v1)


def test_build_embedder_selects_deterministic(settings: Settings) -> None:
    embedder = build_embedder(settings)
    assert isinstance(embedder, DeterministicEmbedder)


def test_embedding_service_batches(settings: Settings) -> None:
    service = EmbeddingService(build_embedder(settings))
    vectors = service.embed_texts(["a", "bb", "ccc"])
    assert len(vectors) == 3
    assert all(len(v) == 16 for v in vectors)


def test_vertex_provider_requires_project_and_uses_injected_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "autonomous-agent-503517")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "vertex")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "4")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-004")
    settings = Settings(_env_file=None)

    class _FakeVertex:
        def embed(self, text: str, *, model: str) -> list[float]:
            assert model == "text-embedding-004"
            return [0.25, 0.25, 0.25, 0.25]

    from trialmatch.services.embeddings import VertexEmbedder

    embedder = VertexEmbedder(settings=settings, client=_FakeVertex())
    assert embedder.embed("hello") == [0.25, 0.25, 0.25, 0.25]
