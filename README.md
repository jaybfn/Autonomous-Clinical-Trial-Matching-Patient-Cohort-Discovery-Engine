# Autonomous Clinical Trial Matching & Patient Cohort Discovery Engine

Enterprise event-driven system for clinical trial matching and patient cohort discovery on **GCP** and **Snowflake**, with multi-agent workers (LangGraph) on Private GKE.

## Architecture (high level)

- **Ingestion:** GCP Pub/Sub clinical record / lab update events (Synthea-shaped producers)
- **Compute:** FastAPI + LangGraph agents on Private GKE (Workload Identity)
- **Warehouse / vectors:** Snowflake (dbt) + Qdrant
- **Primary datasets:** Synthea (synthetic EPR) + ClinicalTrials.gov (eligibility text)
- **Observability:** OpenTelemetry (PHI-safe spans) → OTLP (Cloud Trace in later phases)
- **GCP project:** `autonomous-agent-503517` via env `GCP_PROJECT_ID` (see `.env.example`)
- **IaC:** Terraform (VPC, NAT, GKE, Pub/Sub, IAM)

## Local development

### Prerequisites

- **Python 3.10+** (OpenTelemetry floor; Dev Container uses 3.11)
- [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers) (recommended) **or** local pip

### Bootstrap

```bash
# Host (once): ADC for GCP / Terraform
gcloud auth application-default login

# Dev Container (recommended): Cursor → Dev Containers: Reopen in Container
# Uses Anysphere Dev Containers + Docker Desktop; mounts %APPDATA%\gcloud as ADC
make test
gcloud config get-value project   # autonomous-agent-503517

# Local without container (Windows example with 3.10):
py -3.10 -m pip install -e ".[dev]"
py -3.10 -m pytest
cp .env.example .env   # set GCP_PROJECT_ID=autonomous-agent-503517
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
| 0.5 Data Sources (Synthea + ClinicalTrials.gov) | Complete |
| 1 Shared Contracts & Config | Complete |
| 1.5 OpenTelemetry Tracing Skeleton | Complete |
| 2 Terraform VPC & Networking | Complete |
| 3 Private GKE, IAM & Workload Identity | Complete |
| 4–14 | Planned |

## Deployed infra outputs (dev)

Captured from `terraform apply` in `infra/terraform/envs/dev` (project `autonomous-agent-503517`). Refresh anytime with `terraform output`.

| Output | Value |
|--------|--------|
| Cluster | `trialmatch-gke` (private endpoint `172.16.0.2`) |
| Registry | `us-central1-docker.pkg.dev/autonomous-agent-503517/trialmatch-docker` |
| Runtime GSA / KSA annotation | `trialmatch-runtime@autonomous-agent-503517.iam.gserviceaccount.com` |
| NAT IPs (Snowflake later) | `136.112.132.174`, `34.61.252.214` |

## Package

Python package: `trialmatch` (`src/trialmatch`), version `0.1.0`.
