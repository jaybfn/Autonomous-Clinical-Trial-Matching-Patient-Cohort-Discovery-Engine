"""Seed Snowflake landing tables from Synthea sample CSVs (client injected; ADC later)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Protocol

from trialmatch.data.synthea_mapper import read_synthea_csv


class SnowflakeSeedClient(Protocol):
    def insert_rows(self, table: str, rows: list[dict]) -> int: ...


def seed_snowflake_from_synthea(
    *,
    sample_dir: Path,
    client: SnowflakeSeedClient,
    table_prefix: str = "RAW_SYNTHEA",
) -> dict[str, int]:
    patients_path = sample_dir / "patients.csv"
    if not patients_path.is_file():
        raise FileNotFoundError(f"Missing required file: {patients_path}")

    files = {
        "patients": ("patients.csv", f"{table_prefix}_PATIENTS"),
        "labs": ("labs.csv", f"{table_prefix}_LABS"),
        "conditions": ("conditions.csv", f"{table_prefix}_CONDITIONS"),
    }
    summary: dict[str, int] = {}
    for key, (filename, table) in files.items():
        path = sample_dir / filename
        if not path.is_file():
            summary[key] = 0
            continue
        rows = list(read_synthea_csv(path))
        summary[key] = client.insert_rows(table, rows)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample-dir",
        type=Path,
        default=Path("data/synthea/samples"),
    )
    parser.add_argument("--table-prefix", default="RAW_SYNTHEA")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and count rows without inserting (no Snowflake client).",
    )
    args = parser.parse_args(argv)

    if args.dry_run:

        class _DryRun:
            def insert_rows(self, table: str, rows: list[dict]) -> int:
                print(f"{table}: {len(rows)} rows")
                return len(rows)

        summary = seed_snowflake_from_synthea(
            sample_dir=args.sample_dir, client=_DryRun(), table_prefix=args.table_prefix
        )
    else:
        raise SystemExit(
            "Live Snowflake seeding requires a Workload Identity / ADC client "
            "(Phase 5). Use --dry-run or inject a client in code/tests."
        )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
