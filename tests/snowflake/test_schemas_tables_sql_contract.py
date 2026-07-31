"""Contract tests for Snowflake landing schemas/tables (Phase 5)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SQL = (REPO_ROOT / "snowflake" / "sql" / "03_schemas_tables.sql").read_text(encoding="utf-8")


def test_schemas_tables_sql_exists() -> None:
    assert (REPO_ROOT / "snowflake" / "sql" / "03_schemas_tables.sql").is_file()


def test_schemas_include_raw_marts_audit() -> None:
    upper = SQL.upper()
    for schema in ("RAW", "MARTS", "AUDIT", "STAGING"):
        assert schema in upper, f"missing schema {schema}"


def test_raw_synthea_landing_tables_named_for_seed_script() -> None:
    upper = SQL.upper()
    assert "RAW_SYNTHEA_PATIENTS" in upper
    assert "RAW_SYNTHEA_LABS" in upper
    assert "RAW_SYNTHEA_CONDITIONS" in upper
    assert "AUDIT_MATCH_JUSTIFICATIONS" in upper


def test_start_stop_columns_are_quoted_identifiers() -> None:
    # START is a Snowflake reserved word; unquoted fails compilation.
    assert '"START"' in SQL
    assert '"STOP"' in SQL
