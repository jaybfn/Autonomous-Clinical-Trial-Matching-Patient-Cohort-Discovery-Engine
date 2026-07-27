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
    assert "password" not in settings.model_dump()
    assert "secret" not in str(settings.model_dump()).lower()


def test_settings_defaults_are_non_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "proj")
    settings = Settings(_env_file=None)
    assert settings.agent_read_role == "AGENT_READ_ROLE"
    assert settings.audit_write_role == "AUDIT_WRITE_ROLE"
    assert settings.qdrant_collection == "trial_criteria"


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
