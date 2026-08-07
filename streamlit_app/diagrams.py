"""Themed Mermaid diagrams for the Streamlit clinician demo."""

from __future__ import annotations

import json
from typing import Literal

import streamlit as st
import streamlit.components.v1 as components

# Vendor-ish palette via Mermaid classDef (approximate brand colors).
# Keep labels ASCII-safe (no raw HTML in node text) to avoid Mermaid parse errors.

SYSTEM_ARCHITECTURE_MERMAID = """
flowchart TB
  subgraph sources[Data sources]
    SYN[Synthea notes labs conditions]
    CTG[ClinicalTrials.gov eligibility JSONL]
    PUBLISH[publish_synthea_events.py]
    INDEX[index_trials_to_qdrant.py]
  end

  subgraph gcp[Google Cloud GCP project]
    subgraph net[Networking Terraform]
      VPC[VPC and private subnets]
      NAT[Cloud NAT IPs]
      FW[Firewall]
    end

    subgraph messaging[Pub/Sub]
      T_CLIN[(clinical-records)]
      T_LAB[(lab-updates)]
      DLQ_C[(clinical-records-dlq)]
      DLQ_L[(lab-updates-dlq)]
      SUB_C[clinical-records-sub]
      SUB_L[lab-updates-sub]
    end

    subgraph gke[Private GKE trialmatch-gke]
      KSA[KSA trialmatch-ksa Workload Identity]
      ING_API[Ingress / static IP]
      API[FastAPI trialmatch-api]
      WORKER[Ingestion worker subscriber.py]
      QDR[(Qdrant trial_criteria)]

      subgraph orch[LangGraph orchestrator]
        C[1 Compliance PII scrub]
        P[2 Parser clinical features]
        M[3 Matcher hybrid rank]
        A[4 Auditor justifications]
        C --> P --> M --> A
      end
    end

    AR[(Artifact Registry trialmatch-docker)]
    SM[Secret Manager Snowflake key path]
    GSA[GSA trialmatch-runtime]
  end

  subgraph llm[LLM providers]
    OLLAMA[Ollama local / free]
    VERTEX[Vertex Gemini ADC]
  end

  subgraph sf[Snowflake TRIALMATCH_DEV]
    RAW[(RAW Synthea landing)]
    STG[(STAGING dbt)]
    MARTS[(MARTS AGENT_READ_ROLE)]
    AUDIT[(AUDIT AUDIT_WRITE_ROLE)]
  end

  subgraph obs[Observability and CI]
    OTEL[OpenTelemetry PHI-safe spans]
    OTLP[OTLP exporter optional]
    GHA[GitHub Actions Ruff Pytest TF]
    DOCS[Tracked docs architecture runbooks]
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
  SM -.->|key-path| MARTS
  NAT --> MARTS

  API --> OTEL
  WORKER --> OTEL
  A --> OTEL
  OTEL --> OTLP
  GHA --> AR
  DOCS --> OTEL

  classDef gcp fill:#E8F0FE,stroke:#4285F4,stroke-width:1.5px,color:#174EA6
  classDef qdrant fill:#F3E8FF,stroke:#7C3AED,stroke-width:1.5px,color:#4C1D95
  classDef snowflake fill:#E5F6FD,stroke:#29B5E8,stroke-width:1.5px,color:#115E7A
  classDef ollama fill:#F3F4F6,stroke:#6B7280,stroke-width:1.5px,color:#111827
  classDef vertex fill:#E6F4EA,stroke:#34A853,stroke-width:1.5px,color:#137333
  classDef agent fill:#D8F0F0,stroke:#0D7377,stroke-width:1.5px,color:#0F1C24
  classDef source fill:#FFF7ED,stroke:#EA580C,stroke-width:1.5px,color:#9A3412
  classDef obs fill:#FEF3C7,stroke:#D97706,stroke-width:1.5px,color:#92400E

  class VPC,NAT,FW,T_CLIN,T_LAB,DLQ_C,DLQ_L,SUB_C,SUB_L,KSA,ING_API,API,WORKER,AR,SM,GSA gcp
  class QDR qdrant
  class C,P,M,A agent
  class OLLAMA ollama
  class VERTEX vertex
  class RAW,STG,MARTS,AUDIT snowflake
  class SYN,CTG,PUBLISH,INDEX source
  class OTEL,OTLP,GHA,DOCS obs
"""

