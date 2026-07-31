"""Snowflake adapter — keypair / env config only; no hardcoded secrets.

Unit tests inject a fake ``connect`` / connection. Live use may install
``snowflake-connector-python`` (optional extra ``[snowflake]``).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol

from trialmatch.config.settings import Settings


class _Cursor(Protocol):
    description: Sequence[Sequence[Any]] | None

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> Any: ...

    def fetchall(self) -> Sequence[Sequence[Any]]: ...


class _Connection(Protocol):
    def cursor(self) -> Any: ...


ConnectFn = Callable[..., _Connection]


def _default_connect(**kwargs: Any) -> _Connection:
    try:
        import snowflake.connector  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - exercised when extra missing
        raise RuntimeError(
            "snowflake-connector-python is required for live connections. "
            "Install with: pip install 'trialmatch[snowflake]'"
        ) from exc
    return snowflake.connector.connect(**kwargs)


def _connection_kwargs(settings: Settings, role: str) -> dict[str, Any]:
    if not settings.snowflake_account or not settings.snowflake_user:
        raise ValueError("SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER are required")
    kwargs: dict[str, Any] = {
        "account": settings.snowflake_account,
        "user": settings.snowflake_user,
        "role": role,
        "warehouse": settings.snowflake_warehouse or None,
        "database": settings.snowflake_database or None,
        "schema": settings.snowflake_schema or None,
    }
    if settings.snowflake_private_key_path:
        kwargs["private_key_file"] = settings.snowflake_private_key_path
    if settings.snowflake_private_key_passphrase:
        kwargs["private_key_file_pwd"] = settings.snowflake_private_key_passphrase
    return {k: v for k, v in kwargs.items() if v is not None}


class SnowflakeClient:
    """Thin wrapper that always runs under an explicit Snowflake role."""

    def __init__(
        self,
        *,
        settings: Settings,
        role: str,
        connection: _Connection | None = None,
        connect: ConnectFn | None = None,
    ) -> None:
        self.settings = settings
        self.role = role
        if connection is not None:
            self.connection = connection
        else:
            connect_fn = connect or _default_connect
            self.connection = connect_fn(**_connection_kwargs(settings, role))

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> None:
        with self.connection.cursor() as cur:
            cur.execute(sql, params)

    def fetch_all(self, sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
        with self.connection.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            columns = [col[0] for col in (cur.description or [])]
        return [dict(zip(columns, row, strict=False)) for row in rows]


def agent_read_client(
    settings: Settings,
    *,
    connect: ConnectFn | None = None,
    connection: _Connection | None = None,
) -> SnowflakeClient:
    return SnowflakeClient(
        settings=settings,
        role=settings.agent_read_role,
        connect=connect,
        connection=connection,
    )


def audit_write_client(
    settings: Settings,
    *,
    connect: ConnectFn | None = None,
    connection: _Connection | None = None,
) -> SnowflakeClient:
    return SnowflakeClient(
        settings=settings,
        role=settings.audit_write_role,
        connect=connect,
        connection=connection,
    )
