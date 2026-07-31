"""Pub/Sub streaming subscriber loop → IngestionHandler → ack/nack."""

from __future__ import annotations

import argparse
from typing import Any

from trialmatch.adapters.pubsub_client import PubSubPublisher, PubSubSubscriber
from trialmatch.api.factory import build_default_graph_runner
from trialmatch.config.settings import Settings
from trialmatch.ingestion.dlq import DeadLetterPublisher
from trialmatch.ingestion.handlers import HandleDisposition, IngestionHandler
from trialmatch.observability.logging import configure_logging, get_logger, sanitize_log_extra
from trialmatch.observability.tracing import configure_tracing

logger = get_logger(__name__)


def on_pubsub_message(handler: IngestionHandler, *, subscription: str, message: Any) -> None:
    """Callback compatible with google.cloud.pubsub_v1 subscriber messages."""
    attributes = dict(getattr(message, "attributes", None) or {})
    result = handler.handle(
        data=bytes(message.data),
        message_id=str(getattr(message, "message_id", "") or ""),
        attributes={str(k): str(v) for k, v in attributes.items()},
        subscription=subscription,
    )
    if result.disposition == HandleDisposition.ACK:
        message.ack()
    else:
        message.nack()
    logger.info(
        "ingestion.message_done",
        extra=sanitize_log_extra(
            {
                "correlation_id": result.correlation_id,
                "status": result.status,
                "event_type": subscription,
            }
        ),
    )


def build_handler(settings: Settings, *, dlq_topic: str) -> IngestionHandler:
    publisher = PubSubPublisher(settings=settings)
    return IngestionHandler(
        runner=build_default_graph_runner(settings),
        dlq=DeadLetterPublisher(publisher=publisher, topic=dlq_topic),
    )


def run_subscriber(
    *,
    settings: Settings,
    subscription: str,
    dlq_topic: str,
    timeout: float | None = None,
    handler: IngestionHandler | None = None,
    subscriber: PubSubSubscriber | None = None,
) -> None:
    resolved_handler = handler or build_handler(settings, dlq_topic=dlq_topic)
    client = subscriber or PubSubSubscriber(settings=settings)

    def _callback(message: Any) -> None:
        on_pubsub_message(resolved_handler, subscription=subscription, message=message)

    logger.info(
        "ingestion.subscriber_start",
        extra=sanitize_log_extra({"status": "ok", "event_type": subscription}),
    )
    client.run(subscription=subscription, callback=_callback, timeout=timeout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TrialMatch Pub/Sub ingestion worker")
    parser.add_argument(
        "--subscription",
        default=None,
        help="Subscription id (default: PUBSUB_CLINICAL_SUBSCRIPTION)",
    )
    parser.add_argument(
        "--dlq-topic",
        default=None,
        help="DLQ topic id (default: PUBSUB_CLINICAL_DLQ_TOPIC)",
    )
    args = parser.parse_args(argv)

    settings = Settings()
    configure_logging(settings.log_level)
    configure_tracing(
        service_name=settings.otel_service_name or "trialmatch-ingestion",
        otlp_endpoint=settings.otel_exporter_otlp_endpoint or None,
    )
    subscription = (args.subscription or settings.pubsub_clinical_subscription).strip()
    dlq_topic = (args.dlq_topic or settings.pubsub_clinical_dlq_topic).strip()
    run_subscriber(settings=settings, subscription=subscription, dlq_topic=dlq_topic)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
