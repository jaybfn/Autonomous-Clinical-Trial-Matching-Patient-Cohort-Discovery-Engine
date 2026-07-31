"""FastAPI dependencies — override in tests; no process-global clients."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Request

from trialmatch.config.settings import Settings
from trialmatch.orchestrator.graph import GraphRunner


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_graph_runner(request: Request) -> GraphRunner:
    """Resolve the graph runner attached at app startup (`app.state.graph_runner`)."""
    runner = getattr(request.app.state, "graph_runner", None)
    if runner is None:
        raise RuntimeError("graph_runner is not configured on the application")
    return runner
