"""Snowflake read queries for Matcher — AGENT_READ_ROLE / SELECT only."""

from __future__ import annotations

import re
from typing import Any

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

PATIENT_FEATURE_COLUMNS = (
    "feature_type",
    "feature_code",
    "feature_label",
    "feature_value",
    "feature_units",
)


def build_patient_features_sql(*, schema: str = "MARTS") -> str:
    """SELECT patient×feature rows from the dbt eligibility feature mart."""
    if not _SAFE_IDENTIFIER.match(schema):
        raise ValueError(f"Unsafe Snowflake schema identifier: {schema!r}")
    cols = ", ".join(PATIENT_FEATURE_COLUMNS)
    return f"SELECT {cols}\nFROM {schema}.DIM_TRIAL_ELIGIBILITY_FEATURES\nWHERE patient_id = %s"


def _row_get(row: dict[str, Any], key: str) -> Any:
    if key in row:
        return row[key]
    upper = key.upper()
    if upper in row:
        return row[upper]
    lower = key.lower()
    if lower in row:
        return row[lower]
    return None


def rows_to_condition_labels(rows: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for row in rows:
        if str(_row_get(row, "feature_type") or "").lower() != "condition":
            continue
        label = _row_get(row, "feature_label")
        if label and str(label).strip():
            labels.append(str(label).strip())
    return labels


def rows_to_lab_labels(rows: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for row in rows:
        if str(_row_get(row, "feature_type") or "").lower() != "lab":
            continue
        label = _row_get(row, "feature_label")
        if label and str(label).strip():
            labels.append(str(label).strip())
    return labels


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def merge_patient_signals(
    *,
    parser_conditions: list[str],
    parser_labs: list[dict[str, Any]],
    snowflake_conditions: list[str],
    snowflake_labs: list[str],
) -> tuple[list[str], list[str]]:
    """Union Parser + Snowflake labels; Parser order wins for casing."""
    lab_names = [
        str(lab.get("name") or lab.get("code") or "").strip()
        for lab in parser_labs
        if isinstance(lab, dict)
    ]
    conditions = _dedupe_preserve([*parser_conditions, *snowflake_conditions])
    labs = _dedupe_preserve([*lab_names, *snowflake_labs])
    return conditions, labs
