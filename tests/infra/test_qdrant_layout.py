"""Phase 6 layout contracts: Qdrant k8s manifests + disk module."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_qdrant_k8s_manifests_exist() -> None:
    base = REPO_ROOT / "k8s" / "qdrant"
    assert (base / "deployment.yaml").is_file()
    assert (base / "service.yaml").is_file()
    deploy = (base / "deployment.yaml").read_text(encoding="utf-8")
    svc = (base / "service.yaml").read_text(encoding="utf-8")
    assert "kind: StatefulSet" in deploy or "kind: Deployment" in deploy
    assert "qdrant" in deploy.lower()
    assert "qdrant/qdrant:v1.18" in deploy or "qdrant/qdrant:v1.18.0" in deploy
    assert "kind: Service" in svc
    assert "6333" in svc


def test_qdrant_disk_terraform_module_exists() -> None:
    module = REPO_ROOT / "infra" / "terraform" / "modules" / "qdrant_disk"
    assert (module / "main.tf").is_file()
    assert (module / "variables.tf").is_file()
    assert (module / "outputs.tf").is_file()
    main = (module / "main.tf").read_text(encoding="utf-8")
    assert "google_compute_disk" in main or "persistent" in main.lower()
