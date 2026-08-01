"""Contracts for in-cluster Ollama manifests (free open LLM)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = REPO_ROOT / "k8s" / "ollama"


def test_ollama_manifests_exist() -> None:
    assert (BASE / "deployment.yaml").is_file()
    assert (BASE / "service.yaml").is_file()


def test_ollama_serves_open_model() -> None:
    deploy = (BASE / "deployment.yaml").read_text(encoding="utf-8")
    svc = (BASE / "service.yaml").read_text(encoding="utf-8")
    assert "ollama/ollama" in deploy
    assert "llama3.2:1b" in deploy
    assert "11434" in deploy
    assert "kind: Service" in svc
    assert "11434" in svc
