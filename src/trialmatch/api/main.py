"""FastAPI application factory for the trial-match API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from trialmatch.api.deps import get_settings
from trialmatch.api.routes import health, match
from trialmatch.config.settings import Settings
from trialmatch.observability.logging import configure_logging, get_logger
from trialmatch.observability.tracing import configure_tracing
from trialmatch.orchestrator.graph import GraphRunner

logger = get_logger(__name__)


def create_app(
    *,
    settings: Settings | None = None,
    graph_runner: GraphRunner | None = None,
    configure_observability: bool = True,
    wire_live_graph: bool = False,
) -> FastAPI:
    """Create the API app.

    Pass ``graph_runner`` in tests. Set ``wire_live_graph=True`` for production
    so startup builds Snowflake/Qdrant/LLM-backed agents from settings.
    """
    resolved = settings
    if resolved is None and wire_live_graph:
        resolved = get_settings()
    elif resolved is None:
        try:
            resolved = get_settings()
        except Exception:  # noqa: BLE001 — allow health tests without full env
            resolved = None

    if configure_observability and resolved is not None:
        configure_logging(resolved.log_level)
        configure_tracing(
            service_name=resolved.otel_service_name or "trialmatch-api",
            otlp_endpoint=resolved.otel_exporter_otlp_endpoint or None,
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if wire_live_graph and app.state.graph_runner is None:
            if app.state.settings is None:
                raise RuntimeError("Cannot wire live graph without settings")
            from trialmatch.adapters.secret_materialize import materialize_snowflake_secrets
            from trialmatch.api.factory import build_default_graph_runner

            app.state.settings = materialize_snowflake_secrets(app.state.settings)
            app.state.graph_runner = build_default_graph_runner(app.state.settings)
            logger.info("startup: live graph_runner ready")
        yield

    app = FastAPI(
        title="TrialMatch API",
        version="0.1.0",
        description="Autonomous clinical trial matching orchestrator",
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.graph_runner = graph_runner

    @app.get("/", tags=["health"])
    def root() -> dict[str, object]:
        """Browser-friendly index — the API has no HTML home page."""
        return {
            "service": "trialmatch-api",
            "status": "ok",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "endpoints": {
                "healthz": "GET /healthz",
                "readyz": "GET /readyz",
                "match": "POST /v1/match",
            },
        }

    app.include_router(health.router)
    app.include_router(match.router)
    return app


def create_live_app() -> FastAPI:
    """ASGI factory for uvicorn / containers (Workload Identity + live adapters)."""
    return create_app(wire_live_graph=True, configure_observability=True)


# Import-safe app for tooling; does not connect to Snowflake/Qdrant/LLM.
app = create_app(configure_observability=False, wire_live_graph=False)
