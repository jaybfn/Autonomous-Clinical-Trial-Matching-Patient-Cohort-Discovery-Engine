"""Map ClinicalTrials.gov eligibility records into trial documents for Qdrant."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def read_eligibility_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Expected object at {path}:{line_no}")
            yield record


def map_eligibility_record(record: dict[str, Any]) -> dict[str, Any]:
    nct_id = str(record.get("nct_id") or "").strip()
    if not nct_id:
        raise ValueError("Eligibility record missing required field: nct_id")

    inclusion = str(record.get("inclusion_criteria") or "").strip()
    exclusion = str(record.get("exclusion_criteria") or "").strip()
    eligibility_text = (
        f"Inclusion criteria:\n{inclusion}\n\nExclusion criteria:\n{exclusion}"
    ).strip()

    return {
        "nct_id": nct_id,
        "source": "clinicaltrials.gov",
        "title": str(record.get("title") or ""),
        "status": str(record.get("status") or ""),
        "inclusion_criteria": inclusion,
        "exclusion_criteria": exclusion,
        "eligibility_text": eligibility_text,
    }
