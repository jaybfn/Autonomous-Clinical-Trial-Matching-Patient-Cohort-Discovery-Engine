"""Deserialize Pub/Sub payloads, invoke LangGraph, decide ack/nack/DLQ."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from pydantic import ValidationError

from trialmatch.domain.events import ClinicalEvent, EventType
from trialmatch.ingestion.dlq import is_poison_error
from trialmatch.observability.logging import get_logger, sanitize_log_extra
from trialmatch.observability.tracing import start_span
from trialmatch.orchestrator.state import MatchState, initial_match_state

logger = get_logger(__name__)


class HandleDisposition(str, Enum):
    ACK = "ack"
    NACK = "nack"


class GraphRunnerPort(Protocol):
    def run(self, state: MatchState) -> MatchState: ...


class DlqPort(Protocol):
    def publish_poison(
        self,
        *,
        original_data: bytes,
        reason: str,
        correlation_id: str,
        subscription: str,
        attributes: dict[str, str] | None = None,
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class HandleResult:
    disposition: HandleDisposition
    status: str  # ok | skipped | poison | retry | failed
    correlation_id: str
    detail: str = ""


def parse_clinical_event(data: bytes) -> ClinicalEvent:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid_json: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("invalid_json: root must be an object")
    try:
        return ClinicalEvent.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"invalid_schema: {exc}") from exc


def extract_note_text(event: ClinicalEvent) -> str | None:
    payload = event.payload or {}
    for key in ("note_text", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


class IngestionHandler:
    """At-least-once handler: ack on success/skip/poison; nack on transient errors."""

    def __init__(self, *, runner: GraphRunnerPort, dlq: DlqPort) -> None:
        self._runner = runner
        self._dlq = dlq

    def handle(
        self,
        *,
        data: bytes,
        message_id: str,
        attributes: dict[str, str],
        subscription: str,
    ) -> HandleResult:
        correlation_id = (message_id or "").strip() or "unknown"
        with start_span(
            "ingestion.handle",
            {"correlation_id": correlation_id, "event_type": "clinical_record"},
        ):
            try:
                event = parse_clinical_event(data)
            except ValueError as exc:
                return self._poison(
                    data=data,
                    reason=str(exc).split(":", 1)[0],
                    correlation_id=correlation_id,
                    subscription=subscription,
                    attributes=attributes,
                    detail=str(exc),
                )

            note = extract_note_text(event)
            if event.event_type == EventType.LAB_UPDATE and not note:
                logger.info(
                    "ingestion.skipped_lab",
                    extra=sanitize_log_extra(
                        {
                            "correlation_id": correlation_id,
                            "status": "skipped",
                            "event_type": event.event_type.value,
                        }
                    ),
                )
                return HandleResult(
                    disposition=HandleDisposition.ACK,
                    status="skipped",
                    correlation_id=correlation_id,
                    detail="lab_update without note text",
                )

            if not note:
                return self._poison(
                    data=data,
                    reason="missing_note_text",
                    correlation_id=correlation_id,
                    subscription=subscription,
                    attributes=attributes,
                    detail="clinical event missing note text",
                )

            state = initial_match_state(
                patient_id=event.patient_id,
                note_text=note,
                correlation_id=correlation_id,
            )
            try:
                final = self._runner.run(state)
            except Exception as exc:  # noqa: BLE001
                if is_poison_error(exc):
                    return self._poison(
                        data=data,
                        reason="graph_poison",
                        correlation_id=correlation_id,
                        subscription=subscription,
                        attributes=attributes,
                        detail=str(exc),
                    )
                logger.warning(
                    "ingestion.retry",
                    extra=sanitize_log_extra(
                        {
                            "correlation_id": correlation_id,
                            "status": "retry",
                            "error": type(exc).__name__,
                        }
                    ),
                )
                return HandleResult(
                    disposition=HandleDisposition.NACK,
                    status="retry",
                    correlation_id=correlation_id,
                    detail=str(exc),
                )

            status = str(final.get("status") or "failed")
            if status == "ok":
                logger.info(
                    "ingestion.ok",
                    extra=sanitize_log_extra(
                        {
                            "correlation_id": correlation_id,
                            "status": "ok",
                            "match_count": len(
                                (final.get("match_result") or {}).get("matches") or []
                            ),
                        }
                    ),
                )
                return HandleResult(
                    disposition=HandleDisposition.ACK,
                    status="ok",
                    correlation_id=correlation_id,
                )

            error = str(final.get("error") or "graph failed")
            if _is_transient_graph_error(error):
                return HandleResult(
                    disposition=HandleDisposition.NACK,
                    status="retry",
                    correlation_id=correlation_id,
                    detail=error,
                )

            return self._poison(
                data=data,
                reason="graph_failed",
                correlation_id=correlation_id,
                subscription=subscription,
                attributes=attributes,
                detail=error,
            )

    def _poison(
        self,
        *,
        data: bytes,
        reason: str,
        correlation_id: str,
        subscription: str,
        attributes: dict[str, str],
        detail: str,
    ) -> HandleResult:
        try:
            self._dlq.publish_poison(
                original_data=data,
                reason=reason,
                correlation_id=correlation_id,
                subscription=subscription,
                attributes=attributes,
            )
        except Exception as exc:  # noqa: BLE001
            # If DLQ publish fails, nack so Pub/Sub retries / native DLQ can take over.
            return HandleResult(
                disposition=HandleDisposition.NACK,
                status="retry",
                correlation_id=correlation_id,
                detail=f"dlq_publish_failed: {exc}",
            )
        logger.warning(
            "ingestion.poison",
            extra=sanitize_log_extra(
                {
                    "correlation_id": correlation_id,
                    "status": "poison",
                    "error": reason,
                }
            ),
        )
        return HandleResult(
            disposition=HandleDisposition.ACK,
            status="poison",
            correlation_id=correlation_id,
            detail=detail,
        )


def _is_transient_graph_error(message: str) -> bool:
    lowered = message.lower()
    markers = (
        "timeout",
        "timed out",
        "llm",
        "qdrant",
        "snowflake",
        "unavailable",
        "connection",
        "temporarily",
        "503",
        "429",
    )
    return any(marker in lowered for marker in markers)
