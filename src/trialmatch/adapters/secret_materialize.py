"""Materialize Secret Manager payloads to local paths (Workload Identity / ADC).

Never logs secret contents. Unit tests inject ``access_secret``.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from trialmatch.config.settings import Settings

AccessSecretFn = Callable[[str, str], bytes]

_DEFAULT_KEY_PATH = "/tmp/trialmatch/snowflake-private-key.pem"
_DEFAULT_PASSPHRASE_PATH = "/tmp/trialmatch/snowflake-private-key.pwd"


def _default_access_secret(project_id: str, secret_id: str) -> bytes:
    try:
        from google.cloud import secretmanager
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "google-cloud-secret-manager is required to fetch Snowflake keys. "
            "Install with: pip install 'trialmatch[secrets]'"
        ) from exc

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data


def _write_private_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.chmod(path, 0o600)


def materialize_snowflake_secrets(
    settings: Settings,
    *,
    access_secret: AccessSecretFn | None = None,
) -> Settings:
    """Fetch Snowflake key (and optional passphrase) from Secret Manager if configured.

    If ``SNOWFLAKE_PRIVATE_KEY_PATH`` already points at an existing file, leave it.
    Returns a copy of settings with filesystem paths set for the connector.
    """
    updates: dict[str, str] = {}
    fetch = access_secret or _default_access_secret
    project = settings.gcp_project_id

    key_path = (settings.snowflake_private_key_path or "").strip()
    if key_path and Path(key_path).is_file():
        pass
    elif settings.snowflake_private_key_sm_id:
        dest = Path(key_path or _DEFAULT_KEY_PATH)
        payload = fetch(project, settings.snowflake_private_key_sm_id)
        if not payload.strip():
            raise RuntimeError(
                f"Secret Manager secret {settings.snowflake_private_key_sm_id!r} is empty"
            )
        _write_private_file(dest, payload)
        updates["snowflake_private_key_path"] = str(dest)

    passphrase = (settings.snowflake_private_key_passphrase or "").strip()
    if passphrase:
        pass
    elif settings.snowflake_private_key_passphrase_sm_id:
        dest = Path(_DEFAULT_PASSPHRASE_PATH)
        payload = fetch(project, settings.snowflake_private_key_passphrase_sm_id)
        text = payload.decode("utf-8").strip()
        if text:
            _write_private_file(dest, text.encode("utf-8"))
            updates["snowflake_private_key_passphrase"] = text

    if not updates:
        return settings
    return settings.model_copy(update=updates)
