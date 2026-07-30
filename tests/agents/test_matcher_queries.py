"""TDD contracts for Matcher Snowflake query builders (AGENT_READ_ROLE only)."""

from __future__ import annotations

from trialmatch.agents.matcher.queries import (
    PATIENT_FEATURE_COLUMNS,
    build_patient_features_sql,
    merge_patient_signals,
    rows_to_condition_labels,
    rows_to_lab_labels,
)


def test_patient_features_sql_is_select_only() -> None:
    sql = build_patient_features_sql(schema="MARTS")
    lowered = sql.lower()
    assert "select" in lowered
    assert "dim_trial_eligibility_features" in lowered
    assert "where patient_id" in lowered
    assert "insert" not in lowered
    assert "update" not in lowered
    assert "delete" not in lowered
    assert "merge" not in lowered
    for col in PATIENT_FEATURE_COLUMNS:
        assert col.lower() in lowered


def test_patient_features_sql_rejects_unsafe_schema() -> None:
    import pytest

    with pytest.raises(ValueError, match="schema"):
        build_patient_features_sql(schema="MARTS; DROP TABLE X")


def test_rows_to_labels() -> None:
    rows = [
        {
            "FEATURE_TYPE": "condition",
            "FEATURE_CODE": "44054006",
            "FEATURE_LABEL": "Diabetes mellitus type 2",
            "FEATURE_VALUE": None,
            "FEATURE_UNITS": None,
        },
        {
            "feature_type": "lab",
            "feature_code": "4548-4",
            "feature_label": "HbA1c",
            "feature_value": 8.1,
            "feature_units": "%",
        },
    ]
    assert rows_to_condition_labels(rows) == ["Diabetes mellitus type 2"]
    assert rows_to_lab_labels(rows) == ["HbA1c"]


def test_merge_patient_signals_dedupes_case_insensitively() -> None:
    conditions, labs = merge_patient_signals(
        parser_conditions=["Diabetes", "Hypertension"],
        parser_labs=[{"name": "HbA1c"}, {"name": "Creatinine"}],
        snowflake_conditions=["diabetes", "Asthma"],
        snowflake_labs=["hba1c", "LDL"],
    )
    assert conditions == ["Diabetes", "Hypertension", "Asthma"]
    assert labs == ["HbA1c", "Creatinine", "LDL"]
