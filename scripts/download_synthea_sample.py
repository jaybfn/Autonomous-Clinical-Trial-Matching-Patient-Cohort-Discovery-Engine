"""Optional download of Synthea-shaped sample files into gitignored data/raw/."""

from __future__ import annotations

import argparse
import urllib.request
from collections.abc import Callable
from pathlib import Path

# Public demo URL placeholder — real bulk pulls should target Synthea releases / Open Data.
DEFAULT_SYNTHEA_SAMPLE_URL = (
    "https://raw.githubusercontent.com/synthetichealth/synthea/"
    "master/src/main/resources/modules/covid19/patients.csv"
)


def _default_fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
        return response.read()


def download_synthea_sample(
    *,
    dest_dir: Path,
    filename: str = "patients.csv",
    url: str = DEFAULT_SYNTHEA_SAMPLE_URL,
    fetch: Callable[[str], bytes] | None = None,
) -> Path:
    if not filename or Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise ValueError("filename must be a bare file name without path separators")
    if filename.startswith(".."):
        raise ValueError("filename must not contain path traversal")

    fetch_fn = fetch or _default_fetch
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_bytes(fetch_fn(url))
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest-dir",
        type=Path,
        default=Path("data/raw/synthea"),
        help="Directory under data/raw/ (gitignored)",
    )
    parser.add_argument("--filename", default="patients.csv")
    parser.add_argument("--url", default=DEFAULT_SYNTHEA_SAMPLE_URL)
    args = parser.parse_args(argv)
    path = download_synthea_sample(dest_dir=args.dest_dir, filename=args.filename, url=args.url)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
