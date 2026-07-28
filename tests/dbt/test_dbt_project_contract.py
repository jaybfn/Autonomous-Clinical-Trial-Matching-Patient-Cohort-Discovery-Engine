"""Contract tests for dbt project layout (Phase 5)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DBT = REPO_ROOT / "dbt"


def test_dbt_project_yml_exists() -> None:
    path = DBT / "dbt_project.yml"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "trialmatch" in text.lower() or "name:" in text


def test_dbt_staging_and_mart_models_exist() -> None:
    required = [
        "models/staging/stg_patients.sql",
        "models/staging/stg_conditions.sql",
        "models/staging/stg_labs.sql",
        "models/staging/stg_encounters.sql",
        "models/marts/fct_patient_history.sql",
        "models/marts/dim_trial_eligibility_features.sql",
        "models/audit/audit_match_justifications.sql",
    ]
    for rel in required:
        assert (DBT / rel).is_file(), f"missing dbt/{rel}"


def test_dbt_schema_yml_defines_tests() -> None:
    schema = DBT / "models" / "schema.yml"
    assert schema.is_file()
    text = schema.read_text(encoding="utf-8")
    assert "not_null" in text
    assert "unique" in text or "relationships" in text
