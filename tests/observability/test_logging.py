"""TDD contracts for structured logging without PHI leakage."""

from __future__ import annotations

import logging

import pytest

from trialmatch.observability.logging import (
    FORBIDDEN_LOG_FIELDS,
    configure_logging,
    get_logger,
    sanitize_log_extra,
)


def test_sanitize_removes_forbidden_phi_fields() -> None:
    cleaned = sanitize_log_extra(
        {
            "patient_id": "p-001",
            "ssn": "078-05-1120",
            "mrn": "1234567",
            "email": "jane@example.com",
            "correlation_id": "corr-1",
        }
    )
    assert cleaned["patient_id"] == "p-001"
    assert cleaned["correlation_id"] == "corr-1"
    assert "ssn" not in cleaned
    assert "mrn" not in cleaned
    assert "email" not in cleaned
    assert "ssn" in FORBIDDEN_LOG_FIELDS


def test_logger_extra_is_sanitized(caplog: pytest.LogCaptureFixture) -> None:
    configure_logging(level="INFO")
    logger = get_logger("trialmatch.test")
    with caplog.at_level(logging.INFO):
        logger.info(
            "processing",
            extra=sanitize_log_extra({"patient_id": "p-001", "phone": "617-555-0100"}),
        )
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert getattr(record, "patient_id", None) == "p-001"
    assert not hasattr(record, "phone")
    assert "617-555-0100" not in caplog.text
    assert "617-555-0100" not in str(record.__dict__)
