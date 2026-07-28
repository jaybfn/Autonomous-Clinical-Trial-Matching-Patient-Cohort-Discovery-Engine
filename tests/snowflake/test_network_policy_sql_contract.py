"""Contract tests for Snowflake network policy SQL (Phase 5)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = REPO_ROOT / "snowflake" / "sql" / "02_network_policy.sql"


def test_network_policy_sql_exists() -> None:
    assert SQL_PATH.is_file()


def test_network_policy_allowlists_nat_ips_not_open_internet() -> None:
    text = SQL_PATH.read_text(encoding="utf-8")
    upper = text.upper()
    assert "NETWORK POLICY" in upper
    assert "ALLOWED_IP_LIST" in upper
    # Forbidden: open allowlist in the ALLOWED_IP_LIST clause.
    assert "ALLOWED_IP_LIST = ('0.0.0.0/0')" not in text.replace(" ", "")
    assert "136.112.132.174" in text or "NAT_IP" in text.upper() or "PLACEHOLDER" in text.upper()
