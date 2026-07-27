"""TDD contracts for optional Synthea sample download into data/raw/."""

from __future__ import annotations

from pathlib import Path

from scripts.download_synthea_sample import download_synthea_sample


def test_download_synthea_sample_writes_to_raw_dir(tmp_path: Path) -> None:
    payload = b"Id,BIRTHDATE\np-001,1980-01-01\n"
    calls: list[str] = []

    def fake_fetch(url: str) -> bytes:
        calls.append(url)
        return payload

    dest = download_synthea_sample(
        dest_dir=tmp_path / "synthea",
        filename="patients.csv",
        fetch=fake_fetch,
    )
    assert dest.is_file()
    assert dest.read_bytes() == payload
    assert dest.parent == tmp_path / "synthea"
    assert calls and calls[0].startswith("http")


def test_download_synthea_sample_rejects_path_escape(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="filename"):
        download_synthea_sample(
            dest_dir=tmp_path,
            filename="../evil.csv",
            fetch=lambda _url: b"x",
        )
