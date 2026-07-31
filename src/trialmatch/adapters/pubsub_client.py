"""Pub/Sub publisher/subscriber adapters via ADC (no API keys)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol

from trialmatch.config.settings import Settings


class PubSubMessage(Protocol):
    message_id: str
    data: bytes
    attributes: dict[str, str]

    def ack(self) -> None: ...

    def nack(self) -> None: ...


class PubSubPublisher:
    """Publish JSON dicts to a topic (short name or full resource path)."""

    def __init__(
        self,
        *,
        settings: Settings,
        client: Any | None = None,
    ) -> None:
        self.settings = settings
        self._client = client

    def _client_or_default(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from google.cloud import pubsub_v1  # type: ignore[attr-defined]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "google-cloud-pubsub is required. Install with: pip install 'trialmatch[pubsub]'"
            ) from exc
        self._client = pubsub_v1.PublisherClient()
        return self._client

    def topic_path(self, topic: str) -> str:
        if topic.startswith("projects/"):
            return topic
        return f"projects/{self.settings.gcp_project_id}/topics/{topic}"

    def publish(self, topic: str, message: dict[str, Any]) -> str:
        client = self._client_or_default()
        data = json.dumps(message, separators=(",", ":")).encode("utf-8")
        path = self.topic_path(topic)
        future = client.publish(path, data)
        return str(future.result())


class PubSubSubscriber:
    """Streaming-pull subscriber that delegates each message to a callback."""

    def __init__(
        self,
        *,
        settings: Settings,
        client: Any | None = None,
    ) -> None:
        self.settings = settings
        self._client = client

    def _client_or_default(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from google.cloud import pubsub_v1  # type: ignore[attr-defined]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "google-cloud-pubsub is required. Install with: pip install 'trialmatch[pubsub]'"
            ) from exc
        self._client = pubsub_v1.SubscriberClient()
        return self._client

    def subscription_path(self, subscription: str) -> str:
        if subscription.startswith("projects/"):
            return subscription
        return f"projects/{self.settings.gcp_project_id}/subscriptions/{subscription}"

    def run(
        self,
        *,
        subscription: str,
        callback: Callable[[Any], None],
        timeout: float | None = None,
    ) -> None:
        """Block on streaming pull. ``timeout`` is for tests; None = run forever."""
        client = self._client_or_default()
        path = self.subscription_path(subscription)
        future = client.subscribe(path, callback=callback)
        try:
            future.result(timeout=timeout)
        except Exception:  # noqa: BLE001
            future.cancel()
            raise
