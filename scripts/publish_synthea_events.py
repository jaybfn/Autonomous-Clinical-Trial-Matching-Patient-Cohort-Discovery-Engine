"""Publish Synthea-mapped clinical/lab events to Pub/Sub (publisher injected)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Protocol

from trialmatch.data.synthea_mapper import (
    map_lab_row,
    map_note_record,
    read_clinical_notes_jsonl,
    read_synthea_csv,
)


class EventPublisher(Protocol):
    def publish(self, topic: str, message: dict) -> str: ...


def publish_synthea_events(
    *,
    sample_dir: Path,
    publisher: EventPublisher,
    clinical_topic: str = "clinical-records",
    lab_topic: str = "lab-updates",
    dry_run: bool = False,
) -> dict[str, int]:
    clinical_count = 0
    lab_count = 0

    notes_path = sample_dir / "clinical_notes.jsonl"
    if notes_path.is_file():
        for note in read_clinical_notes_jsonl(notes_path):
            event = map_note_record(note)
            if not dry_run:
                publisher.publish(clinical_topic, event)
            clinical_count += 1

    labs_path = sample_dir / "labs.csv"
    if labs_path.is_file():
        for row in read_synthea_csv(labs_path):
            event = map_lab_row(row)
            if not dry_run:
                publisher.publish(lab_topic, event)
            lab_count += 1

    return {"clinical_records": clinical_count, "lab_updates": lab_count}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-dir", type=Path, default=Path("data/synthea/samples"))
    parser.add_argument("--clinical-topic", default="clinical-records")
    parser.add_argument("--lab-topic", default="lab-updates")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    class _NoopPublisher:
        def publish(self, topic: str, message: dict) -> str:
            raise RuntimeError("Live Pub/Sub publish requires ADC client (Phase 12)")

    # CLI always dry-runs until Phase 12 ADC publisher is available.
    summary = publish_synthea_events(
        sample_dir=args.sample_dir,
        publisher=_NoopPublisher(),
        clinical_topic=args.clinical_topic,
        lab_topic=args.lab_topic,
        dry_run=True,
    )
    print("Dry-run only until ADC Pub/Sub publisher is wired (Phase 12).")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
