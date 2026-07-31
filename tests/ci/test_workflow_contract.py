"""TDD contracts for GitHub Actions workflows (structure + no hardcoded secrets)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CI_WORKFLOW = WORKFLOWS / "ci.yml"
TERRAFORM_WORKFLOW = WORKFLOWS / "terraform.yml"
CODEOWNERS = REPO_ROOT / ".github" / "CODEOWNERS"

# Patterns that must never appear as hardcoded credentials in workflow YAML.
FORBIDDEN_SECRET_PATTERNS = [
    re.compile(r"BEGIN\s+(RSA\s+)?PRIVATE\s+KEY", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}", re.I),
    re.compile(r"password\s*[:=]\s*['\"][^'\"]+['\"]", re.I),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"GOOGLE_APPLICATION_CREDENTIALS\s*[:=]\s*['\"]/.+['\"]"),
]


def _load_workflow(path: Path) -> dict:
    assert path.is_file(), f"missing workflow: {path}"
    # Keep `on` as a string key (PyYAML 1.1 otherwise turns bare `on:` into True).
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    assert isinstance(data, dict)
    return data


def _workflow_on(data: dict) -> dict | list | str:
    if "on" in data:
        return data["on"]
    if True in data:  # YAML 1.1 quirk for unquoted `on:`
        return data[True]
    raise AssertionError("workflow missing 'on' trigger")


def _job_step_texts(job: dict) -> list[str]:
    texts: list[str] = []
    for step in job.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for key in ("name", "run", "uses"):
            value = step.get(key)
            if isinstance(value, str):
                texts.append(value)
    return texts


def test_ci_workflow_runs_ruff_and_pytest() -> None:
    data = _load_workflow(CI_WORKFLOW)
    on = _workflow_on(data)
    assert "pull_request" in on or on == "pull_request"
    jobs = data["jobs"]
    assert "lint-test" in jobs or "ci" in jobs
    job = jobs.get("lint-test") or jobs["ci"]
    blob = "\n".join(_job_step_texts(job)).lower()
    assert "requirements-dev.txt" in blob
    assert "ruff" in blob
    assert "pytest" in blob


def test_terraform_workflow_fmt_and_validate_without_apply() -> None:
    data = _load_workflow(TERRAFORM_WORKFLOW)
    jobs = data["jobs"]
    assert "terraform" in jobs
    job = jobs["terraform"]
    blob = "\n".join(_job_step_texts(job)).lower()
    assert "terraform fmt" in blob
    assert "validate" in blob
    assert "terraform apply" not in blob
    assert "terraform destroy" not in blob


def test_workflows_contain_no_hardcoded_secrets() -> None:
    paths = [CI_WORKFLOW, TERRAFORM_WORKFLOW]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_SECRET_PATTERNS:
            match = pattern.search(text)
            assert match is None, f"{path.name} matched forbidden pattern: {pattern.pattern}"


def test_workflows_do_not_embed_service_account_json() -> None:
    for path in (CI_WORKFLOW, TERRAFORM_WORKFLOW):
        text = path.read_text(encoding="utf-8")
        assert '"type": "service_account"' not in text
        assert "private_key_id" not in text


def test_codeowners_exists() -> None:
    assert CODEOWNERS.is_file()
    text = CODEOWNERS.read_text(encoding="utf-8")
    assert "*" in text
    assert "@" in text


@pytest.mark.parametrize("filename", ["ci.yml", "terraform.yml"])
def test_workflow_files_are_valid_yaml(filename: str) -> None:
    path = WORKFLOWS / filename
    data = _load_workflow(path)
    assert "jobs" in data
