"""PUT + COPY local Synthea CSVs into Snowflake RAW.RAW_SYNTHEA_* tables.

Expects slim files (not the full HF dump) under --data-dir, default:
  data/raw/synthea-hf/for_snowflake/{patients,labs,conditions}.csv

Usage:
  python scripts/put_copy_synthea_to_snowflake.py
  python scripts/put_copy_synthea_to_snowflake.py --truncate
  python scripts/put_copy_synthea_to_snowflake.py --data-dir /path/to/csvs
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from trialmatch.adapters.snowflake_client import SnowflakeClient
from trialmatch.config.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "raw" / "synthea-hf" / "for_snowflake"

FILE_FORMAT = """
FILE_FORMAT = (
  TYPE = CSV
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  EMPTY_FIELD_AS_NULL = TRUE
  ERROR_ON_COLUMN_COUNT_MISMATCH = TRUE
)
"""

TABLES: dict[str, tuple[str, str]] = {
    "RAW_SYNTHEA_PATIENTS": (
        "patients.csv",
        "ID, BIRTHDATE, GENDER, RACE, ETHNICITY, CITY, STATE",
    ),
    "RAW_SYNTHEA_LABS": (
        "labs.csv",
        "PATIENT, DATE, CODE, DESCRIPTION, VALUE, UNITS",
    ),
    "RAW_SYNTHEA_CONDITIONS": (
        "conditions.csv",
        'PATIENT, "START", "STOP", CODE, DESCRIPTION',
    ),
}


def _ensure_key_path(settings: Settings) -> Settings:
    """Expand $HOME and fall back to the Dev Container default key path."""
    key = (settings.snowflake_private_key_path or "").strip()
    if key:
        expanded = os.path.expanduser(os.path.expandvars(key))
        if expanded != settings.snowflake_private_key_path:
            settings = settings.model_copy(update={"snowflake_private_key_path": expanded})
        return settings
    default = Path.home() / "snowflake-keys" / "rsa_key.p8"
    if default.is_file():
        return settings.model_copy(update={"snowflake_private_key_path": str(default)})
    return settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=(
            f"Directory with patients.csv / labs.csv / conditions.csv (default: {DEFAULT_DATA_DIR})"
        ),
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="TRUNCATE RAW_SYNTHEA_PATIENTS/LABS/CONDITIONS before COPY",
    )
    parser.add_argument(
        "--role",
        default="ACCOUNTADMIN",
        help="Snowflake role used for PUT/COPY (default: ACCOUNTADMIN)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=REPO_ROOT / ".env",
        help="Path to .env (default: repo .env)",
    )
    args = parser.parse_args(argv)

    load_dotenv(args.env_file, override=True)
    settings = _ensure_key_path(Settings())
    if not settings.snowflake_account or not settings.snowflake_user:
        print("SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER are required (check .env)", file=sys.stderr)
        return 1
    if not settings.snowflake_private_key_path:
        print("SNOWFLAKE_PRIVATE_KEY_PATH is required", file=sys.stderr)
        return 1

    data_dir = args.data_dir.resolve()
    client = SnowflakeClient(settings=settings, role=args.role)
    client.execute("USE WAREHOUSE TRIALMATCH_WH")
    client.execute("USE DATABASE TRIALMATCH_DEV")
    client.execute("USE SCHEMA RAW")

    if args.truncate:
        for table in TABLES:
            print(f"TRUNCATE {table}")
            client.execute(f"TRUNCATE TABLE {table}")

    with client.connection.cursor() as cur:
        for table, (filename, cols) in TABLES.items():
            path = (data_dir / filename).resolve()
            if not path.is_file():
                print(f"Missing {path} — prepare slim CSVs first", file=sys.stderr)
                return 1

            put_sql = f"PUT file://{path} @%{table} AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
            print(f"PUT {path.name} -> @{table}")
            cur.execute(put_sql)
            print(cur.fetchall())

            copy_sql = f"""
            COPY INTO {table} ({cols})
            FROM @%{table}
            {FILE_FORMAT}
            ON_ERROR = 'CONTINUE'
            """
            print(f"COPY INTO {table}")
            cur.execute(copy_sql)
            result = cur.fetchall()
            print(result)
            # Snowflake COPY returns per-file stats; surface errors clearly.
            for row in result:
                # typical: (file, status, rows_parsed, rows_loaded, error_limit, errors_seen, ...)
                if len(row) >= 7 and row[1] not in ("LOADED", "PARTIALLY_LOADED"):
                    print(f"  warning: {row}")

    for table in TABLES:
        rows = client.fetch_all(f"SELECT COUNT(*) AS n FROM RAW.{table}")
        print(table, rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
