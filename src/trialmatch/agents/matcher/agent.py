"""Matcher agent — hybrid Qdrant retrieval + Snowflake structured features."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from trialmatch.agents.matcher.queries import (
    build_patient_features_sql,
    merge_patient_signals,
    rows_to_condition_labels,
    rows_to_lab_labels,
)
from trialmatch.agents.matcher.scoring import HybridWeights, hybrid_score
from trialmatch.domain.patient import PatientFeatures
from trialmatch.domain.trial import TrialMatch, TrialMatchResult
from trialmatch.observability.logging import get_logger, sanitize_log_extra
from trialmatch.services.embeddings import Embedder

logger = get_logger(__name__)

AGENT_NAME = "matcher"
AGENT_VERSION = "0.1.0"


class MatcherError(RuntimeError):
    """Fail-closed error when hybrid matching cannot complete safely."""


class SnowflakeReader(Protocol):
    def fetch_all(self, sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]: ...


class VectorSearcher(Protocol):
    def search(self, vector: list[float], limit: int = 10) -> list[dict[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class MatchResult:
    result: TrialMatchResult
    agent_version: str = AGENT_VERSION


def build_patient_query_text(features: PatientFeatures) -> str:
    """Embeddable text from structured features (no demographics / identifiers)."""
    parts: list[str] = []
    if features.conditions:
        parts.append("Conditions: " + ", ".join(features.conditions))
    for lab in features.labs:
        if not isinstance(lab, dict):
            continue
        name = str(lab.get("name") or lab.get("code") or "lab").strip()
        value = lab.get("value")
        units = str(lab.get("units") or "").strip()
        if value is None:
            parts.append(f"Lab {name}".strip())
        else:
            parts.append(f"Lab {name}: {value} {units}".strip())
    if features.note_summary and features.note_summary.strip():
        parts.append(features.note_summary.strip())
    return "\n".join(parts).strip() or "clinical features unavailable"


class MatcherAgent:
    """Coordinates vector retrieval, mart reads, and hybrid ranking."""

    def __init__(
        self,
        *,
        snowflake: SnowflakeReader,
        qdrant: VectorSearcher,
        embedder: Embedder,
        schema: str = "MARTS",
        vector_limit: int = 10,
        weights: HybridWeights | None = None,
    ) -> None:
        self._snowflake = snowflake
        self._qdrant = qdrant
        self._embedder = embedder
        self._schema = schema
        self._vector_limit = vector_limit
        self._weights = weights

    def match(
        self,
        features: PatientFeatures,
        *,
        correlation_id: str | None = None,
    ) -> MatchResult:
        patient_id = (features.patient_id or "").strip()
        if not patient_id:
            raise MatcherError("patient_id must not be blank")

        try:
            rows = self._snowflake.fetch_all(
                build_patient_features_sql(schema=self._schema),
                (patient_id,),
            )
        except Exception as exc:  # noqa: BLE001 — fail closed
            raise MatcherError(f"Snowflake read failed: {exc}") from exc

        conditions, labs = merge_patient_signals(
            parser_conditions=list(features.conditions),
            parser_labs=list(features.labs),
            snowflake_conditions=rows_to_condition_labels(rows),
            snowflake_labs=rows_to_lab_labels(rows),
        )

        query_text = build_patient_query_text(features)
        try:
            vector = self._embedder.embed(query_text)
        except Exception as exc:  # noqa: BLE001
            raise MatcherError(f"Embedding failed: {exc}") from exc

        try:
            hits = self._qdrant.search(vector, limit=self._vector_limit)
        except Exception as exc:  # noqa: BLE001
            raise MatcherError(f"Qdrant search failed: {exc}") from exc

        matches: list[TrialMatch] = []
        for hit in hits:
            payload = hit.get("payload") if isinstance(hit.get("payload"), dict) else {}
            nct_id = str(payload.get("nct_id") or "").strip()
            if not nct_id:
                continue
            eligibility = str(payload.get("eligibility_text") or "")
            neighbor_id = str(hit.get("id") or "")
            score, evidence = hybrid_score(
                vector_score=float(hit.get("score") or 0.0),
                vector_neighbor_id=neighbor_id,
                patient_conditions=conditions,
                patient_labs=labs,
                eligibility_text=eligibility,
                weights=self._weights,
            )
            if payload.get("title"):
                evidence = {**evidence, "title": str(payload["title"])}
            matches.append(TrialMatch(nct_id=nct_id, score=score, evidence=evidence))

        matches.sort(key=lambda m: m.score, reverse=True)
        result = TrialMatchResult(patient_id=patient_id, matches=matches)
        logger.info(
            "matcher.match.completed",
            extra=sanitize_log_extra(
                {
                    "agent_name": AGENT_NAME,
                    "correlation_id": correlation_id or "",
                    "patient_id": patient_id,
                    "match_count": len(matches),
                    "vector_limit": self._vector_limit,
                    "status": "ok",
                }
            ),
        )
        return MatchResult(result=result)
