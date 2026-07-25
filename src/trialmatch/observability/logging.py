"""Structured logging helpers that refuse common PHI field names."""

from __future__ import annotations

import logging
from typing import Any

FORBIDDEN_LOG_FIELDS = frozenset(
    {
        "ssn",
        "mrn",
        "email",
        "phone",
        "address",
        "dob",
        "birthdate",
        "name",
        "full_name",
        "first_name",
        "last_name",
        "text",
        "raw_note",
        "note_text",
        "password",
        "secret",
        "token",
        "api_key",
    }
)


def sanitize_log_extra(extra: dict[str, Any]) -> dict[str, Any]:
    """Drop keys that commonly carry PHI or secrets before attaching to log records."""
    return {key: value for key, value in extra.items() if key.lower() not in FORBIDDEN_LOG_FIELDS}


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
    else:
        root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
