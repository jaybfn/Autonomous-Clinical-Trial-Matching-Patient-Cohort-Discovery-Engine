"""TDD contracts for seeding Snowflake from Synthea samples (mocked client)."""

from __future__ import annotations

from pathlib import Path

from scripts.seed_snowflake_from_synthea import seed_snowflake_from_synthea

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "synthea"


class FakeSnowflakeClient:
    def __init__(self) -> None:
        self.rows_by_table: dict[str, list[dict]] = {}

    def insert_rows(self, table: str, rows: list[dict]) -> int:
        self.rows_by_table.setdefault(table, []).extend(rows)
        return len(rows)


def test_seed_loads_patients_labs_conditions(tmp_path: Path) -> None:
    # Use committed fixtures as sample root
    client = FakeSnowflakeClient()
    summary = seed_snowflake_from_synthea(
        sample_dir=FIXTURES,
        client=client,
        table_prefix="RAW_SYNTHEA",
    )
    assert summary["patients"] >= 1
    assert summary["labs"] >= 1
    assert summary["conditions"] >= 1
    assert "RAW_SYNTHEA_PATIENTS" in client.rows_by_table
    assert "RAW_SYNTHEA_LABS" in client.rows_by_table
    assert "RAW_SYNTHEA_CONDITIONS" in client.rows_by_table
    assert client.rows_by_table["RAW_SYNTHEA_PATIENTS"][0]["Id"]


def test_seed_requires_patients_csv(tmp_path: Path) -> None:
    import pytest

    client = FakeSnowflakeClient()
    with pytest.raises(FileNotFoundError):
        seed_snowflake_from_synthea(sample_dir=tmp_path, client=client)
