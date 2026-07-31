"""LangGraph state for the clinical trial match pipeline."""

from __future__ import annotations

import uuid
from typing import Any, TypedDict


class MatchState(TypedDict, total=False):
    """Shared graph state — never put raw PHI into logs/spans from these fields."""

    correlation_id: str
    patient_id: str
    note_text: str
    scrubbed_text: str
    content_hash: str
    redaction_tokens: dict[str, str]
    features: dict[str, Any]
    match_result: dict[str, Any]
    audit_record: dict[str, Any]
    written_match_ids: list[str]
    agent_versions: dict[str, str]
    error: str | None
    status: str  # pending | ok | failed


def initial_match_state(
    *,
    patient_id: str,
    note_text: str,
    correlation_id: str | None = None,
) -> MatchState:
    return {
        "correlation_id": (correlation_id or "").strip() or str(uuid.uuid4()),
        "patient_id": (patient_id or "").strip(),
        "note_text": note_text or "",
        "agent_versions": {},
        "redaction_tokens": {},
        "written_match_ids": [],
        "error": None,
        "status": "pending",
    }
