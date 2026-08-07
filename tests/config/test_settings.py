"""TDD contracts for env-only settings (no hardcoded secrets)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from trialmatch.config.settings import Settings


def test_settings_require_gcp_project_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("TRIALMATCH_GCP_PROJECT_ID", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "my-gcp-project")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "xy12345.us-central1.gcp")
    monkeypatch.setenv("PUBSUB_CLINICAL_TOPIC", "clinical-records")
    monkeypatch.setenv("PUBSUB_LAB_TOPIC", "lab-updates")

    settings = Settings(_env_file=None)
    assert settings.gcp_project_id == "my-gcp-project"
    assert settings.environment == "dev"
    assert settings.log_level == "DEBUG"
    assert settings.qdrant_url == "http://qdrant:6333"
    assert settings.snowflake_account == "xy12345.us-central1.gcp"
    dumped = settings.model_dump()
    assert "password" not in dumped
    assert ("BEGIN " + "PRIVATE KEY") not in str(dumped).upper()


def test_settings_defaults_are_non_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "proj")
    settings = Settings(_env_file=None)
    assert settings.agent_read_role == "AGENT_READ_ROLE"
    assert settings.audit_write_role == "AUDIT_WRITE_ROLE"
    assert settings.qdrant_collection == "trial_criteria"
    assert settings.embedding_provider == "deterministic"
    assert settings.embedding_dimension == 768
    assert settings.vertex_llm_model == "gemini-2.0-flash-001"
    assert settings.vertex_llm_location == "us-central1"
    assert settings.llm_provider == "ollama"
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_llm_model == "llama3.1:8b"
    assert settings.matcher_vector_limit == 10
    assert settings.matcher_snowflake_schema == "MARTS"
    assert settings.auditor_snowflake_schema == "AUDIT"
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8080
    assert settings.trialmatch_api_key == ""
    assert settings.pubsub_clinical_subscription == "clinical-records-sub"
    assert settings.pubsub_clinical_dlq_topic == "clinical-records-dlq"


def test_settings_otel_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "autonomous-agent-503517")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    settings = Settings(_env_file=None)
    assert settings.gcp_project_id == "autonomous-agent-503517"
    assert settings.otel_service_name == "trialmatch"
    assert settings.otel_exporter_otlp_endpoint == ""


def test_settings_otel_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "autonomous-agent-503517")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "trialmatch-api")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    settings = Settings(_env_file=None)
    assert settings.otel_service_name == "trialmatch-api"
    assert settings.otel_exporter_otlp_endpoint == "http://localhost:4317"
