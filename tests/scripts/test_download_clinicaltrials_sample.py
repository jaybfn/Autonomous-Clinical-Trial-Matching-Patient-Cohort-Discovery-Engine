"""TDD contracts for optional ClinicalTrials.gov sample download."""

from __future__ import annotations

from pathlib import Path

from scripts.download_clinicaltrials_sample import download_clinicaltrials_sample


def test_download_clinicaltrials_sample_writes_jsonl(tmp_path: Path) -> None:
    payload = (
        b'{"nct_id":"NCT00000001","title":"T","inclusion_criteria":"A",'
        b'"exclusion_criteria":"B","status":"Recruiting"}\n'
    )

    def fake_fetch(url: str) -> bytes:
        assert "clinicaltrials" in url.lower() or url.startswith("http")
        return payload

    dest = download_clinicaltrials_sample(
        dest_dir=tmp_path / "clinicaltrials",
        filename="eligibility.jsonl",
        fetch=fake_fetch,
    )
    assert dest.read_bytes() == payload


def test_download_clinicaltrials_sample_creates_parent(tmp_path: Path) -> None:
    dest = download_clinicaltrials_sample(
        dest_dir=tmp_path / "nested" / "clinicaltrials",
        filename="eligibility.jsonl",
        fetch=lambda _url: b"{}\n",
    )
    assert dest.parent.is_dir()
