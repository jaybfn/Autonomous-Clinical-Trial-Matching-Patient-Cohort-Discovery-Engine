"""Themed Mermaid diagrams for the Streamlit clinician demo."""

from __future__ import annotations

import json
from typing import Literal

import streamlit as st
import streamlit.components.v1 as components

# Keep charts relatively flat — deep nested subgraphs + many cross edges
# trigger Mermaid/dagre: "Could not find a suitable point for the given distance".

SYSTEM_ARCHITECTURE_MERMAID = """
flowchart LR
  subgraph sources[Data sources]
    SYN[Synthea]
    CTG[ClinicalTrials.gov]
  end

  subgraph gcp[Google Cloud]
    PUB[Pub/Sub topics]
    ING[GCE Ingress]
    API[FastAPI trialmatch-api]
    WORKER[Ingestion worker]
    AR[Artifact Registry]
    SM[Secret Manager]
    GSA[Runtime GSA / WI]
    NAT[Cloud NAT]
  end

  subgraph gke[Private GKE]
    C[Compliance]
    P[Parser]
    M[Matcher]
    A[Auditor]
    QDR[(Qdrant)]
    OLLAMA[Ollama]
  end

  subgraph sf[Snowflake]
    RAW[(RAW)]
    MARTS[(MARTS)]
    AUDIT[(AUDIT)]
  end

  subgraph llm[LLM options]
    VERTEX[Vertex Gemini]
  end

  SYN --> PUB --> WORKER
  CTG --> QDR
  ING --> API
  WORKER --> C
  API --> C
  C --> P --> M --> A
  P -.-> OLLAMA
  P -.-> VERTEX
  M --> QDR
  M --> MARTS
  A --> AUDIT
  RAW --> MARTS
  SM -.-> API
  GSA -.-> API
  AR -.-> API
  NAT --> MARTS

  classDef gcp fill:#E8F0FE,stroke:#4285F4,stroke-width:1.5px,color:#174EA6
  classDef qdrant fill:#F3E8FF,stroke:#7C3AED,stroke-width:1.5px,color:#4C1D95
  classDef snowflake fill:#E5F6FD,stroke:#29B5E8,stroke-width:1.5px,color:#115E7A
  classDef ollama fill:#F3F4F6,stroke:#6B7280,stroke-width:1.5px,color:#111827
  classDef vertex fill:#E6F4EA,stroke:#34A853,stroke-width:1.5px,color:#137333
  classDef agent fill:#D8F0F0,stroke:#0D7377,stroke-width:1.5px,color:#0F1C24
  classDef source fill:#FFF7ED,stroke:#EA580C,stroke-width:1.5px,color:#9A3412

  class PUB,ING,API,WORKER,AR,SM,GSA,NAT gcp
  class QDR qdrant
  class C,P,M,A agent
  class OLLAMA ollama
  class VERTEX vertex
  class RAW,MARTS,AUDIT snowflake
  class SYN,CTG source
"""

AGENT_PIPELINE_MERMAID = """
flowchart TD
  START([START]) --> C[Compliance - PII scrub]
  C -->|ok| P[Parser - clinical features]
  C -->|error| FAIL([END failed])
  P -->|ok| M[Matcher - Qdrant + Snowflake]
  P -->|error| FAIL
  M -->|ok| A[Auditor - justification + audit]
  M -->|error| FAIL
  A --> OK([END ok])

  NOTE[Inputs: note_text + patient_id] --> C
  P -.-> LLM[Ollama / Vertex]
  M -.-> QDR[(Qdrant)]
  M -.-> SF[(Snowflake)]
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


def render_mermaid(code: str, *, height: int = 720, element_id: str = "mermaid-diagram") -> None:
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
    #out {{
      display: flex;
      justify-content: center;
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
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs";
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
        clusterBkg: "#ffffff",
        clusterBorder: "#c5d0d8",
        titleColor: "#0f1c24",
        edgeLabelBackground: "#ffffff"
      }},
      flowchart: {{
        curve: "linear",
        htmlLabels: true,
        padding: 16,
        nodeSpacing: 40,
        rankSpacing: 50,
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
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_diagram(kind: DiagramKind) -> None:
    if kind == "architecture":
        st.caption(
            "Simplified end-to-end stack (README architecture) — "
            "blocks colored by platform (GCP, Snowflake, Qdrant, agents)."
        )
        render_theme_legend()
        render_mermaid(SYSTEM_ARCHITECTURE_MERMAID, height=560, element_id="arch-diagram")
    else:
        st.caption(
            "LangGraph fail-closed pipeline for POST /v1/match — "
            "Compliance → Parser → Matcher → Auditor."
        )
        render_theme_legend()
        render_mermaid(AGENT_PIPELINE_MERMAID, height=640, element_id="agents-diagram")
