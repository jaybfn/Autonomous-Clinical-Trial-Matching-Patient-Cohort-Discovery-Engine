"""Thin HTTP client for TrialMatch FastAPI — matching stays on the backend."""

from __future__ import annotations

from typing import Any

import requests

DEFAULT_TIMEOUT_S = 180


class TrialMatchApiError(RuntimeError):
    """Raised when the TrialMatch API cannot be reached or returns a bad response."""


def healthz(base_url: str, *, timeout_s: float = 5.0) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/healthz"
    try:
        response = requests.get(url, timeout=timeout_s)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise TrialMatchApiError(f"Health check failed for {url}: {exc}") from exc


def match_patient(
    base_url: str,
    *,
    patient_id: str,
    note_text: str,
    correlation_id: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """POST /v1/match — returns MatchResponse JSON (including status=failed)."""
    url = f"{base_url.rstrip('/')}/v1/match"
    payload: dict[str, Any] = {
        "patient_id": patient_id.strip(),
        "note_text": note_text.strip(),
    }
    if correlation_id and correlation_id.strip():
        payload["correlation_id"] = correlation_id.strip()
    try:
        response = requests.post(url, json=payload, timeout=timeout_s)
    except requests.Timeout as exc:
        raise TrialMatchApiError(
            f"Match request timed out after {timeout_s:.0f}s — is the API tunnel up?"
        ) from exc
    except requests.RequestException as exc:
        raise TrialMatchApiError(f"Match request failed for {url}: {exc}") from exc

    if response.status_code == 422:
        detail = response.text
        raise TrialMatchApiError(f"Validation error (422): {detail}")
    if response.status_code >= 400:
        raise TrialMatchApiError(f"API HTTP {response.status_code}: {response.text[:500]}")
    try:
        return response.json()
    except ValueError as exc:
        raise TrialMatchApiError("API returned non-JSON body") from exc
