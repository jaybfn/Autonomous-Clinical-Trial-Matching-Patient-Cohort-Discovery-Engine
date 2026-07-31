# TrialMatch Architecture

Operator-facing overview of the Autonomous Clinical Trial Matching & Patient Cohort Discovery Engine.

## Purpose

Match synthetic/EPR clinical notes to ClinicalTrials.gov-style eligibility using a fail-closed multi-agent pipeline on GCP + Snowflake.

## Data sources

| Source | Role |
|--------|------|
| **Synthea** | Synthetic patients, labs, conditions, clinical notes (dev/prototype) |
| **ClinicalTrials.gov** | Trial eligibility text → Qdrant vectors |

## Full system diagram

```mermaid
flowchart TB
  subgraph sources [Data sources]
    SYN[Synthea samples - notes labs conditions]
    CTG[ClinicalTrials.gov eligibility JSONL]
    PUBLISH[publish_synthea_events.py]
    INDEX[index_trials_to_qdrant.py]
  end

  subgraph gcp [GCP project autonomous-agent-503517]
    subgraph net [Networking Terraform]
      VPC[VPC + Private subnets]
      NAT[Cloud NAT IPs]
      FW[Firewall]
    end

    subgraph messaging [Pub/Sub]
      T_CLIN[(clinical-records)]
      T_LAB[(lab-updates)]
      DLQ_C[(clinical-records-dlq)]
      DLQ_L[(lab-updates-dlq)]
      SUB_C[clinical-records-sub]
      SUB_L[lab-updates-sub]
    end

    subgraph gke [Private GKE trialmatch-gke]
      KSA[KSA trialmatch-ksa Workload Identity]
      ING_API[Ingress / static IP]
      API[FastAPI trialmatch-api]
      WORKER[Ingestion worker subscriber.py]
      QDR[(Qdrant trial_criteria)]

      subgraph orch [LangGraph orchestrator]
        C[1 Compliance - PII scrub]
        P[2 Parser - clinical features]
        M[3 Matcher - hybrid rank]
        A[4 Auditor - justifications]
        C --> P --> M --> A
      end
    end

    AR[(Artifact Registry - trialmatch-docker)]
    SM[Secret Manager - Snowflake key path]
    GSA[GSA trialmatch-runtime]
  end

  subgraph llm [LLM providers]
    OLLAMA[Ollama - local / free]
    VERTEX[Vertex Gemini - ADC]
  end

  subgraph sf [Snowflake TRIALMATCH_DEV]
    RAW[(RAW Synthea landing)]
    STG[(STAGING - dbt)]
    MARTS[(MARTS - AGENT_READ_ROLE)]
    AUDIT[(AUDIT - AUDIT_WRITE_ROLE)]
  end

  subgraph obs [Observability and CI]
    OTEL[OpenTelemetry - PHI-safe spans]
    OTLP[OTLP exporter - optional]
    GHA[GitHub Actions - Ruff Pytest TF]
    DOCS[Tracked docs - architecture runbooks WI]
  end

  SYN --> PUBLISH --> T_CLIN
  SYN --> PUBLISH --> T_LAB
  CTG --> INDEX --> QDR
  T_CLIN --> SUB_C --> WORKER
  T_LAB --> SUB_L --> WORKER
  WORKER -->|poison| DLQ_C
  WORKER -->|poison| DLQ_L

  ING_API --> API
  API --> C
  WORKER --> C
  KSA --> GSA
  API --> KSA
  WORKER --> KSA
  AR -.->|image| API
  AR -.->|image| WORKER

  P -.-> OLLAMA
  P -.-> VERTEX
  M --> QDR
  M -->|SELECT| MARTS
  A -->|INSERT| AUDIT
  RAW --> STG --> MARTS
  SM -.->|key path only| MARTS
  NAT --> MARTS

  API --> OTEL
  WORKER --> OTEL
  A --> OTEL
  OTEL --> OTLP
  GHA --> AR
  DOCS --> OTEL
```

## Runtime pipeline (compact)

```text
Pub/Sub (clinical-records) ──► Ingestion worker
                                    │
FastAPI POST /v1/match ─────────────┤
                                    ▼
                    LangGraph (fail-closed)
         Compliance → Parser → Matcher → Auditor
                    │            │          │
                    │            ├─ Qdrant (vectors)
                    │            └─ Snowflake MARTS (AGENT_READ_ROLE)
                    └─ Snowflake AUDIT (AUDIT_WRITE_ROLE)
```

| Agent | Responsibility | Privileges |
|-------|----------------|------------|
| Compliance | PHI scrub + content hash | In-process only |
| Parser | LLM → structured features | Ollama (local) or Vertex (ADC) |
| Matcher | Hybrid rank trials | Snowflake **read**, Qdrant search |
| Auditor | Justification + append-only audit | Snowflake **AUDIT write** only |

## Deploy topology (dev)

| Component | Value |
|-----------|--------|
| GCP project | `autonomous-agent-503517` |
| Private GKE | `trialmatch-gke` (endpoint `172.16.0.2`) |
| Namespace / KSA | `trialmatch` / `trialmatch-ksa` |
| Runtime GSA | `trialmatch-runtime@autonomous-agent-503517.iam.gserviceaccount.com` |
| Artifact Registry | `us-central1-docker.pkg.dev/autonomous-agent-503517/trialmatch-docker` |
| NAT IPs (Snowflake allowlist) | `136.112.132.174`, `34.61.252.214` |
| Pub/Sub | `clinical-records`, `lab-updates` (+ DLQs) |

IaC: `infra/terraform/envs/dev`. Workloads: `k8s/api`, `k8s/ingestion`, `k8s/qdrant`.

## Observability

- OpenTelemetry via `trialmatch.observability.tracing`
- Span attributes are **allowlisted** (no note text, SSN, MRN, email, etc.)
- Configure `OTEL_EXPORTER_OTLP_ENDPOINT` to export to a collector / Cloud Trace

## Related docs

- [Workload Identity](security/workload-identity.md)
- [Matching incident runbook](runbooks/incident-matching.md)
- Root [README.md](../README.md) (pipeline mermaid + phase status)
