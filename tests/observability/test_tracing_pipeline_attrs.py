"""Extra tracing contracts: orchestrator span names stay PHI-safe."""

from __future__ import annotations

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from trialmatch.observability.tracing import (
    ALLOWED_SPAN_ATTRIBUTES,
    configure_tracing,
    start_span,
)


def test_allowed_span_attribute_set_is_frozen_and_minimal() -> None:
    # Keep the allowlist tight — expanding it is a security review item.
    assert ALLOWED_SPAN_ATTRIBUTES == frozenset(
        {
            "correlation_id",
            "event_type",
            "agent_name",
            "nct_id",
            "status",
            "gcp.project_id",
        }
    )


def test_orchestrator_style_spans_drop_note_fields() -> None:
    exporter = InMemorySpanExporter()
    configure_tracing(service_name="trialmatch-obs", memory_exporter=exporter, force=True)
    with start_span(
        "orchestrator.parser",
        {
            "correlation_id": "c1",
            "agent_name": "parser",
            "note_text": "PHI note",
            "scrubbed_text": "still sensitive",
            "status": "ok",
        },
    ):
        pass
    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert attrs["agent_name"] == "parser"
    assert "note_text" not in attrs
    assert "scrubbed_text" not in attrs
    assert "PHI" not in str(attrs)
