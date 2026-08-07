"""Load tiny committed Synthea samples into Snowflake RAW tables (no pandas)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from dotenv import load_dotenv

from trialmatch.adapters.snowflake_client import SnowflakeClient
from trialmatch.config.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "data" / "synthea" / "samples"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    load_dotenv(REPO_ROOT / ".env", override=True)
    settings = Settings()
    client = SnowflakeClient(settings=settings, role="ACCOUNTADMIN")
    client.execute("USE WAREHOUSE TRIALMATCH_WH")
    client.execute("USE DATABASE TRIALMATCH_DEV")
    client.execute("USE SCHEMA RAW")

    patients = read_csv(SAMPLE_DIR / "patients.csv")
    labs = read_csv(SAMPLE_DIR / "labs.csv")
    conditions = read_csv(SAMPLE_DIR / "conditions.csv")

    with client.connection.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO RAW_SYNTHEA_PATIENTS
              (ID, BIRTHDATE, GENDER, RACE, ETHNICITY, CITY, STATE)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    row.get("Id") or row.get("ID"),
                    row["BIRTHDATE"] or None,
                    row["GENDER"],
                    row["RACE"],
                    row["ETHNICITY"],
                    row["CITY"],
                    row["STATE"],
                )
                for row in patients
            ],
        )
        print("patients", cur.rowcount)

        cur.executemany(
            """
            INSERT INTO RAW_SYNTHEA_LABS
              (PATIENT, DATE, CODE, DESCRIPTION, VALUE, UNITS)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    row["PATIENT"],
                    row["DATE"].replace("Z", "") if row.get("DATE") else None,
                    row["CODE"],
                    row["DESCRIPTION"],
                    float(row["VALUE"]) if row.get("VALUE") else None,
                    row["UNITS"],
                )
                for row in labs
            ],
        )
        print("labs", cur.rowcount)

        cur.executemany(
            """
            INSERT INTO RAW_SYNTHEA_CONDITIONS
              (PATIENT, "START", "STOP", CODE, DESCRIPTION)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [
                (
                    row["PATIENT"],
                    row["START"] or None,
                    row["STOP"] or None,
                    row["CODE"],
                    row["DESCRIPTION"],
                )
                for row in conditions
            ],
        )
        print("conditions", cur.rowcount)

    print(client.fetch_all("SELECT COUNT(*) AS n FROM RAW.RAW_SYNTHEA_PATIENTS"))
    print(client.fetch_all("SELECT COUNT(*) AS n FROM RAW.RAW_SYNTHEA_LABS"))
    print(client.fetch_all("SELECT COUNT(*) AS n FROM RAW.RAW_SYNTHEA_CONDITIONS"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
