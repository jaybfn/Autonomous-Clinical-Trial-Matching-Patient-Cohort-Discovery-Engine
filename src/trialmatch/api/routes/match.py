"""Match API — invoke the shared LangGraph pipeline."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from trialmatch.api.deps import get_graph_runner
from trialmatch.api.schemas import MatchItem, MatchRequest, MatchResponse
from trialmatch.observability.logging import get_logger, sanitize_log_extra
from trialmatch.observability.tracing import start_span
from trialmatch.orchestrator.graph import GraphRunner
from trialmatch.orchestrator.state import initial_match_state

router = APIRouter(prefix="/v1", tags=["match"])
logger = get_logger(__name__)


def _response_from_state(state: dict[str, Any]) -> MatchResponse:
    match_result = state.get("match_result") or {}
    raw_matches = match_result.get("matches") or []
    matches = [
        MatchItem(
            nct_id=str(item.get("nct_id")),
            score=float(item.get("score") or 0.0),
            evidence=dict(item.get("evidence") or {}),
        )
        for item in raw_matches
        if item.get("nct_id")
    ]
    audit = state.get("audit_record") or {}
    return MatchResponse(
        correlation_id=str(state.get("correlation_id") or ""),
        patient_id=str(state.get("patient_id") or ""),
        status=str(state.get("status") or "failed"),
        matches=matches,
        justification_summary=audit.get("justification_summary"),
        content_hash=state.get("content_hash"),
        written_match_ids=list(state.get("written_match_ids") or []),
        agent_versions=dict(state.get("agent_versions") or {}),
        error=state.get("error"),
    )


@router.post("/match", response_model=MatchResponse)
def match_trials(
    body: MatchRequest,
    runner: Annotated[GraphRunner, Depends(get_graph_runner)],
) -> MatchResponse:
    state = initial_match_state(
        patient_id=body.patient_id,
        note_text=body.note_text,
        correlation_id=body.correlation_id,
    )
    with start_span(
        "api.match",
        {
            "correlation_id": state["correlation_id"],
            "event_type": "clinical_record",
            "status": "started",
        },
    ):
        final = runner.run(state)
    logger.info(
        "api.match.completed",
        extra=sanitize_log_extra(
            {
                "correlation_id": final.get("correlation_id") or "",
                "status": final.get("status") or "failed",
                "match_count": len((final.get("match_result") or {}).get("matches") or []),
            }
        ),
    )
    return _response_from_state(final)
