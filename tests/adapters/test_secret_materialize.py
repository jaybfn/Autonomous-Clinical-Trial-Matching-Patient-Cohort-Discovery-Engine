"""TDD: Secret Manager → local PEM path (no live GCP calls)."""

from __future__ import annotations

from pathlib import Path

import pytest

from trialmatch.adapters.secret_materialize import materialize_snowflake_secrets
from trialmatch.config.settings import Settings


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Settings:
    monkeypatch.setenv("GCP_PROJECT_ID", "autonomous-agent-503517")
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "xy12345.us-central1.gcp")
    monkeypatch.setenv("SNOWFLAKE_USER", "TRIALMATCH_APP")
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY_SM_ID", "trialmatch-snowflake-private-key")
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY_PATH", str(tmp_path / "snowflake-private-key.pem"))
    return Settings(_env_file=None)


def test_materialize_writes_pem_from_sm_id(settings: Settings, tmp_path: Path) -> None:
    # Split marker so pre-commit detect-private-key does not false-positive.
    pem = ("-----BEGIN " + "PRIVATE KEY-----\nabc\n-----END " + "PRIVATE KEY-----\n").encode()

    def fake_access(project_id: str, secret_id: str) -> bytes:
        assert project_id == "autonomous-agent-503517"
        assert secret_id == "trialmatch-snowflake-private-key"
        return pem

    updated = materialize_snowflake_secrets(settings, access_secret=fake_access)
    path = Path(updated.snowflake_private_key_path)
    assert path.is_file()
    assert path.read_bytes() == pem
    assert path.parent == tmp_path


def test_materialize_skips_when_path_already_exists(settings: Settings, tmp_path: Path) -> None:
    existing = tmp_path / "snowflake-private-key.pem"
    existing.write_text("already-here", encoding="utf-8")
    calls: list[str] = []

    def fake_access(project_id: str, secret_id: str) -> bytes:
        calls.append(secret_id)
        return b"new"

    updated = materialize_snowflake_secrets(settings, access_secret=fake_access)
    assert calls == []
    assert updated.snowflake_private_key_path == str(existing)
    assert existing.read_text(encoding="utf-8") == "already-here"


def test_materialize_loads_optional_passphrase(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "autonomous-agent-503517")
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY_SM_ID", "trialmatch-snowflake-private-key")
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE_SM_ID", "trialmatch-snowflake-passphrase")
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY_PATH", str(tmp_path / "snowflake-private-key.pem"))
    settings = Settings(_env_file=None)

    def fake_access(project_id: str, secret_id: str) -> bytes:
        if secret_id.endswith("passphrase"):
            return b"hunter2\n"
        return ("-----BEGIN " + "PRIVATE KEY-----\nx\n-----END " + "PRIVATE KEY-----\n").encode()

    updated = materialize_snowflake_secrets(settings, access_secret=fake_access)
    assert updated.snowflake_private_key_passphrase == "hunter2"
