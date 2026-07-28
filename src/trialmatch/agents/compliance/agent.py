"""Compliance agent — scrub PHI before parser / matcher / logs see raw notes."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from trialmatch.agents.compliance.ner import NerBackend, RuleBasedPersonNer
from trialmatch.agents.compliance.patterns import PhiSpan, find_phi_spans
from trialmatch.domain.events import ClinicalEvent
from trialmatch.observability.logging import get_logger, sanitize_log_extra

logger = get_logger(__name__)

AGENT_NAME = "compliance"
AGENT_VERSION = "0.1.0"


class ComplianceError(RuntimeError):
    """Fail-closed error when scrubbing cannot complete safely."""


@dataclass(frozen=True, slots=True)
class ScrubResult:
    scrubbed_text: str
    redaction_map: dict[str, str]  # token -> entity_type (never raw PHI)
    redaction_count: int
    content_hash: str
    agent_version: str = AGENT_VERSION


def _token_for(entity_type: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"[REDACTED_{entity_type.upper()}_{digest}]"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _merge_spans(*groups: list[PhiSpan]) -> list[PhiSpan]:
    candidates = [span for group in groups for span in group]
    candidates.sort(key=lambda s: (s.start, -(s.end - s.start)))
    selected: list[PhiSpan] = []
    occupied_until = -1
    for span in candidates:
        if span.start < occupied_until:
            continue
        selected.append(span)
        occupied_until = span.end
    return selected


class ComplianceAgent:
    """Orchestrates regex patterns + NER; returns scrubbed text + stable tokens."""

    def __init__(self, *, ner: NerBackend | None = None) -> None:
        self._ner: NerBackend = ner if ner is not None else RuleBasedPersonNer()

    def scrub(self, text: str, *, correlation_id: str | None = None) -> ScrubResult:
        if text is None:
            raise ComplianceError("text must not be None")

        try:
            ner_spans = self._ner.find_entities(text)
        except Exception as exc:  # noqa: BLE001 — fail closed
            raise ComplianceError(f"NER backend failed: {exc}") from exc

        spans = _merge_spans(find_phi_spans(text), ner_spans)
        redaction_map: dict[str, str] = {}
        # Replace from the end so offsets stay valid.
        scrubbed = text
        for span in sorted(spans, key=lambda s: s.start, reverse=True):
            token = _token_for(span.entity_type, span.text)
            redaction_map[token] = span.entity_type
            scrubbed = scrubbed[: span.start] + token + scrubbed[span.end :]

        result = ScrubResult(
            scrubbed_text=scrubbed,
            redaction_map=redaction_map,
            redaction_count=len(redaction_map),
            content_hash=_content_hash(text),
        )

        # PHI-safe log: never include note text or raw values.
        logger.info(
            "compliance.scrub.completed",
            extra=sanitize_log_extra(
                {
                    "agent_name": AGENT_NAME,
                    "correlation_id": correlation_id or "",
                    "redaction_count": result.redaction_count,
                    "content_hash": result.content_hash,
                    "status": "ok",
                }
            ),
        )
        return result

    def scrub_event(
        self, event: ClinicalEvent, *, note_keys: tuple[str, ...] = ("note_text", "text")
    ) -> tuple[ClinicalEvent, ScrubResult | None]:
        """Return a copy of the event with note fields scrubbed."""
        payload = dict(event.payload)
        last: ScrubResult | None = None
        for key in note_keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                last = self.scrub(value, correlation_id=event.patient_id)
                payload[key] = last.scrubbed_text
        updated = event.model_copy(update={"payload": payload})
        return updated, last
