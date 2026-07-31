.PHONY: help install test lint format bootstrap pre-commit-install pre-commit bastion-ssh bastion

help:
	@echo "Targets: bootstrap install test lint format pre-commit-install pre-commit bastion-ssh"

bastion-ssh bastion:
	@./scripts/bastion-ssh.sh

bootstrap: install pre-commit-install

# Prefer Python 3.10+ (OpenTelemetry floor). Override with: make PYTHON=python3.11 test
PYTHON ?= python

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m ruff format --check src tests

format:
	$(PYTHON) -m ruff check --fix src tests
	$(PYTHON) -m ruff format src tests

pre-commit-install:
	$(PYTHON) -m pre_commit install --hook-type pre-commit --hook-type pre-push

pre-commit:
	$(PYTHON) -m pre_commit run --all-files
