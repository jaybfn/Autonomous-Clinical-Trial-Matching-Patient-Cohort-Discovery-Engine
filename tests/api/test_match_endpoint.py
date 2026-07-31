"""TDD: /v1/match endpoint invokes orchestrator graph."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from trialmatch.api.deps import get_graph_runner
from trialmatch.api.main import create_app
from trialmatch.orchestrator.state import MatchState


class _FakeRunner:
    def __init__(self, result: MatchState | None = None, boom: bool = False) -> None:
        self.result = result
        self.boom = boom
        self.calls: list[dict[str, Any]] = []

    def run(self, state: MatchState) -> MatchState:
        self.calls.append(dict(state))
        if self.boom:
            raise RuntimeError("graph exploded")
        if self.result is not None:
            return self.result
        return {
            **state,
            "status": "ok",
            "content_hash": "h1",
            "scrubbed_text": "scrubbed",
            "match_result": {
                "patient_id": state["patient_id"],
                "matches": [{"nct_id": "NCT1", "score": 0.8, "evidence": {}}],
            },
            "audit_record": {
                "justification_summary": "Matched NCT1",
                "matched_nct_ids": ["NCT1"],
            },
            "written_match_ids": ["m1"],
            "agent_versions": {"auditor": "0.1.0"},
            "error": None,
        }


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    runner = _FakeRunner()
    app.dependency_overrides[get_graph_runner] = lambda: runner
    return TestClient(app)


def test_match_endpoint_returns_ranked_trials(client: TestClient) -> None:
    response = client.post(
        "/v1/match",
        json={
            "patient_id": "p-001",
            "note_text": "Patient with type 2 diabetes",
            "correlation_id": "corr-99",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["patient_id"] == "p-001"
    assert body["correlation_id"] == "corr-99"
    assert body["matches"][0]["nct_id"] == "NCT1"
    assert body["justification_summary"] == "Matched NCT1"
    assert body["content_hash"] == "h1"
    assert "note_text" not in body
    assert "scrubbed_text" not in body


def test_match_endpoint_validates_request() -> None:
    app = create_app()
    app.dependency_overrides[get_graph_runner] = lambda: _FakeRunner()
    client = TestClient(app)
    response = client.post("/v1/match", json={"patient_id": "", "note_text": "x"})
    assert response.status_code == 422


def test_match_endpoint_maps_failed_graph_to_200_with_status_failed() -> None:
    app = create_app()
    app.dependency_overrides[get_graph_runner] = lambda: _FakeRunner(
        result={
            "patient_id": "p-1",
            "note_text": "x",
            "correlation_id": "c1",
            "status": "failed",
            "error": "Parser failed: llm down",
            "agent_versions": {},
        }
    )
    client = TestClient(app)
    response = client.post(
        "/v1/match",
        json={"patient_id": "p-1", "note_text": "note body"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "llm" in body["error"].lower()
    assert body["matches"] == []
