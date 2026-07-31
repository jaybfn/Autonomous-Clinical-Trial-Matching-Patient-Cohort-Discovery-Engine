"""Dead-letter publishing for poison Pub/Sub messages (no raw note bodies)."""

from __future__ import annotations

import json
from typing import Any, Protocol


class DeadLetterError(RuntimeError):
    """DLQ configuration or publish failure."""


class MessagePublisher(Protocol):
    def publish(self, topic: str, message: dict[str, Any]) -> str: ...


_POISON_TYPES = (ValueError, TypeError, KeyError, json.JSONDecodeError)


def is_poison_error(exc: BaseException) -> bool:
    """Permanent decode/validation errors → DLQ; timeouts/runtime → retry/nack."""
    return isinstance(exc, _POISON_TYPES)


class DeadLetterPublisher:
    def __init__(self, *, publisher: MessagePublisher, topic: str) -> None:
        cleaned = (topic or "").strip()
        if not cleaned:
            raise DeadLetterError("DLQ topic must not be blank")
        self._publisher = publisher
        self._topic = cleaned

    def publish_poison(
        self,
        *,
        original_data: bytes,
        reason: str,
        correlation_id: str,
        subscription: str,
        attributes: dict[str, str] | None = None,
    ) -> str:
        payload_keys: list[str] = []
        try:
            parsed = json.loads(original_data.decode("utf-8"))
            if isinstance(parsed, dict):
                payload = parsed.get("payload")
                if isinstance(payload, dict):
                    payload_keys = sorted(str(k) for k in payload if k not in {"text", "note_text"})
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, AttributeError):
            payload_keys = []

        envelope = {
            "reason": reason,
            "correlation_id": correlation_id,
            "subscription": subscription,
            "attributes": dict(attributes or {}),
            "original_byte_length": len(original_data),
            "payload_keys": payload_keys,
            # Intentionally omit original body / note text (PHI-safe DLQ).
        }
        return self._publisher.publish(self._topic, envelope)
