# Autonomous Clinical Trial Matching & Patient Cohort Discovery Engine

Enterprise event-driven system for clinical trial matching and patient cohort discovery on **GCP** and **Snowflake**, with multi-agent workers (LangGraph) on Private GKE.

## Architecture (high level)

- **Ingestion:** GCP Pub/Sub clinical record / lab update events (Synthea-shaped producers)
- **Compute:** FastAPI + LangGraph agents on Private GKE (Workload Identity)
- **Warehouse / vectors:** Snowflake (dbt) + Qdrant
- **Primary datasets:** Synthea (synthetic EPR) + ClinicalTrials.gov (eligibility text)
- **IaC:** Terraform (VPC, NAT, GKE, Pub/Sub, IAM)

## Local development

### Prerequisites

- Python 3.9+
- [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers) (recommended) **or** local pip

### Bootstrap

```bash
# Dev Container: reopen in container, then:
make test

# Local:
make install
make test
make lint
```

### Coding standards

1. **TDD** — write `test_*` first, then implementation.
2. **Local README rule** — every code file `X` has a gitignored companion `X.README.md`.
3. **Local learning guides** — phase-wise file explanations live in gitignored `doc/` (start at `doc/README.md`).
4. **Zero hardcoded secrets** — ADC / Workload Identity only.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Phase status

| Phase | Status |
|-------|--------|
| 0 Project Setup & DevContainer | Complete |
| 0.5 Data Sources (Synthea + ClinicalTrials.gov) | Planned |
| 1–14 | Planned |

## Package

Python package: `trialmatch` (`src/trialmatch`), version `0.1.0`.
