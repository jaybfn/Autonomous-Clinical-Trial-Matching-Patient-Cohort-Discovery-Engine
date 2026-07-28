"""Phase 4 contract tests: Pub/Sub, Ingress, Secret Manager (no terraform CLI)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TF_ROOT = REPO_ROOT / "infra" / "terraform"

CLINICAL_TOPIC = "clinical-records"
LAB_TOPIC = "lab-updates"


def test_phase4_modules_exist() -> None:
    for module in ("pubsub", "ingress", "secret_manager"):
        module_dir = TF_ROOT / "modules" / module
        assert (module_dir / "main.tf").is_file(), f"missing {module}/main.tf"
        assert (module_dir / "variables.tf").is_file()
        assert (module_dir / "outputs.tf").is_file()


def test_pubsub_defines_clinical_and_lab_topics_with_dlq() -> None:
    main = (TF_ROOT / "modules" / "pubsub" / "main.tf").read_text(encoding="utf-8")
    variables = (TF_ROOT / "modules" / "pubsub" / "variables.tf").read_text(encoding="utf-8")
    outputs = (TF_ROOT / "modules" / "pubsub" / "outputs.tf").read_text(encoding="utf-8")
    combined = main + "\n" + variables
    assert "google_pubsub_topic" in main
    assert CLINICAL_TOPIC in combined
    assert LAB_TOPIC in combined
    assert "dlq" in combined.lower() or "-dlq" in combined
    assert "dead_letter_policy" in main
    assert "google_pubsub_subscription" in main
    assert "clinical_topic" in outputs or "topic" in outputs
    assert "subscription" in outputs


def test_pubsub_grants_runtime_gsa_without_keys() -> None:
    main = (TF_ROOT / "modules" / "pubsub" / "main.tf").read_text(encoding="utf-8")
    assert "google_service_account_key" not in main
    assert "pubsub.publisher" in main or "roles/pubsub.publisher" in main
    assert "pubsub.subscriber" in main or "roles/pubsub.subscriber" in main


def test_secret_manager_creates_secrets_without_values() -> None:
    main = (TF_ROOT / "modules" / "secret_manager" / "main.tf").read_text(encoding="utf-8")
    assert "google_secret_manager_secret" in main
    assert "google_secret_manager_secret_version" not in main
    assert "secret_data" not in main
    assert "secretAccessor" in main or "secretmanager.secretAccessor" in main


def test_ingress_reserves_static_ip() -> None:
    main = (TF_ROOT / "modules" / "ingress" / "main.tf").read_text(encoding="utf-8")
    outputs = (TF_ROOT / "modules" / "ingress" / "outputs.tf").read_text(encoding="utf-8")
    assert "google_compute_global_address" in main
    assert "address" in outputs or "ip" in outputs.lower()


def test_dev_env_wires_phase4_modules() -> None:
    main = (TF_ROOT / "envs" / "dev" / "main.tf").read_text(encoding="utf-8")
    outputs = (TF_ROOT / "envs" / "dev" / "outputs.tf").read_text(encoding="utf-8")
    assert 'module "pubsub"' in main
    assert 'module "ingress"' in main
    assert 'module "secret_manager"' in main
    assert "clinical" in outputs.lower() or "pubsub" in outputs.lower()
    assert "ingress" in outputs.lower() or "static" in outputs.lower()
    assert "secret" in outputs.lower()


def test_no_secret_payloads_in_phase4_terraform() -> None:
    offenders: list[str] = []
    for module in ("pubsub", "ingress", "secret_manager"):
        for path in (TF_ROOT / "modules" / module).rglob("*.tf"):
            text = path.read_text(encoding="utf-8")
            if "secret_data" in text or "google_secret_manager_secret_version" in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))
            if "BEGIN " + "PRIVATE KEY" in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"secret payloads / keys in terraform: {offenders}"
