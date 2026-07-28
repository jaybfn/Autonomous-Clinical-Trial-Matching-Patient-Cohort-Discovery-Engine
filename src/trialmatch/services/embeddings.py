"""Text embedding providers — deterministic for tests, Vertex via ADC for prod."""

from __future__ import annotations

import hashlib
import math
import struct
from typing import Protocol

from trialmatch.config.settings import Settings


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class DeterministicEmbedder:
    """Local hash-based embedder for tests / offline dry-runs (no network)."""

    def __init__(self, dimension: int = 768) -> None:
        if dimension < 1:
            raise ValueError("dimension must be >= 1")
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        seed = digest
        while len(values) < self.dimension:
            seed = hashlib.sha256(seed).digest()
            for i in range(0, len(seed), 4):
                if len(values) >= self.dimension:
                    break
                (n,) = struct.unpack_from("!I", seed, i)
                # Map to [-1, 1]
                values.append((n / 0xFFFFFFFF) * 2.0 - 1.0)
        # L2-normalize for cosine-friendly space
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]


class VertexEmbedder:
    """Vertex AI text embeddings via an injectable client (ADC in production)."""

    def __init__(self, *, settings: Settings, client: object | None = None) -> None:
        self.settings = settings
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self._client = client

    def embed(self, text: str) -> list[float]:
        client = self._client or _default_vertex_client(self.settings)
        vector = client.embed(text, model=self.model)  # type: ignore[attr-defined]
        if len(vector) != self.dimension:
            raise ValueError(f"Vertex returned dim={len(vector)}, expected {self.dimension}")
        return list(vector)


class EmbeddingService:
    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embedder.embed(t) for t in texts]


def build_embedder(settings: Settings) -> Embedder:
    provider = (settings.embedding_provider or "deterministic").lower()
    if provider in {"deterministic", "local", "hash"}:
        return DeterministicEmbedder(dimension=settings.embedding_dimension)
    if provider in {"vertex", "vertex_ai"}:
        return VertexEmbedder(settings=settings)
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider}")


def _default_vertex_client(settings: Settings) -> object:
    """Lazy Vertex AI client — requires google-cloud-aiplatform at runtime."""
    try:
        import vertexai  # type: ignore
        from vertexai.language_models import TextEmbeddingModel  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "google-cloud-aiplatform is required for Vertex embeddings. "
            "Install with: pip install 'trialmatch[vertex]'"
        ) from exc

    vertexai.init(project=settings.gcp_project_id)

    class _Client:
        def __init__(self) -> None:
            self._model = TextEmbeddingModel.from_pretrained(settings.embedding_model)

        def embed(self, text: str, *, model: str) -> list[float]:
            _ = model
            embeddings = self._model.get_embeddings([text])
            return list(embeddings[0].values)

    return _Client()
