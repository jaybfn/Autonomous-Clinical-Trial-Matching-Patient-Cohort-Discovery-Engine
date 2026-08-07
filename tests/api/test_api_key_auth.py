"""API key auth for POST /v1/match."""

from __future__ import annotations

from fastapi.testclient import TestClient

from trialmatch.api.deps import get_graph_runner
from trialmatch.api.main import create_app
from trialmatch.config.settings import Settings
from trialmatch.orchestrator.state import MatchState


class _FakeRunner:
    def run(self, state: MatchState) -> MatchState:
        return {
            **state,
            "status": "ok",
            "content_hash": "h1",
            "match_result": {
                "patient_id": state["patient_id"],
                "matches": [{"nct_id": "NCT1", "score": 0.8, "evidence": {}}],
            },
            "audit_record": {"justification_summary": "ok", "matched_nct_ids": ["NCT1"]},
            "written_match_ids": [],
            "agent_versions": {},
            "error": None,
        }


def _client_with_api_key(api_key: str) -> TestClient:
    settings = Settings.model_validate(
        {
            "GCP_PROJECT_ID": "test-project",
            "TRIALMATCH_API_KEY": api_key,
        }
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_graph_runner] = lambda: _FakeRunner()
    return TestClient(app)


def test_match_without_api_key_configured_allows_unauthenticated() -> None:
    client = _client_with_api_key("")
    response = client.post(
        "/v1/match",
        json={"patient_id": "p-1", "note_text": "diabetes"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_match_with_api_key_rejects_missing_header() -> None:
    client = _client_with_api_key("super-secret")
    response = client.post(
        "/v1/match",
        json={"patient_id": "p-1", "note_text": "diabetes"},
    )
    assert response.status_code == 401
    assert "api key" in response.json()["detail"].lower()


def test_match_with_api_key_rejects_wrong_header() -> None:
    client = _client_with_api_key("super-secret")
    response = client.post(
        "/v1/match",
        json={"patient_id": "p-1", "note_text": "diabetes"},
        headers={"X-API-Key": "wrong"},
    )
    assert response.status_code == 401


def test_match_with_api_key_accepts_correct_header() -> None:
    client = _client_with_api_key("super-secret")
    response = client.post(
        "/v1/match",
        json={"patient_id": "p-1", "note_text": "diabetes"},
        headers={"X-API-Key": "super-secret"},
    )
    assert response.status_code == 200
    assert response.json()["matches"][0]["nct_id"] == "NCT1"


def test_healthz_remains_unauthenticated_when_api_key_set() -> None:
    client = _client_with_api_key("super-secret")
    assert client.get("/healthz").status_code == 200
