"""Append-only Snowflake audit sink — AUDIT_WRITE_ROLE only."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from typing import Any, Protocol

from trialmatch.domain.audit import AuditRecord

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REQUIRED_WRITE_ROLE = "AUDIT_WRITE_ROLE"


class AuditSinkError(RuntimeError):
    """Fail-closed sink errors (role, schema, or write failures)."""


class SnowflakeWriter(Protocol):
    role: str

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> None: ...


def build_match_id(*, correlation_id: str, nct_id: str, content_hash: str) -> str:
    """Deterministic MATCH_ID for append-only rows (stable across retries)."""
    material = f"{correlation_id.strip()}|{nct_id.strip().upper()}|{content_hash.strip()}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def build_insert_sql(*, schema: str = "AUDIT") -> str:
    if not _SAFE_IDENTIFIER.match(schema):
        raise AuditSinkError(f"Unsafe Snowflake schema identifier: {schema!r}")
    return (
        f"INSERT INTO {schema}.AUDIT_MATCH_JUSTIFICATIONS "
        f"(MATCH_ID, PATIENT_ID, NCT_ID, JUSTIFICATION, AGENT_NAME, CORRELATION_ID) "
        f"VALUES (%s, %s, %s, %s, %s, %s)"
    )


class AuditSink:
    """Writes one audit row per matched NCT under AUDIT_WRITE_ROLE."""

    def __init__(
        self,
        *,
        client: SnowflakeWriter,
        schema: str = "AUDIT",
        agent_name: str = "auditor",
    ) -> None:
        self._client = client
        self._schema = schema
        self._agent_name = agent_name

    def append(self, record: AuditRecord) -> list[str]:
        role = getattr(self._client, "role", "") or ""
        if role != _REQUIRED_WRITE_ROLE:
            raise AuditSinkError(f"Audit sink requires role {_REQUIRED_WRITE_ROLE}, got {role!r}")
        try:
            sql = build_insert_sql(schema=self._schema)
        except AuditSinkError:
            raise
        except Exception as exc:  # pragma: no cover
            raise AuditSinkError(str(exc)) from exc

        match_ids: list[str] = []
        ncts = list(record.matched_nct_ids) or [""]
        # Always persist at least the summary row when there are zero matches.
        for nct_id in ncts:
            match_id = build_match_id(
                correlation_id=record.correlation_id,
                nct_id=nct_id or "_NONE_",
                content_hash=record.content_hash,
            )
            justification = record.justification_summary
            if nct_id:
                # Prefer a focused line when multiple NCTs were matched.
                justification = (
                    f"{record.justification_summary} [nct_id={nct_id}]"
                    if len(record.matched_nct_ids) > 1
                    else record.justification_summary
                )
            params = (
                match_id,
                record.patient_id,
                nct_id or None,
                justification,
                self._agent_name,
                record.correlation_id,
            )
            try:
                self._client.execute(sql, params)
            except Exception as exc:  # noqa: BLE001
                raise AuditSinkError(f"Audit insert failed: {exc}") from exc
            match_ids.append(match_id)
        return match_ids
