"""LLM clients for Parser — Ollama (local) or Vertex (ADC). No API keys."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Protocol
from urllib.parse import urljoin

from trialmatch.config.settings import Settings

CompleterFn = Callable[..., str]
TransportFn = Callable[[str, dict], dict]


class LlmClient(Protocol):
    def complete_json(self, *, system: str, user: str) -> str: ...


class VertexLlmClient:
    """Thin Vertex wrapper; inject ``completer`` in unit tests."""

    def __init__(
        self,
        *,
        settings: Settings,
        completer: CompleterFn | None = None,
    ) -> None:
        self.settings = settings
        self.model = settings.vertex_llm_model
        self.location = settings.vertex_llm_location
        self._completer = completer

    def complete_json(self, *, system: str, user: str) -> str:
        completer = self._completer or _default_vertex_completer(self.settings)
        return completer(
            system=system,
            user=user,
            model=self.model,
            location=self.location,
        )


class OllamaLlmClient:
    """Ollama native ``/api/chat`` client — local/self-hosted, $0 token fees."""

    def __init__(
        self,
        *,
        settings: Settings,
        transport: TransportFn | None = None,
    ) -> None:
        self.settings = settings
        self.model = settings.ollama_llm_model
        self.base_url = settings.ollama_base_url.rstrip("/") + "/"
        self._transport = transport

    def complete_json(self, *, system: str, user: str) -> str:
        url = urljoin(self.base_url, "api/chat")
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0},
            "messages": [
                {"role": "system", "content": system.strip()},
                {"role": "user", "content": user.strip()},
            ],
        }
        transport = self._transport or _default_http_json_transport
        response = transport(url, payload)
        message = response.get("message") if isinstance(response, dict) else None
        if not isinstance(message, dict):
            raise RuntimeError("Ollama returned malformed chat response")
        text = message.get("content")
        if not text or not str(text).strip():
            raise RuntimeError("Ollama returned empty response")
        return str(text)


def build_llm_client(
    settings: Settings,
    *,
    completer: CompleterFn | None = None,
    transport: TransportFn | None = None,
) -> LlmClient:
    """Factory: ``LLM_PROVIDER=ollama|vertex``."""
    provider = (settings.llm_provider or "").strip().lower()
    if provider == "ollama":
        return OllamaLlmClient(settings=settings, transport=transport)
    if provider == "vertex":
        return VertexLlmClient(settings=settings, completer=completer)
    raise ValueError(
        f"Unsupported LLM_PROVIDER={settings.llm_provider!r}; expected 'ollama' or 'vertex'"
    )


def _default_http_json_transport(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ollama returned non-JSON body: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Ollama JSON must be an object")
    return parsed


def _default_vertex_completer(settings: Settings) -> CompleterFn:
    try:
        import vertexai
        from vertexai.generative_models import GenerationConfig, GenerativeModel
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "google-cloud-aiplatform is required for Vertex LLM. "
            "Install with: pip install 'trialmatch[vertex]'"
        ) from exc

    vertexai.init(project=settings.gcp_project_id, location=settings.vertex_llm_location)
    generative_model = GenerativeModel(settings.vertex_llm_model)

    def _complete(*, system: str, user: str, model: str, location: str) -> str:
        _ = (model, location)
        prompt = f"{system.strip()}\n\n{user.strip()}"
        response = generative_model.generate_content(
            prompt,
            generation_config=GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Vertex returned empty response")
        return text

    return _complete
