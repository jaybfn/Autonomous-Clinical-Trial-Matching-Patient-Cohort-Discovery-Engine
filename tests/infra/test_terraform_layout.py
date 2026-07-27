"""Phase 2 contract tests: Terraform layout and hygiene (no terraform CLI required)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TF_ROOT = REPO_ROOT / "infra" / "terraform"

SECRET_PATTERNS = [
    re.compile(r'(?i)password\s*=\s*"[^"]+"'),
    re.compile(r'(?i)secret(_key)?\s*=\s*"[^"]+"'),
    re.compile(r'(?i)private_key\s*=\s*"-----BEGIN'),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def _tf_files() -> list[Path]:
    return sorted(TF_ROOT.rglob("*.tf"))


def test_required_modules_exist() -> None:
    for module in ("vpc", "cloud_nat", "firewall"):
        module_dir = TF_ROOT / "modules" / module
        assert (module_dir / "main.tf").is_file(), f"missing {module}/main.tf"
        assert (module_dir / "variables.tf").is_file()
        assert (module_dir / "outputs.tf").is_file()


def test_dev_env_files_exist() -> None:
    env = TF_ROOT / "envs" / "dev"
    for name in ("main.tf", "variables.tf", "outputs.tf", "backend.tf", "providers.tf"):
        assert (env / name).is_file(), f"missing envs/dev/{name}"
    assert (env / "terraform.tfvars.example").is_file()


def test_root_versions_file_exists() -> None:
    assert (TF_ROOT / "versions.tf").is_file()


def test_nat_module_defines_static_ip_outputs() -> None:
    outputs = (TF_ROOT / "modules" / "cloud_nat" / "outputs.tf").read_text(encoding="utf-8")
    assert "nat_static_ips" in outputs
    assert "output" in outputs


def test_vpc_enables_private_google_access() -> None:
    main = (TF_ROOT / "modules" / "vpc" / "main.tf").read_text(encoding="utf-8")
    assert "private_ip_google_access" in main
    assert "true" in main


def test_dev_outputs_export_nat_ips_for_snowflake() -> None:
    outputs = (TF_ROOT / "envs" / "dev" / "outputs.tf").read_text(encoding="utf-8")
    assert "nat_static_ips" in outputs
    assert "network_name" in outputs
    assert "private_subnet_name" in outputs


def test_no_plaintext_secret_assignments_in_tf() -> None:
    assert _tf_files(), "expected terraform files under infra/terraform"
    offenders: list[str] = []
    for path in _tf_files():
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{pattern.pattern}")
    assert not offenders, f"possible secrets in terraform: {offenders}"


def test_tfvars_example_uses_locked_gcp_project() -> None:
    example = (TF_ROOT / "envs" / "dev" / "terraform.tfvars.example").read_text(encoding="utf-8")
    assert "autonomous-agent-503517" in example
    assert "project_id" in example


def test_vpc_module_tftest_exists() -> None:
    assert (TF_ROOT / "modules" / "vpc" / "test_vpc.tftest.hcl").is_file()
