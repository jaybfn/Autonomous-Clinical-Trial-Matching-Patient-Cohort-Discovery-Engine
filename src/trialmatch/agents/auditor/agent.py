"""Auditor agent — PII-free justifications + append-only audit persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from trialmatch.agents.auditor.report import (
    build_justification_summary,
    normalize_redaction_tokens,
)
from trialmatch.domain.audit import AuditRecord
from trialmatch.domain.trial import TrialMatchResult
from trialmatch.observability.logging import get_logger, sanitize_log_extra

logger = get_logger(__name__)

AGENT_NAME = "auditor"
AGENT_VERSION = "0.1.0"


class AuditorError(RuntimeError):
    """Fail-closed error when audit recording cannot complete safely."""


class AuditSinkPort(Protocol):
    def append(self, record: AuditRecord) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class AuditResult:
    record: AuditRecord
    written_match_ids: list[str]
    agent_version: str = AGENT_VERSION


class AuditorAgent:
    """Builds an immutable AuditRecord from Matcher output and persists it."""

    def __init__(self, *, sink: AuditSinkPort) -> None:
        self._sink = sink

    def audit(
        self,
        *,
        match_result: TrialMatchResult,
        content_hash: str,
        redaction_tokens: dict[str, str],
        correlation_id: str,
        agent_versions: dict[str, str] | None = None,
    ) -> AuditResult:
        corr = (correlation_id or "").strip()
        if not corr:
            raise AuditorError("correlation_id must not be blank")
        digest = (content_hash or "").strip()
        if not digest:
            raise AuditorError("content_hash must not be blank")
        patient_id = (match_result.patient_id or "").strip()
        if not patient_id:
            raise AuditorError("patient_id must not be blank")

        try:
            tokens = normalize_redaction_tokens(redaction_tokens)
        except ValueError as exc:
            raise AuditorError(str(exc)) from exc

        versions = dict(agent_versions or {})
        versions[AGENT_NAME] = AGENT_VERSION

        ranked = sorted(match_result.matches, key=lambda m: m.score, reverse=True)
        matched_nct_ids = [m.nct_id for m in ranked]
        summary = build_justification_summary(match_result)
        extras = {
            "match_count": len(ranked),
            "match_scores": {m.nct_id: m.score for m in ranked},
        }

        try:
            record = AuditRecord(
                correlation_id=corr,
                patient_id=patient_id,
                content_hash=digest,
                agent_versions=versions,
                redaction_tokens=tokens,
                justification_summary=summary,
                matched_nct_ids=matched_nct_ids,
                extras=extras,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as exc:  # noqa: BLE001 — domain validation fail-closed
            raise AuditorError(f"AuditRecord validation failed: {exc}") from exc

        try:
            written = self._sink.append(record)
        except Exception as exc:  # noqa: BLE001
            raise AuditorError(f"Audit sink failed: {exc}") from exc

        logger.info(
            "auditor.audit.completed",
            extra=sanitize_log_extra(
                {
                    "agent_name": AGENT_NAME,
                    "correlation_id": corr,
                    "match_count": len(matched_nct_ids),
                    "written_rows": len(written),
                    "status": "ok",
                }
            ),
        )
        return AuditResult(record=record, written_match_ids=list(written))
