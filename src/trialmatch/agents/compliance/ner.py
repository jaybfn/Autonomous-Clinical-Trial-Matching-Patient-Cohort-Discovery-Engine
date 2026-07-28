"""Pluggable NER backends for person / org style PHI."""

from __future__ import annotations

import re
from typing import Protocol

from trialmatch.agents.compliance.patterns import PhiSpan


class NerBackend(Protocol):
    def find_entities(self, text: str) -> list[PhiSpan]: ...


class NullNer:
    """No-op NER (regex-only compliance)."""

    def find_entities(self, text: str) -> list[PhiSpan]:
        _ = text
        return []


class RuleBasedPersonNer:
    """Lightweight person detector for synthetic notes (swap for spaCy/medspaCy later)."""

    _PATTERNS = (
        re.compile(
            r"\bPatient\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
        ),
        re.compile(
            r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:MRN|SSN|presents|seen for)\b",
        ),
    )

    def find_entities(self, text: str) -> list[PhiSpan]:
        spans: list[PhiSpan] = []
        for pattern in self._PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.start(1), match.end(1)
                spans.append(
                    PhiSpan(
                        entity_type="person",
                        start=start,
                        end=end,
                        text=match.group(1),
                    )
                )
        return spans
