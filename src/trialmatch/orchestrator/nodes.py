"""LangGraph node functions for Compliance → Parser → Matcher → Auditor."""

from __future__ import annotations

from typing import Any, Protocol

from trialmatch.domain.patient import PatientFeatures
from trialmatch.domain.trial import TrialMatchResult
from trialmatch.observability.tracing import start_span
from trialmatch.orchestrator.state import MatchState


class CompliancePort(Protocol):
    def scrub(self, text: str, *, correlation_id: str | None = None) -> Any: ...


class ParserPort(Protocol):
    def parse(
        self,
        *,
        scrubbed_text: str,
        patient_id: str,
        correlation_id: str | None = None,
    ) -> Any: ...


class MatcherPort(Protocol):
    def match(self, features: PatientFeatures, *, correlation_id: str | None = None) -> Any: ...


class AuditorPort(Protocol):
    def audit(
        self,
        *,
        match_result: TrialMatchResult,
        content_hash: str,
        redaction_tokens: dict[str, str],
        correlation_id: str,
        agent_versions: dict[str, str] | None = None,
    ) -> Any: ...


def make_compliance_node(compliance: CompliancePort):
    def compliance_node(state: MatchState) -> dict[str, Any]:
        with start_span(
            "orchestrator.compliance",
            {"agent_name": "compliance", "correlation_id": state.get("correlation_id")},
        ):
            note = (state.get("note_text") or "").strip()
            if not note:
                return {"status": "failed", "error": "note_text must not be blank"}
            try:
                result = compliance.scrub(note, correlation_id=state.get("correlation_id"))
            except Exception as exc:  # noqa: BLE001 — fail closed
                return {"status": "failed", "error": f"Compliance failed: {exc}"}
            versions = dict(state.get("agent_versions") or {})
            versions["compliance"] = getattr(result, "agent_version", "0.1.0")
            return {
                "scrubbed_text": result.scrubbed_text,
                "content_hash": result.content_hash,
                "redaction_tokens": dict(result.redaction_map),
                "agent_versions": versions,
            }

    return compliance_node


def make_parser_node(parser: ParserPort):
    def parser_node(state: MatchState) -> dict[str, Any]:
        with start_span(
            "orchestrator.parser",
            {"agent_name": "parser", "correlation_id": state.get("correlation_id")},
        ):
            try:
                result = parser.parse(
                    scrubbed_text=state.get("scrubbed_text") or "",
                    patient_id=state.get("patient_id") or "",
                    correlation_id=state.get("correlation_id"),
                )
            except Exception as exc:  # noqa: BLE001
                return {"status": "failed", "error": f"Parser failed: {exc}"}
            versions = dict(state.get("agent_versions") or {})
            versions["parser"] = getattr(result, "agent_version", "0.1.0")
            patient_features = result.features.to_patient_features()
            return {
                "features": patient_features.model_dump(),
                "agent_versions": versions,
            }

    return parser_node


def make_matcher_node(matcher: MatcherPort):
    def matcher_node(state: MatchState) -> dict[str, Any]:
        with start_span(
            "orchestrator.matcher",
            {"agent_name": "matcher", "correlation_id": state.get("correlation_id")},
        ):
            try:
                features = PatientFeatures.model_validate(state.get("features") or {})
                result = matcher.match(features, correlation_id=state.get("correlation_id"))
            except Exception as exc:  # noqa: BLE001
                return {"status": "failed", "error": f"Matcher failed: {exc}"}
            versions = dict(state.get("agent_versions") or {})
            versions["matcher"] = getattr(result, "agent_version", "0.1.0")
            return {
                "match_result": result.result.model_dump(),
                "agent_versions": versions,
            }

    return matcher_node


def make_auditor_node(auditor: AuditorPort):
    def auditor_node(state: MatchState) -> dict[str, Any]:
        with start_span(
            "orchestrator.auditor",
            {"agent_name": "auditor", "correlation_id": state.get("correlation_id")},
        ):
            try:
                match_result = TrialMatchResult.model_validate(state.get("match_result") or {})
                result = auditor.audit(
                    match_result=match_result,
                    content_hash=state.get("content_hash") or "",
                    redaction_tokens=dict(state.get("redaction_tokens") or {}),
                    correlation_id=state.get("correlation_id") or "",
                    agent_versions=dict(state.get("agent_versions") or {}),
                )
            except Exception as exc:  # noqa: BLE001
                return {"status": "failed", "error": f"Auditor failed: {exc}"}
            versions = dict(state.get("agent_versions") or {})
            versions["auditor"] = getattr(result, "agent_version", "0.1.0")
            return {
                "audit_record": result.record.model_dump(),
                "written_match_ids": list(result.written_match_ids),
                "agent_versions": versions,
                "status": "ok",
                "error": None,
            }

    return auditor_node
