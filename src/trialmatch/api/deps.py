"""FastAPI dependencies — override in tests; no process-global clients."""

from __future__ import annotations

import hmac
from functools import lru_cache
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from trialmatch.config.settings import Settings
from trialmatch.orchestrator.graph import GraphRunner


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _resolve_settings(request: Request) -> Settings | None:
    attached = getattr(request.app.state, "settings", None)
    if attached is not None:
        return attached  # type: ignore[no-any-return]
    try:
        return get_settings()
    except Exception:  # noqa: BLE001 — settings may be incomplete in unit tests
        return None


def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Enforce ``X-API-Key`` when ``TRIALMATCH_API_KEY`` is configured.

    Empty configured key leaves auth disabled (local demos / tests).
    """
    settings = _resolve_settings(request)
    expected = (getattr(settings, "trialmatch_api_key", None) or "").strip()
    if not expected:
        return
    provided = (x_api_key or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def get_graph_runner(request: Request) -> GraphRunner:
    """Resolve the graph runner attached at app startup (`app.state.graph_runner`)."""
    runner = getattr(request.app.state, "graph_runner", None)
    if runner is None:
        raise RuntimeError("graph_runner is not configured on the application")
    return runner
