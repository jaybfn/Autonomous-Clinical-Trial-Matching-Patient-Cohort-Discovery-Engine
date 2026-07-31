"""TDD: API liveness / readiness contracts."""

from __future__ import annotations

from fastapi.testclient import TestClient

from trialmatch.api.main import create_app


def test_root_lists_endpoints() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "trialmatch-api"
    assert body["docs"] == "/docs"
    assert "match" in body["endpoints"]


def test_healthz_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert "service" in body
