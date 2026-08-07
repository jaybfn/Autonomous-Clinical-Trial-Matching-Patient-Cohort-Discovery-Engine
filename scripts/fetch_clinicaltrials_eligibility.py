"""Fetch ClinicalTrials.gov studies into eligibility JSONL for Qdrant indexing.

Uses the public CT.gov API v2 (no API key). Writes records shaped for
``trialmatch.data.clinicaltrials_mapper.map_eligibility_record``.

Usage:
  python scripts/fetch_clinicaltrials_eligibility.py
  python scripts/fetch_clinicaltrials_eligibility.py --query "type 2 diabetes" --page-size 50
  python scripts/fetch_clinicaltrials_eligibility.py --max-studies 100
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "data" / "raw" / "clinicaltrials" / "eligibility.jsonl"
API = "https://clinicaltrials.gov/api/v2/studies"


def _split_criteria(raw: str) -> tuple[str, str]:
    """Best-effort split of CT.gov eligibilityCriteria into inclusion / exclusion."""
    text = (raw or "").strip()
    if not text:
        return "", ""
    match = re.search(r"(?i)\bexclusion\s+criteria\s*:", text)
    if not match:
        return text, ""
    inclusion = text[: match.start()]
    exclusion = text[match.end() :]
    inclusion = re.sub(r"(?i)^\s*inclusion\s+criteria\s*:\s*", "", inclusion).strip()
    return inclusion.strip(), exclusion.strip()


def _study_to_record(study: dict[str, Any]) -> dict[str, str] | None:
    proto = study.get("protocolSection") or {}
    ident = proto.get("identificationModule") or {}
    status = proto.get("statusModule") or {}
    elig = proto.get("eligibilityModule") or {}

    nct_id = str(ident.get("nctId") or "").strip()
    if not nct_id:
        return None
    inclusion, exclusion = _split_criteria(str(elig.get("eligibilityCriteria") or ""))
    if not inclusion and not exclusion:
        return None
    return {
        "nct_id": nct_id,
        "title": str(ident.get("briefTitle") or ident.get("officialTitle") or ""),
        "status": str(status.get("overallStatus") or ""),
        "inclusion_criteria": inclusion,
        "exclusion_criteria": exclusion,
    }


def fetch_studies(
    *,
    query: str,
    page_size: int,
    max_studies: int,
    status_filter: str = "RECRUITING",
) -> list[dict[str, str]]:
    """Fetch studies. max_studies <= 0 means paginate until CT.gov is exhausted."""
    records: list[dict[str, str]] = []
    page_token: str | None = None
    unlimited = max_studies <= 0
    while unlimited or len(records) < max_studies:
        take = page_size if unlimited else min(page_size, max_studies - len(records), 100)
        take = min(max(take, 1), 100)
        params: dict[str, str] = {
            "format": "json",
            "pageSize": str(take),
            "query.cond": query,
            "countTotal": "true",
        }
        if status_filter:
            params["filter.overallStatus"] = status_filter
        if page_token:
            params["pageToken"] = page_token
        url = f"{API}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310
            payload = json.loads(resp.read())
        if page_token is None and payload.get("totalCount") is not None:
            print(f"  CT.gov totalCount={payload['totalCount']}", flush=True)
        studies = payload.get("studies") or []
        if not studies:
            break
        for study in studies:
            rec = _study_to_record(study)
            if rec:
                records.append(rec)
            if not unlimited and len(records) >= max_studies:
                break
        print(f"  fetched {len(records)} usable records so far ...", flush=True)
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="type 2 diabetes", help="CT.gov condition query")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument(
        "--max-studies",
        type=int,
        default=0,
        help="Max studies to keep (0 = all pages for this query/filter). Default: 0",
    )
    parser.add_argument(
        "--status",
        default="RECRUITING",
        help="overallStatus filter (empty string = no filter)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    limit_label = "ALL" if args.max_studies <= 0 else str(args.max_studies)
    print(f"Fetching studies query={args.query!r} status={args.status!r} max={limit_label} ...")
    records = fetch_studies(
        query=args.query,
        page_size=args.page_size,
        max_studies=args.max_studies,
        status_filter=args.status,
    )
    if not records:
        print("No studies returned", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} trials -> {args.out}")
    print(f"Next: python scripts/index_trials_to_qdrant.py --sample-path {args.out} --live")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
