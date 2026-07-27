"""Phase 3 contract tests: GKE, Artifact Registry, IAM, Workload Identity (no terraform CLI)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TF_ROOT = REPO_ROOT / "infra" / "terraform"
K8S_ROOT = REPO_ROOT / "k8s"

WI_ANNOTATION_KEY = "iam.gke.io/gcp-service-account"
LOCKED_PROJECT = "autonomous-agent-503517"
RUNTIME_GSA_ID = "trialmatch-runtime"
KSA_NAME = "trialmatch-ksa"
KSA_NAMESPACE = "trialmatch"


def test_phase3_modules_exist() -> None:
    for module in ("gke", "artifact_registry", "iam", "workload_identity"):
        module_dir = TF_ROOT / "modules" / module
        assert (module_dir / "main.tf").is_file(), f"missing {module}/main.tf"
        assert (module_dir / "variables.tf").is_file()
        assert (module_dir / "outputs.tf").is_file()


def test_gke_module_is_private_cluster() -> None:
    main = (TF_ROOT / "modules" / "gke" / "main.tf").read_text(encoding="utf-8")
    assert "google_container_cluster" in main
    assert "enable_private_nodes" in main
    assert "enable_private_endpoint" in main
    assert "workload_identity_config" in main
    assert "remove_default_node_pool" in main or "remove_default_node_pool = true" in main


def test_gke_module_tftest_exists() -> None:
    assert (TF_ROOT / "modules" / "gke" / "test_gke.tftest.hcl").is_file()


def test_vpc_exports_gke_secondary_range_names() -> None:
    outputs = (TF_ROOT / "modules" / "vpc" / "outputs.tf").read_text(encoding="utf-8")
    assert "pods_range_name" in outputs
    assert "services_range_name" in outputs


def test_artifact_registry_module_defines_docker_repo() -> None:
    main = (TF_ROOT / "modules" / "artifact_registry" / "main.tf").read_text(encoding="utf-8")
    outputs = (TF_ROOT / "modules" / "artifact_registry" / "outputs.tf").read_text(encoding="utf-8")
    assert "google_artifact_registry_repository" in main
    assert "format" in main and "DOCKER" in main
    assert "repository_url" in outputs


def test_iam_module_creates_runtime_gsa_without_keys() -> None:
    main = (TF_ROOT / "modules" / "iam" / "main.tf").read_text(encoding="utf-8")
    variables = (TF_ROOT / "modules" / "iam" / "variables.tf").read_text(encoding="utf-8")
    combined = main + "\n" + variables
    assert "google_service_account" in main
    assert RUNTIME_GSA_ID in combined or "account_id" in main
    assert "google_service_account_key" not in main
    assert "roles/pubsub.subscriber" in combined or "pubsub.subscriber" in combined
    assert "secretmanager.secretAccessor" in combined or "secretAccessor" in combined


def test_workload_identity_binds_ksa_to_gsa() -> None:
    main = (TF_ROOT / "modules" / "workload_identity" / "main.tf").read_text(encoding="utf-8")
    outputs = (TF_ROOT / "modules" / "workload_identity" / "outputs.tf").read_text(encoding="utf-8")
    assert "roles/iam.workloadIdentityUser" in main
    assert "svc.id.goog" in main
    assert "gsa_email" in outputs or "gcp_service_account_email" in outputs
    assert "ksa_annotation" in outputs or WI_ANNOTATION_KEY.replace(".", "_") in outputs


def test_dev_env_wires_phase3_modules() -> None:
    main = (TF_ROOT / "envs" / "dev" / "main.tf").read_text(encoding="utf-8")
    outputs = (TF_ROOT / "envs" / "dev" / "outputs.tf").read_text(encoding="utf-8")
    assert 'module "gke"' in main
    assert 'module "artifact_registry"' in main
    assert 'module "iam"' in main
    assert 'module "workload_identity"' in main
    # WI must wait for the GKE identity pool.
    wi_block = main.split('module "workload_identity"')[1].split("module ")[0]
    assert "module.gke" in wi_block
    assert "cluster_name" in outputs
    assert "artifact_registry_url" in outputs or "repository_url" in outputs
    assert "workload_identity" in outputs.lower() or "ksa_annotation" in outputs


def test_gke_defaults_avoid_ssd_quota_pressure() -> None:
    variables = (TF_ROOT / "modules" / "gke" / "variables.tf").read_text(encoding="utf-8")
    assert 'default     = "pd-standard"' in variables or 'default = "pd-standard"' in variables
    assert "disk_size_gb" in variables


def test_ksa_manifest_matches_workload_identity_contract() -> None:
    manifest = K8S_ROOT / "serviceaccounts" / "trialmatch-ksa.yaml"
    assert manifest.is_file()
    text = manifest.read_text(encoding="utf-8")
    assert "kind: ServiceAccount" in text
    assert f"name: {KSA_NAME}" in text
    assert f"namespace: {KSA_NAMESPACE}" in text
    assert WI_ANNOTATION_KEY in text
    assert f"{RUNTIME_GSA_ID}@{LOCKED_PROJECT}.iam.gserviceaccount.com" in text


def test_no_service_account_json_keys_in_phase3() -> None:
    offenders: list[str] = []
    for path in list(TF_ROOT.rglob("*.tf")) + list(K8S_ROOT.rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        pem_marker = "BEGIN " + "PRIVATE KEY"
        if "google_service_account_key" in text or pem_marker in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"SA keys / private key material found: {offenders}"
