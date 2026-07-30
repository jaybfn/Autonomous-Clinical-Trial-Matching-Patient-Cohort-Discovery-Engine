"""TDD contracts for LLM adapters (Vertex + Ollama; no paid API keys)."""

from __future__ import annotations

from pathlib import Path

import pytest

from trialmatch.adapters.llm_client import (
    OllamaLlmClient,
    VertexLlmClient,
    build_llm_client,
)
from trialmatch.config.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("GCP_PROJECT_ID", "autonomous-agent-503517")
    monkeypatch.setenv("VERTEX_LLM_MODEL", "gemini-2.0-flash-001")
    monkeypatch.setenv("VERTEX_LLM_LOCATION", "us-central1")
    monkeypatch.setenv("LLM_PROVIDER", "vertex")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_LLM_MODEL", "llama3.1:8b")
    return Settings(_env_file=None)


def test_vertex_client_uses_injected_completer(settings: Settings) -> None:
    def _fake(*, system: str, user: str, model: str, location: str) -> str:
        assert model == "gemini-2.0-flash-001"
        assert location == "us-central1"
        assert system
        assert user
        return '{"conditions":[],"labs":[],"medications":[],"note_summary":"ok"}'

    client = VertexLlmClient(settings=settings, completer=_fake)
    text = client.complete_json(system="sys", user="usr")
    assert "note_summary" in text


def test_ollama_client_posts_chat_with_json_format(settings: Settings) -> None:
    calls: list[tuple[str, dict]] = []

    def _transport(url: str, payload: dict) -> dict:
        calls.append((url, payload))
        assert url == "http://localhost:11434/api/chat"
        assert payload["model"] == "llama3.1:8b"
        assert payload["stream"] is False
        assert payload["format"] == "json"
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        return {
            "message": {
                "role": "assistant",
                "content": (
                    '{"conditions":["Diabetes"],"labs":[],"medications":[],"note_summary":"ok"}'
                ),
            }
        }

    client = OllamaLlmClient(settings=settings, transport=_transport)
    text = client.complete_json(system="sys", user="scrubbed note")
    assert "Diabetes" in text
    assert len(calls) == 1


def test_ollama_client_fails_on_empty_message(settings: Settings) -> None:
    def _transport(url: str, payload: dict) -> dict:
        _ = (url, payload)
        return {"message": {"role": "assistant", "content": ""}}

    client = OllamaLlmClient(settings=settings, transport=_transport)
    with pytest.raises(RuntimeError, match="empty"):
        client.complete_json(system="sys", user="usr")


def test_build_llm_client_selects_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "autonomous-agent-503517")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_LLM_MODEL", "qwen2.5:14b")
    settings = Settings(_env_file=None)
    client = build_llm_client(settings)
    assert isinstance(client, OllamaLlmClient)
    assert client.model == "qwen2.5:14b"


def test_build_llm_client_selects_vertex(settings: Settings) -> None:
    client = build_llm_client(settings)
    assert isinstance(client, VertexLlmClient)


def test_build_llm_client_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "autonomous-agent-503517")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    settings = Settings(_env_file=None)
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        build_llm_client(settings)


def test_llm_source_has_no_api_key_literals() -> None:
    source = (REPO_ROOT / "src" / "trialmatch" / "adapters" / "llm_client.py").read_text(
        encoding="utf-8"
    )
    lowered = source.lower()
    assert "api_key=" not in lowered
    assert "api-key" not in lowered
    assert "sk-" not in source
    # Prefer Ollama native HTTP over OpenAI SDK / paid OpenAI cloud.
    assert "from openai" not in lowered
    assert "import openai" not in lowered


def test_settings_llm_provider_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "proj")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_LLM_MODEL", raising=False)
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "ollama"
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_llm_model == "llama3.1:8b"