AGENT_PIPELINE_MERMAID = """
flowchart TD
  START([START]) --> C[Compliance - PII scrub]
  C -->|ok| P[Parser - clinical features]
  C -->|error| FAIL([END failed])
  P -->|ok| M[Matcher - Qdrant + Snowflake]
  P -->|error| FAIL
  M -->|ok| A[Auditor - justification + audit write]
  M -->|error| FAIL
  A --> OK([END ok])

  subgraph inputs[Inputs]
    NOTE[note_text + patient_id + correlation_id]
  end

  subgraph stores[Backends]
    LLM[Ollama / Vertex LLM]
    QDR[(Qdrant trial vectors)]
    SF[(Snowflake MARTS read / AUDIT write)]
  end

  NOTE --> C
  P -.-> LLM
  M -.-> QDR
  M -.-> SF
  A -.-> SF

  classDef agent fill:#D8F0F0,stroke:#0D7377,stroke-width:2px,color:#0F1C24
  classDef terminal fill:#F3F4F6,stroke:#5A7184,stroke-width:1.5px,color:#0F1C24
  classDef input fill:#FFF7ED,stroke:#EA580C,stroke-width:1.5px,color:#9A3412
  classDef qdrant fill:#F3E8FF,stroke:#7C3AED,stroke-width:1.5px,color:#4C1D95
  classDef snowflake fill:#E5F6FD,stroke:#29B5E8,stroke-width:1.5px,color:#115E7A
  classDef llm fill:#E8F0FE,stroke:#4285F4,stroke-width:1.5px,color:#174EA6

  class C,P,M,A agent
  class START,OK,FAIL terminal
  class NOTE input
  class QDR qdrant
  class SF snowflake
  class LLM llm
"""

DiagramKind = Literal["architecture", "agents"]


def render_mermaid(code: str, *, height: int = 920, element_id: str = "mermaid-diagram") -> None:
    """Render Mermaid by injecting source via JSON (avoids HTML-entity parse errors)."""
    safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in element_id)
    code_json = json.dumps(code.strip())
    html_doc = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    html, body {{
      margin: 0;
      padding: 0;
      background: transparent;
      font-family: system-ui, sans-serif;
    }}
    #wrap {{
      padding: 0.35rem 0.15rem 1rem;
      overflow: auto;
      min-height: 200px;
    }}
    #err {{
      display: none;
      color: #a33b2b;
      font-size: 0.9rem;
      white-space: pre-wrap;
      padding: 0.75rem;
      border: 1px solid #f0c2bc;
      border-radius: 8px;
      background: #fff5f4;
    }}
    #out svg {{
      max-width: 100%;
      height: auto;
    }}
  </style>
</head>
<body>
  <div id="wrap">
    <div id="err"></div>
    <div id="out"></div>
  </div>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
    const code = {code_json};
    const out = document.getElementById("out");
    const err = document.getElementById("err");
    mermaid.initialize({{
      startOnLoad: false,
      securityLevel: "loose",
      theme: "base",
      themeVariables: {{
        fontFamily: "system-ui, sans-serif",
        fontSize: "14px",
        primaryColor: "#E8F0FE",
        primaryTextColor: "#174EA6",
        primaryBorderColor: "#4285F4",
        lineColor: "#5A7184",
        secondaryColor: "#E5F6FD",
        tertiaryColor: "#F3E8FF",
        clusterBkg: "#ffffffcc",
        clusterBorder: "#c5d0d8",
        titleColor: "#0f1c24",
        edgeLabelBackground: "#ffffff"
      }},
      flowchart: {{
        curve: "basis",
        htmlLabels: true,
        padding: 12,
        nodeSpacing: 28,
        rankSpacing: 36,
        useMaxWidth: true
      }}
    }});
    try {{
      const result = await mermaid.render("{safe_id}-svg", code);
      out.innerHTML = result.svg;
    }} catch (e) {{
      err.style.display = "block";
      err.textContent = "Mermaid render failed: " + (e && e.message ? e.message : String(e));
    }}
  </script>
</body>
</html>
"""
    components.html(html_doc, height=height, scrolling=True)


def render_theme_legend() -> None:
    """Small legend explaining block colors."""
    st.markdown(
        """
        <div class="tm-legend">
          <span class="tm-leg tm-leg-gcp">GCP</span>
          <span class="tm-leg tm-leg-sf">Snowflake</span>
          <span class="tm-leg tm-leg-qd">Qdrant</span>
          <span class="tm-leg tm-leg-agent">Agents</span>
          <span class="tm-leg tm-leg-vertex">Vertex</span>
          <span class="tm-leg tm-leg-ollama">Ollama</span>
          <span class="tm-leg tm-leg-src">Sources</span>
          <span class="tm-leg tm-leg-obs">Obs / CI</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_diagram(kind: DiagramKind) -> None:
    if kind == "architecture":
        st.caption(
            "End-to-end stack from the README — blocks colored by platform "
            "(GCP blue, Snowflake cyan, Qdrant violet, agents teal)."
        )
        render_theme_legend()
        render_mermaid(SYSTEM_ARCHITECTURE_MERMAID, height=1100, element_id="arch-diagram")
    else:
        st.caption(
            "LangGraph fail-closed pipeline used by POST /v1/match — "
            "Compliance → Parser → Matcher → Auditor."
        )
        render_theme_legend()
        render_mermaid(AGENT_PIPELINE_MERMAID, height=720, element_id="agents-diagram")
