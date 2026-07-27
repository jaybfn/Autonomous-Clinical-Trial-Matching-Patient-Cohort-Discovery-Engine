"""OpenTelemetry tracing facade with PHI-safe span attributes."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Span, Tracer

ALLOWED_SPAN_ATTRIBUTES = frozenset(
    {
        "correlation_id",
        "event_type",
        "agent_name",
        "nct_id",
        "status",
        "gcp.project_id",
    }
)

_TRACER_NAME = "trialmatch"


def sanitize_span_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """Keep only allowlisted span attributes (never PHI / free-text clinical content)."""
    return {
        key: value
        for key, value in attributes.items()
        if key in ALLOWED_SPAN_ATTRIBUTES and value is not None
    }


def reset_tracer_provider() -> None:
    """Allow re-configuring the global provider (needed for isolated unit tests)."""
    # OpenTelemetry allows set_tracer_provider only once unless reset.
    from opentelemetry.util._once import Once

    trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
    trace._TRACER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]


def configure_tracing(
    *,
    service_name: str = "trialmatch",
    otlp_endpoint: Optional[str] = None,
    memory_exporter: Optional[InMemorySpanExporter] = None,
    force: bool = False,
) -> TracerProvider:
    """
    Configure the global TracerProvider.

    Empty/missing ``otlp_endpoint`` skips OTLP export (safe default for unit tests / local).
    Pass ``memory_exporter`` for in-process assertions in tests.
    Set ``force=True`` to replace an existing provider (tests only).
    """
    if force:
        reset_tracer_provider()

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if memory_exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(memory_exporter))

    endpoint = (otlp_endpoint or "").strip()
    if endpoint:
        # Lazy import so unit tests without a collector never require a live exporter path.
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))

    trace.set_tracer_provider(provider)
    return provider


def get_tracer(name: str = _TRACER_NAME) -> Tracer:
    return trace.get_tracer(name)


@contextmanager
def start_span(name: str, attributes: Optional[dict[str, Any]] = None) -> Iterator[Span]:
    """Start a span with sanitized attributes."""
    tracer = get_tracer()
    cleaned = sanitize_span_attributes(attributes or {})
    with tracer.start_as_current_span(name, attributes=cleaned) as span:
        yield span
