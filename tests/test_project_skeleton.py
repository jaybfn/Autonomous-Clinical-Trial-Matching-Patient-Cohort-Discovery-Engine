"""Phase 0 contract tests: package metadata and repo hygiene."""

from __future__ import annotations

from pathlib import Path

import trialmatch

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_package_exposes_version() -> None:
    assert hasattr(trialmatch, "__version__")
    assert isinstance(trialmatch.__version__, str)
    assert trialmatch.__version__ == "0.1.0"


def test_package_exposes_name() -> None:
    assert trialmatch.__name__ == "trialmatch"


def test_gitignore_blocks_local_readme_companions() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.README.md" in gitignore


def test_gitignore_blocks_env_and_secrets() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in (".env", ".env.*", "*.pem", "credentials.json", ".terraform/"):
        assert pattern in gitignore


def test_gitignore_blocks_local_doc_learning_folder() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "doc/" in gitignore


def test_gitignore_blocks_bulk_data_raw_downloads() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/raw/" in gitignore


def test_pyproject_defines_package_metadata() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "trialmatch"' in pyproject
    assert 'version = "0.1.0"' in pyproject
    assert "pytest" in pyproject
    assert "ruff" in pyproject


def test_devcontainer_files_exist() -> None:
    assert (REPO_ROOT / ".devcontainer" / "devcontainer.json").is_file()
    assert (REPO_ROOT / ".devcontainer" / "Dockerfile").is_file()


def test_devcontainer_wires_gcloud_adc_and_project_env() -> None:
    """Host ADC + gcloud CLI must be available inside the Dev Container."""
    cfg = (REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8")
    dockerfile = (REPO_ROOT / ".devcontainer" / "Dockerfile").read_text(encoding="utf-8")
    post_create = REPO_ROOT / ".devcontainer" / "post-create.sh"
    assert "google-cloud-cli" in dockerfile
    assert post_create.is_file()
    assert "APPDATA" in cfg
    assert "/mnt/host-gcloud" in cfg
    assert "GOOGLE_APPLICATION_CREDENTIALS" in cfg
    assert "CLOUDSDK_CONFIG" in cfg
    assert "/home/vscode/.config/gcloud" in cfg
    assert "GCP_PROJECT_ID" in cfg
    assert "GOOGLE_CLOUD_PROJECT" in cfg
    assert "safe.directory" in cfg
    assert "GIT_CONFIG_VALUE_0" in cfg
    # Must not use the Windows mount as CLOUDSDK_CONFIG (EPERM on credentials.db).
    assert '"CLOUDSDK_CONFIG": "/mnt/host-gcloud"' not in cfg
    assert "target=/home/vscode/.config/gcloud" not in cfg


def test_vscode_settings_configure_ruff_and_pytest() -> None:
    settings = (REPO_ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8")
    assert "ruff" in settings.lower()
    assert "pytest" in settings.lower()


def test_contributing_documents_tdd_and_readme_rule() -> None:
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "TDD" in contributing or "test-driven" in contributing.lower()
    assert "*.README.md" in contributing


def test_makefile_exposes_test_and_lint_targets() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "test:" in makefile
    assert "lint:" in makefile
