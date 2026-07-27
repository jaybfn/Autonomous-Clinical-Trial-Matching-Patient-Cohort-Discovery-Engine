# Contributing

## Definition of Done

For every functional change:

1. **TDD flow** — write the test file first (e.g. `test_service.py`), confirm it fails or validates the contract, then implement.
2. **Local README rule** — every code file (`*.py`, `*.tf`, `*.sql`, `*.yml`, etc.) MUST have a corresponding gitignored companion named `*.README.md` describing purpose, inputs/outputs, and local execution steps.
3. **Local learning guides** — phase-wise “why every file exists” docs live under gitignored `doc/` (see `doc/README.md`). Do not commit `doc/`.
4. **Git hygiene** — `*.README.md` and `doc/` must never be committed (enforced by `.gitignore`).
5. **Zero hardcoded secrets** — use Application Default Credentials (ADC) or Workload Identity bindings only.
6. **Synthetic/open data only for prototyping** — Synthea + ClinicalTrials.gov; commit small samples under `data/*/samples/`, keep bulk downloads in gitignored `data/raw/`.

## Local checks before PR

```bash
# Requires Python 3.10+ (OpenTelemetry floor)
py -3.10 -m pip install -e ".[dev]"
py -3.10 -m pytest
py -3.10 -m ruff check src tests
```

Copy `.env.example` → `.env` and keep `GCP_PROJECT_ID=autonomous-agent-503517`.

## Branch & PR expectations

- Keep phases focused; do not mix unrelated infra and agent changes.
- CI will enforce Ruff, Pytest, and Terraform formatting checks (Phase 13).
