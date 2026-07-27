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
pip install -r requirements-dev.txt
make pre-commit-install   # once per clone / Dev Container
make test
make lint
# Or run the full hook suite:
make pre-commit
```

### Pre-commit hooks (recommended)

| When | What runs | Why |
|------|-----------|-----|
| **Every commit** | Ruff lint/format, Terraform `fmt`, trailing whitespace, YAML/JSON/TOML, merge-conflict markers, large files, private-key detect | Fast; catches style & secret foot-guns before review |
| **Every push** | `pytest` | Full unit suite; keeps TDD “red” commits allowed locally |
| **CI (Phase 13)** | Same checks again | Enforce even if someone skips hooks with `--no-verify` |

Copy `.env.example` → `.env` and keep `GCP_PROJECT_ID=autonomous-agent-503517`.

## Branch & PR expectations

- Keep phases focused; do not mix unrelated infra and agent changes.
- CI will enforce Ruff, Pytest, and Terraform formatting checks (Phase 13).
