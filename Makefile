.PHONY: help install test lint format bootstrap

help:
	@echo "Targets: bootstrap install test lint format"

bootstrap: install

install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements-dev.txt

test:
	python -m pytest

lint:
	python -m ruff check src tests
	python -m ruff format --check src tests

format:
	python -m ruff check --fix src tests
	python -m ruff format src tests
