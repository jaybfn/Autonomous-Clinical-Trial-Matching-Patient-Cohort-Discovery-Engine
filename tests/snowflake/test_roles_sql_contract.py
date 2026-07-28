"""Contract tests for Snowflake RBAC SQL (Phase 5)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLES_SQL = (REPO_ROOT / "snowflake" / "sql" / "01_roles.sql").read_text(encoding="utf-8")
SCHEMAS_SQL = (REPO_ROOT / "snowflake" / "sql" / "03_schemas_tables.sql").read_text(
    encoding="utf-8"
)


def test_roles_sql_file_exists() -> None:
    assert (REPO_ROOT / "snowflake" / "sql" / "01_roles.sql").is_file()


def test_roles_sql_defines_separated_read_and_audit_roles() -> None:
    upper = ROLES_SQL.upper()
    assert "AGENT_READ_ROLE" in upper
    assert "AUDIT_WRITE_ROLE" in upper
    assert "CREATE ROLE" in upper or "CREATE OR REPLACE ROLE" in upper


def test_schema_grants_select_to_read_and_insert_to_audit() -> None:
    """SELECT for Matcher vs INSERT for Auditor live in 03 after tables exist."""
    upper = SCHEMAS_SQL.upper()
    assert "GRANT SELECT" in upper
    assert "AGENT_READ_ROLE" in upper
    assert "GRANT INSERT" in upper
    assert "AUDIT_WRITE_ROLE" in upper
