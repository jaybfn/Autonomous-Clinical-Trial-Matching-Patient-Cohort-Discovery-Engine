"""TDD contracts for PHI-safe OpenTelemetry tracing facade."""

from __future__ import annotations

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from trialmatch.observability.tracing import (
    ALLOWED_SPAN_ATTRIBUTES,
    configure_tracing,
    get_tracer,
    sanitize_span_attributes,
    start_span,
)


def test_sanitize_span_attributes_allowlist_only() -> None:
    cleaned = sanitize_span_attributes(
        {
            "correlation_id": "corr-1",
            "event_type": "clinical_record",
            "agent_name": "compliance",
            "nct_id": "NCT01234567",
            "status": "ok",
            "gcp.project_id": "autonomous-agent-503517",
            "ssn": "078-05-1120",
            "mrn": "1234567",
            "email": "jane@example.com",
            "phone": "617-555-0100",
            "text": "raw clinical note",
            "unknown_field": "drop-me",
        }
    )
    assert cleaned == {
        "correlation_id": "corr-1",
        "event_type": "clinical_record",
        "agent_name": "compliance",
        "nct_id": "NCT01234567",
        "status": "ok",
        "gcp.project_id": "autonomous-agent-503517",
    }
    assert "ssn" not in cleaned
    assert "text" not in cleaned
    assert "correlation_id" in ALLOWED_SPAN_ATTRIBUTES


def test_start_span_records_sanitized_attributes() -> None:
    exporter = InMemorySpanExporter()
    configure_tracing(service_name="trialmatch-test", memory_exporter=exporter, force=True)

    with start_span(
        "agent.compliance",
        attributes={
            "correlation_id": "corr-9",
            "agent_name": "compliance",
            "ssn": "078-05-1120",
            "text": "should not appear",
        },
    ):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "agent.compliance"
    attrs = dict(span.attributes or {})
    assert attrs["correlation_id"] == "corr-9"
    assert attrs["agent_name"] == "compliance"
    assert "ssn" not in attrs
    assert "text" not in attrs
    assert "078-05-1120" not in str(attrs)


def test_configure_tracing_without_otlp_endpoint_does_not_crash() -> None:
    exporter = InMemorySpanExporter()
    provider = configure_tracing(
        service_name="trialmatch",
        otlp_endpoint="",
        memory_exporter=exporter,
        force=True,
    )
    assert provider is not None
    tracer = get_tracer()
    with tracer.start_as_current_span("noop"):
        pass
    assert len(exporter.get_finished_spans()) >= 1
