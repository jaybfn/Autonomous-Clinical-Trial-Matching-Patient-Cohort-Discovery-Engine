"""Clinician-readable justification narratives from Matcher evidence."""

from __future__ import annotations

from trialmatch.domain.trial import TrialMatch, TrialMatchResult


def normalize_redaction_tokens(redaction_map: dict[str, str]) -> dict[str, str]:
    """Keep token → entity_type maps only (never raw PHI values)."""
    normalized: dict[str, str] = {}
    for token, entity_type in redaction_map.items():
        key = (token or "").strip()
        value = (entity_type or "").strip().lower()
        if not key or not value:
            continue
        if "@" in value or any(ch.isdigit() for ch in value):
            raise ValueError("redaction token values must be entity types, not raw identifiers")
        normalized[key] = value
    return normalized


def build_per_match_justification(match: TrialMatch) -> str:
    evidence = match.evidence or {}
    title = str(evidence.get("title") or "").strip()
    condition_hits = [str(x) for x in (evidence.get("condition_hits") or []) if x]
    lab_hits = [str(x) for x in (evidence.get("lab_hits") or []) if x]
    vector_score = evidence.get("vector_score")

    parts = [f"Trial {match.nct_id}"]
    if title:
        parts[0] = f"Trial {match.nct_id} ({title})"
    parts.append(f"hybrid_score={match.score:.2f}")
    if vector_score is not None:
        try:
            parts.append(f"vector_score={float(vector_score):.2f}")
        except (TypeError, ValueError):
            pass
    if condition_hits:
        parts.append("condition_hits=" + ", ".join(condition_hits))
    if lab_hits:
        parts.append("lab_hits=" + ", ".join(lab_hits))
    return "; ".join(parts) + "."


def build_justification_summary(
    match_result: TrialMatchResult,
    *,
    max_matches: int = 5,
) -> str:
    matches = sorted(match_result.matches, key=lambda m: m.score, reverse=True)
    if not matches:
        return "No trials matched for this patient under current hybrid criteria."
    selected = matches[: max(1, max_matches)]
    lines = [
        f"Ranked {len(matches)} trial(s); showing top {len(selected)}.",
    ]
    for index, match in enumerate(selected, start=1):
        lines.append(f"{index}. {build_per_match_justification(match)}")
    return " ".join(lines)
