"""TDD: happy-path LangGraph Compliance → Parser → Matcher → Auditor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trialmatch.agents.auditor.agent import AuditResult
from trialmatch.agents.compliance.agent import ScrubResult
from trialmatch.agents.matcher.agent import MatchResult
from trialmatch.agents.parser.agent import ParseResult
from trialmatch.agents.parser.schemas import ParsedClinicalFeatures
from trialmatch.domain.audit import AuditRecord
from trialmatch.domain.trial import TrialMatch, TrialMatchResult
from trialmatch.orchestrator.graph import AgentBundle, build_match_graph, run_match_graph
from trialmatch.orchestrator.state import initial_match_state


@dataclass
class _FakeCompliance:
    def scrub(self, text: str, *, correlation_id: str | None = None) -> ScrubResult:
        assert "secret@example.com" in text or "note" in text.lower() or text
        return ScrubResult(
            scrubbed_text="Patient with diabetes [REDACTED_EMAIL_ab12]",
            redaction_map={"[REDACTED_EMAIL_ab12]": "email"},
            redaction_count=1,
            content_hash="hash-note-1",
            agent_version="0.1.0",
        )


@dataclass
class _FakeParser:
    def parse(
        self,
        *,
        scrubbed_text: str,
        patient_id: str,
        correlation_id: str | None = None,
    ) -> ParseResult:
        assert "[REDACTED_EMAIL_ab12]" in scrubbed_text
        features = ParsedClinicalFeatures(
            patient_id=patient_id,
            conditions=["Type 2 diabetes mellitus"],
            labs=[],
            medications=[],
            note_summary="diabetes",
        )
        return ParseResult(features=features, prompt_version="parser-v1")


@dataclass
class _FakeMatcher:
    def match(self, features: Any, *, correlation_id: str | None = None) -> MatchResult:
        assert features.patient_id == "p-001"
        assert "Type 2 diabetes mellitus" in features.conditions
        return MatchResult(
            result=TrialMatchResult(
                patient_id=features.patient_id,
                matches=[
                    TrialMatch(
                        nct_id="NCT01234567",
                        score=0.9,
                        evidence={"condition_hits": ["Type 2 diabetes mellitus"]},
                    )
                ],
            )
        )


@dataclass
class _FakeAuditor:
    def audit(
        self,
        *,
        match_result: TrialMatchResult,
        content_hash: str,
        redaction_tokens: dict[str, str],
        correlation_id: str,
        agent_versions: dict[str, str] | None = None,
    ) -> AuditResult:
        assert content_hash == "hash-note-1"
        assert redaction_tokens["[REDACTED_EMAIL_ab12]"] == "email"
        assert correlation_id == "corr-1"
        assert agent_versions is not None
        assert "compliance" in agent_versions
        record = AuditRecord(
            correlation_id=correlation_id,
            patient_id=match_result.patient_id,
            content_hash=content_hash,
            agent_versions={**(agent_versions or {}), "auditor": "0.1.0"},
            redaction_tokens=redaction_tokens,
            justification_summary="Matched NCT01234567",
            matched_nct_ids=[m.nct_id for m in match_result.matches],
            extras={"match_count": len(match_result.matches)},
        )
        return AuditResult(record=record, written_match_ids=["mid-1"])


def test_graph_happy_path_runs_all_agents_in_order() -> None:
    graph = build_match_graph(
        AgentBundle(
            compliance=_FakeCompliance(),  # type: ignore[arg-type]
            parser=_FakeParser(),  # type: ignore[arg-type]
            matcher=_FakeMatcher(),  # type: ignore[arg-type]
            auditor=_FakeAuditor(),  # type: ignore[arg-type]
        )
    )
    final = run_match_graph(
        graph,
        initial_match_state(
            patient_id="p-001",
            note_text="Patient secret@example.com has diabetes",
            correlation_id="corr-1",
        ),
    )
    assert final["status"] == "ok"
    assert final.get("error") in (None, "")
    assert final["content_hash"] == "hash-note-1"
    assert final["match_result"]["matches"][0]["nct_id"] == "NCT01234567"
    assert final["audit_record"]["matched_nct_ids"] == ["NCT01234567"]
    assert final["written_match_ids"] == ["mid-1"]
    assert final["agent_versions"]["auditor"] == "0.1.0"
