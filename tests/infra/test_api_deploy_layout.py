"""Contracts for API Deployment Snowflake wiring (no secret payloads in manifests)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API = REPO_ROOT / "k8s" / "api"


def test_api_configmap_and_deployment_exist() -> None:
    assert (API / "configmap.yaml").is_file()
    assert (API / "deployment.yaml").is_file()


def test_deployment_uses_configmap_and_workload_identity() -> None:
    deploy = (API / "deployment.yaml").read_text(encoding="utf-8")
    assert "serviceAccountName: trialmatch-ksa" in deploy
    assert "configMapRef:" in deploy
    assert "trialmatch-api-config" in deploy
    assert "LLM_PROVIDER" in deploy
    assert "vertex" in deploy


def test_configmap_references_sm_ids_not_pem_material() -> None:
    cm = (API / "configmap.yaml").read_text(encoding="utf-8")
    assert "SNOWFLAKE_PRIVATE_KEY_SM_ID" in cm
    assert "trialmatch-snowflake-private-key" in cm
    assert ("BEGIN " + "PRIVATE KEY") not in cm
    assert ("BEGIN RSA " + "PRIVATE KEY") not in cm
