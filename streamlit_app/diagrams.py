"""Platform-themed architecture diagrams for the Streamlit demo (HTML/CSS, no Mermaid)."""

from __future__ import annotations

from typing import Literal

import streamlit as st

DiagramKind = Literal["architecture", "agents"]


def render_theme_legend() -> None:
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


def _architecture_html() -> str:
    return """
<div class="tm-flow">
  <div class="tm-flow-row">
    <section class="tm-zone tm-zone-src">
      <h4>Data sources</h4>
      <div class="tm-nodes">
        <div class="tm-node tm-src">Synthea<br/><small>notes / labs / conditions</small></div>
        <div class="tm-node tm-src">ClinicalTrials.gov<br/><small>eligibility JSONL</small></div>
      </div>
    </section>
    <div class="tm-arrow">→</div>
    <section class="tm-zone tm-zone-gcp">
      <h4>Google Cloud</h4>
      <div class="tm-nodes">
        <div class="tm-node tm-gcp">Pub/Sub<br/><small>clinical + lab topics</small></div>
        <div class="tm-node tm-gcp">GCE Ingress<br/><small>public API IP</small></div>
        <div class="tm-node tm-gcp">FastAPI<br/><small>trialmatch-api</small></div>
        <div class="tm-node tm-gcp">Ingestion worker</div>
        <div class="tm-node tm-gcp">Artifact Registry</div>
        <div class="tm-node tm-gcp">Secret Manager</div>
        <div class="tm-node tm-gcp">Workload Identity<br/><small>runtime GSA</small></div>
        <div class="tm-node tm-gcp">Cloud NAT</div>
      </div>
    </section>
  </div>

  <div class="tm-flow-down">↓</div>

  <div class="tm-flow-row">
    <section class="tm-zone tm-zone-gke">
      <h4>Private GKE · LangGraph</h4>
      <div class="tm-agent-strip">
        <div class="tm-node tm-agent">1 Compliance<br/><small>PII scrub</small></div>
        <span class="tm-pipe">→</span>
        <div class="tm-node tm-agent">2 Parser<br/><small>clinical features</small></div>
        <span class="tm-pipe">→</span>
        <div class="tm-node tm-agent">3 Matcher<br/><small>hybrid rank</small></div>
        <span class="tm-pipe">→</span>
        <div class="tm-node tm-agent">4 Auditor<br/><small>justifications</small></div>
      </div>
      <div class="tm-nodes tm-nodes-tight">
        <div class="tm-node tm-qd">Qdrant<br/><small>trial_criteria vectors</small></div>
        <div class="tm-node tm-ollama">Ollama<br/><small>llama3.2:1b</small></div>
        <div class="tm-node tm-vertex">Vertex Gemini<br/><small>optional ADC</small></div>
      </div>
    </section>
    <div class="tm-arrow">↔</div>
    <section class="tm-zone tm-zone-sf">
      <h4>Snowflake · TRIALMATCH_DEV</h4>
      <div class="tm-nodes">
        <div class="tm-node tm-sf">RAW<br/><small>Synthea landing</small></div>
        <div class="tm-node tm-sf">STAGING<br/><small>dbt</small></div>
        <div class="tm-node tm-sf">MARTS<br/><small>AGENT_READ_ROLE</small></div>
        <div class="tm-node tm-sf">AUDIT<br/><small>AUDIT_WRITE_ROLE</small></div>
      </div>
      <p class="tm-flow-note">Matcher SELECT from MARTS · Auditor INSERT into AUDIT</p>
    </section>
  </div>

  <div class="tm-flow-down">↓</div>

  <section class="tm-zone tm-zone-obs">
    <h4>Observability and CI</h4>
    <div class="tm-nodes">
      <div class="tm-node tm-obs">OpenTelemetry<br/><small>PHI-safe spans</small></div>
      <div class="tm-node tm-obs">GitHub Actions<br/><small>Ruff / Pytest / TF</small></div>
      <div class="tm-node tm-obs">Tracked docs<br/><small>architecture / runbooks</small></div>
    </div>
  </section>
</div>
"""


def _agents_html() -> str:
    return """
<div class="tm-flow">
  <div class="tm-agent-pipeline">
    <div class="tm-node tm-src tm-node-wide">
      Inputs<br/><small>note_text + patient_id + correlation_id</small>
    </div>
    <div class="tm-flow-down">↓</div>
    <div class="tm-node tm-terminal">START</div>
    <div class="tm-flow-down">↓</div>
    <div class="tm-node tm-agent tm-node-wide">
      Compliance · Agent 1<br/><small>PII scrub → scrubbed_text + content_hash</small>
    </div>
    <div class="tm-branch">
      <span class="tm-ok-edge">ok ↓</span>
      <span class="tm-fail-edge">error → END failed</span>
    </div>
    <div class="tm-node tm-agent tm-node-wide">
      Parser · Agent 2<br/><small>LLM JSON → validated clinical features</small>
    </div>
    <div class="tm-side-links">
      <span class="tm-node tm-ollama">Ollama</span>
      <span class="tm-node tm-vertex">Vertex</span>
    </div>
    <div class="tm-branch">
      <span class="tm-ok-edge">ok ↓</span>
      <span class="tm-fail-edge">error → END failed</span>
    </div>
    <div class="tm-node tm-agent tm-node-wide">
      Matcher · Agent 3<br/>
      <small>Hybrid Qdrant vector + Snowflake feature overlap</small>
    </div>
    <div class="tm-side-links">
      <span class="tm-node tm-qd">Qdrant</span>
      <span class="tm-node tm-sf">Snowflake MARTS</span>
    </div>
    <div class="tm-branch">
      <span class="tm-ok-edge">ok ↓</span>
      <span class="tm-fail-edge">error → END failed</span>
    </div>
    <div class="tm-node tm-agent tm-node-wide">
      Auditor · Agent 4<br/><small>Justification + append-only AUDIT write</small>
    </div>
    <div class="tm-side-links">
      <span class="tm-node tm-sf">Snowflake AUDIT</span>
    </div>
    <div class="tm-flow-down">↓</div>
    <div class="tm-node tm-terminal tm-terminal-ok">
      END ok · ranked matches + audit record
    </div>
  </div>
</div>
"""


def render_diagram(kind: DiagramKind) -> None:
    render_theme_legend()
    if kind == "architecture":
        st.caption(
            "End-to-end stack from the project README — blocks colored by platform "
            "(GCP blue, Snowflake cyan, Qdrant violet, agents teal)."
        )
        st.markdown(_architecture_html(), unsafe_allow_html=True)
    else:
        st.caption(
            "LangGraph fail-closed pipeline for POST /v1/match — "
            "any agent error short-circuits to END failed."
        )
        st.markdown(_agents_html(), unsafe_allow_html=True)
