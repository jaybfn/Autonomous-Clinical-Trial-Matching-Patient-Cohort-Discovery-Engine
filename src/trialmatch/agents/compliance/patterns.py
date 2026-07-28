"""Regex PHI detectors for the Compliance agent."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PhiSpan:
    entity_type: str
    start: int
    end: int
    text: str


# Order matters when resolving overlaps — prefer more specific / longer matches later via merge.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "ssn",
        re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
    ),
    (
        "phone",
        re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"),
    ),
    (
        "mrn",
        re.compile(r"\bMRN[:\s#]*([0-9]{5,10})\b", re.IGNORECASE),
    ),
    (
        "dob",
        re.compile(
            r"\b(?:DOB|D\.O\.B\.|date of birth)[:\s]*"
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
            re.IGNORECASE,
        ),
    ),
    (
        "address",
        re.compile(
            r"\b\d{1,5}\s+[A-Za-z0-9.'\-]+\s+"
            r"(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Lane|Ln|Dr|Drive)\b"
            r"(?:,?\s*[A-Za-z .]+)?",
            re.IGNORECASE,
        ),
    ),
]


def find_phi_spans(text: str) -> list[PhiSpan]:
    """Return non-overlapping PHI spans (earlier/longer wins on conflicts)."""
    candidates: list[PhiSpan] = []
    for entity_type, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            # Prefer capture group content when present (MRN/DOB label wrappers).
            if match.lastindex:
                start, end = match.start(1), match.end(1)
                value = match.group(1)
            else:
                start, end = match.start(), match.end()
                value = match.group(0)
            candidates.append(PhiSpan(entity_type=entity_type, start=start, end=end, text=value))

    candidates.sort(key=lambda s: (s.start, -(s.end - s.start)))
    selected: list[PhiSpan] = []
    occupied_until = -1
    for span in candidates:
        if span.start < occupied_until:
            continue
        selected.append(span)
        occupied_until = span.end
    return selected
