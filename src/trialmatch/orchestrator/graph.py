"""Compile and run the match LangGraph (Compliance → Parser → Matcher → Auditor)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from langgraph.graph import END, START, StateGraph

from trialmatch.orchestrator.nodes import (
    AuditorPort,
    CompliancePort,
    MatcherPort,
    ParserPort,
    make_auditor_node,
    make_compliance_node,
    make_matcher_node,
    make_parser_node,
)
from trialmatch.orchestrator.state import MatchState


@dataclass(frozen=True, slots=True)
class AgentBundle:
    compliance: CompliancePort
    parser: ParserPort
    matcher: MatcherPort
    auditor: AuditorPort


class GraphRunner(Protocol):
    def run(self, state: MatchState) -> MatchState: ...


def _route_if_ok(state: MatchState) -> Literal["continue", "end"]:
    if state.get("status") == "failed" or state.get("error"):
        return "end"
    return "continue"


def build_match_graph(agents: AgentBundle) -> Any:
    """Build and compile the locked pipeline graph."""
    graph = StateGraph(MatchState)
    graph.add_node("compliance", make_compliance_node(agents.compliance))
    graph.add_node("parser", make_parser_node(agents.parser))
    graph.add_node("matcher", make_matcher_node(agents.matcher))
    graph.add_node("auditor", make_auditor_node(agents.auditor))

    graph.add_edge(START, "compliance")
    graph.add_conditional_edges(
        "compliance",
        _route_if_ok,
        {"continue": "parser", "end": END},
    )
    graph.add_conditional_edges(
        "parser",
        _route_if_ok,
        {"continue": "matcher", "end": END},
    )
    graph.add_conditional_edges(
        "matcher",
        _route_if_ok,
        {"continue": "auditor", "end": END},
    )
    graph.add_edge("auditor", END)
    return graph.compile()


def run_match_graph(graph: Any, state: MatchState) -> MatchState:
    """Invoke a compiled graph and normalize the final state."""
    final = graph.invoke(state)
    if final.get("status") not in {"ok", "failed"}:
        if final.get("error"):
            final["status"] = "failed"
        elif final.get("audit_record"):
            final["status"] = "ok"
        else:
            final["status"] = "failed"
            final.setdefault("error", "graph ended without completing auditor")
    return final  # type: ignore[return-value]


class CompiledGraphRunner:
    """Thin runner wrapper used by FastAPI dependency injection."""

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    def run(self, state: MatchState) -> MatchState:
        return run_match_graph(self._graph, state)
