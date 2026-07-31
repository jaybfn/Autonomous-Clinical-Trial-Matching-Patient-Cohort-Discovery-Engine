"""TDD: LangGraph fail-closed stops after agent errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trialmatch.agents.compliance.agent import ComplianceError, ScrubResult
from trialmatch.agents.parser.agent import ParserError, ParseResult
from trialmatch.orchestrator.graph import AgentBundle, build_match_graph, run_match_graph
from trialmatch.orchestrator.state import initial_match_state


@dataclass
class _OkCompliance:
    def scrub(self, text: str, *, correlation_id: str | None = None) -> ScrubResult:
        return ScrubResult(
            scrubbed_text="scrubbed",
            redaction_map={},
            redaction_count=0,
            content_hash="h1",
        )


@dataclass
class _BoomCompliance:
    def scrub(self, text: str, *, correlation_id: str | None = None) -> ScrubResult:
        raise ComplianceError("scrub failed")


@dataclass
class _BoomParser:
    def parse(self, **kwargs: Any) -> ParseResult:
        raise ParserError("llm down")


@dataclass
class _Unused:
    def match(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("matcher must not run after upstream failure")

    def audit(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("auditor must not run after upstream failure")

    def parse(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("parser must not run after compliance failure")


def test_graph_stops_when_compliance_fails() -> None:
    unused = _Unused()
    graph = build_match_graph(
        AgentBundle(
            compliance=_BoomCompliance(),  # type: ignore[arg-type]
            parser=unused,  # type: ignore[arg-type]
            matcher=unused,  # type: ignore[arg-type]
            auditor=unused,  # type: ignore[arg-type]
        )
    )
    final = run_match_graph(
        graph,
        initial_match_state(patient_id="p-1", note_text="x", correlation_id="c1"),
    )
    assert final["status"] == "failed"
    assert "scrub" in (final.get("error") or "").lower()
    assert "match_result" not in final or not final.get("match_result")


def test_graph_stops_when_parser_fails() -> None:
    unused = _Unused()
    graph = build_match_graph(
        AgentBundle(
            compliance=_OkCompliance(),  # type: ignore[arg-type]
            parser=_BoomParser(),  # type: ignore[arg-type]
            matcher=unused,  # type: ignore[arg-type]
            auditor=unused,  # type: ignore[arg-type]
        )
    )
    final = run_match_graph(
        graph,
        initial_match_state(patient_id="p-1", note_text="note", correlation_id="c2"),
    )
    assert final["status"] == "failed"
    assert (
        "llm" in (final.get("error") or "").lower()
        or "parser" in (final.get("error") or "").lower()
    )


def test_graph_rejects_blank_note() -> None:
    unused = _Unused()
    graph = build_match_graph(
        AgentBundle(
            compliance=_OkCompliance(),  # type: ignore[arg-type]
            parser=unused,  # type: ignore[arg-type]
            matcher=unused,  # type: ignore[arg-type]
            auditor=unused,  # type: ignore[arg-type]
        )
    )
    final = run_match_graph(
        graph,
        initial_match_state(patient_id="p-1", note_text="  ", correlation_id="c3"),
    )
    assert final["status"] == "failed"
    assert final.get("error")
