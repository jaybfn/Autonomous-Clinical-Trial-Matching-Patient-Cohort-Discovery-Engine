"""TDD contracts for Snowflake adapter — fully mocked (no live warehouse)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trialmatch.adapters.snowflake_client import (
    SnowflakeClient,
    agent_read_client,
    audit_write_client,
)
from trialmatch.config.settings import Settings


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("GCP_PROJECT_ID", "autonomous-agent-503517")
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "xy12345.us-central1.gcp")
    monkeypatch.setenv("SNOWFLAKE_USER", "TRIALMATCH_APP")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSE", "TRIALMATCH_WH")
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "TRIALMATCH_DEV")
    monkeypatch.setenv("SNOWFLAKE_SCHEMA", "MARTS")
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY_PATH", "/tmp/sf-key.pem")
    return Settings(_env_file=None)


def test_agent_read_client_uses_agent_read_role(settings: Settings) -> None:
    conn = MagicMock()
    client = agent_read_client(settings, connect=lambda **_: conn)
    assert client.role == "AGENT_READ_ROLE"
    assert client.connection is conn


def test_audit_write_client_uses_audit_write_role(settings: Settings) -> None:
    conn = MagicMock()
    client = audit_write_client(settings, connect=lambda **_: conn)
    assert client.role == "AUDIT_WRITE_ROLE"


def test_fetch_all_executes_with_read_role(settings: Settings) -> None:
    cursor = MagicMock()
    cursor.description = [("PATIENT_ID",), ("CONDITION_CODE",)]
    cursor.fetchall.return_value = [("p-001", "44054006")]
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    client = SnowflakeClient(settings=settings, role="AGENT_READ_ROLE", connection=conn)
    rows = client.fetch_all("SELECT patient_id, condition_code FROM marts.fct_patient_history")
    assert rows == [{"PATIENT_ID": "p-001", "CONDITION_CODE": "44054006"}]
    cursor.execute.assert_called()


def test_execute_insert_for_audit(settings: Settings) -> None:
    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    client = SnowflakeClient(settings=settings, role="AUDIT_WRITE_ROLE", connection=conn)
    client.execute(
        "INSERT INTO audit.audit_match_justifications (match_id, justification) VALUES (%s, %s)",
        ("m-1", "meets HbA1c criterion"),
    )
    cursor.execute.assert_called_once()


def test_settings_expose_private_key_path_not_secret_material(
    settings: Settings,
) -> None:
    dumped = settings.model_dump()
    assert "snowflake_private_key_path" in dumped
    assert "BEGIN" not in str(dumped).upper()
    assert "PRIVATE KEY" not in str(dumped).upper()
