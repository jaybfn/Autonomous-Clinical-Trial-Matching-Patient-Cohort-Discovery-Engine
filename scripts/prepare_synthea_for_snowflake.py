"""Build slim Synthea CSVs for Snowflake PUT/COPY from the HF SyntheticMass dump.

Reads:
  data/raw/synthea-hf/SyntheticMass_Data_Hack_ArangoDB/
    patients.csv, conditions.csv, observations.csv

Writes:
  data/raw/synthea-hf/for_snowflake/
    patients.csv, labs.csv, conditions.csv

HF quirks handled:
  - patients have ADDRESS but no CITY/STATE → leave CITY/STATE empty
  - observations.csv is used as labs.csv
  - only rows for the first N patients (by appearance in patients.csv)

Usage:
  python scripts/prepare_synthea_for_snowflake.py
  python scripts/prepare_synthea_for_snowflake.py --limit 5000
  python scripts/prepare_synthea_for_snowflake.py --limit 0   # all patients (slow / huge)
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = REPO_ROOT / "data" / "raw" / "synthea-hf" / "SyntheticMass_Data_Hack_ArangoDB"
DEFAULT_OUT = REPO_ROOT / "data" / "raw" / "synthea-hf" / "for_snowflake"

PATIENT_OUT_COLS = ["ID", "BIRTHDATE", "GENDER", "RACE", "ETHNICITY", "CITY", "STATE"]
LAB_OUT_COLS = ["PATIENT", "DATE", "CODE", "DESCRIPTION", "VALUE", "UNITS"]
CONDITION_OUT_COLS = ["PATIENT", "START", "STOP", "CODE", "DESCRIPTION"]

# HF dump has some rows with unquoted commas that shift columns.
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_valid_patient_row(row: dict[str, str]) -> bool:
    pid = (row.get("ID") or row.get("Id") or "").strip()
    birthdate = (row.get("BIRTHDATE") or "").strip()
    gender = (row.get("GENDER") or "").strip().upper()
    return bool(_UUID_RE.match(pid) and _DATE_RE.match(birthdate) and gender in {"M", "F"})


def _write_patients(src: Path, out: Path, limit: int) -> set[str]:
    patient_ids: set[str] = set()
    skipped = 0
    with (
        src.open(newline="", encoding="utf-8") as fin,
        out.open("w", newline="", encoding="utf-8") as fout,
    ):
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=PATIENT_OUT_COLS, lineterminator="\n")
        writer.writeheader()
        for row in reader:
            if not _is_valid_patient_row(row):
                skipped += 1
                continue
            if limit > 0 and len(patient_ids) >= limit:
                break
            pid = (row.get("ID") or row.get("Id") or "").strip()
            patient_ids.add(pid)
            writer.writerow(
                {
                    "ID": pid,
                    "BIRTHDATE": (row.get("BIRTHDATE") or "").strip(),
                    "GENDER": (row.get("GENDER") or "").strip().upper(),
                    "RACE": row.get("RACE", ""),
                    "ETHNICITY": row.get("ETHNICITY", ""),
                    "CITY": row.get("CITY", ""),
                    "STATE": row.get("STATE", ""),
                }
            )
    print(f"  skipped malformed patient rows: {skipped}")
    return patient_ids


def _filter_write(
    *,
    src: Path,
    out: Path,
    out_cols: list[str],
    patient_ids: set[str],
    patient_field: str = "PATIENT",
    progress_every: int = 500_000,
) -> int:
    kept = 0
    scanned = 0
    with (
        src.open(newline="", encoding="utf-8") as fin,
        out.open("w", newline="", encoding="utf-8") as fout,
    ):
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=out_cols, lineterminator="\n")
        writer.writeheader()
        for row in reader:
            scanned += 1
            if progress_every and scanned % progress_every == 0:
                print(f"  ... scanned {scanned:,} rows, kept {kept:,}", flush=True)
            pid = (row.get(patient_field) or "").strip()
            if pid not in patient_ids:
                continue
            writer.writerow({col: row.get(col, "") for col in out_cols})
            kept += 1
    print(f"  scanned {scanned:,} total rows", flush=True)
    return kept


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src-dir", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--limit",
        type=int,
        default=5000,
        help="Max patients to include (0 = all). Default: 5000",
    )
    args = parser.parse_args(argv)

    src_dir = args.src_dir.resolve()
    out_dir = args.out_dir.resolve()
    for name in ("patients.csv", "conditions.csv", "observations.csv"):
        path = src_dir / name
        if not path.is_file():
            print(f"Missing source file: {path}", file=sys.stderr)
            return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Writing patients (limit={args.limit}) ...")
    patient_ids = _write_patients(src_dir / "patients.csv", out_dir / "patients.csv", args.limit)
    print(f"  patients: {len(patient_ids)}")

    print("Filtering conditions ...")
    n_cond = _filter_write(
        src=src_dir / "conditions.csv",
        out=out_dir / "conditions.csv",
        out_cols=CONDITION_OUT_COLS,
        patient_ids=patient_ids,
    )
    print(f"  conditions: {n_cond}")

    print("Filtering observations -> labs (this can take a while) ...")
    n_labs = _filter_write(
        src=src_dir / "observations.csv",
        out=out_dir / "labs.csv",
        out_cols=LAB_OUT_COLS,
        patient_ids=patient_ids,
    )
    print(f"  labs: {n_labs}")

    print(f"Done. Slim CSVs in {out_dir}")
    print("Next: python scripts/put_copy_synthea_to_snowflake.py --truncate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
