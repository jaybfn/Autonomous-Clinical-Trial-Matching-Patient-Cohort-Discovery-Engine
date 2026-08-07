"""TrialMatch clinician demo — Streamlit UI (thin client over FastAPI)."""

from __future__ import annotations

import html
import json
import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from api_client import TrialMatchApiError, healthz, match_patient  # noqa: E402

PRESETS_PATH = APP_DIR / "presets.json"
STYLES_PATH = APP_DIR / "styles.css"


def _secret(name: str, default: str = "") -> str:
    """Prefer Streamlit secrets, then environment variables."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:  # noqa: BLE001 — secrets.toml may be absent
        pass
    return os.environ.get(name, default)


def _api_base() -> str:
    return _secret("TRIALMATCH_API_BASE_URL", "http://127.0.0.1:18080").rstrip("/")


def _guest_creds() -> tuple[str, str]:
    user = _secret("DEMO_GUEST_USERNAME", "")
    password = _secret("DEMO_GUEST_PASSWORD", "")
    return user, password


def _load_css() -> None:
    if STYLES_PATH.is_file():
        css = STYLES_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _load_presets() -> list[dict[str, str]]:
    with PRESETS_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list) or not data:
        raise RuntimeError("presets.json must be a non-empty list")
    return data


def _escape(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _chips(values: list[Any], *, kind: str) -> str:
    if not values:
        return '<span class="tm-meta">None</span>'
    cls = "tm-chip-hit" if kind == "hit" else "tm-chip-miss"
    parts = [f'<span class="tm-chip {cls}">{_escape(v)}</span>' for v in values if str(v).strip()]
    return f'<div class="tm-chips">{"".join(parts)}</div>'


def _render_login() -> None:
    st.markdown(
        """
        <div class="tm-shell tm-login-card">
          <div class="tm-hero">
            <p class="tm-brand">TrialMatch</p>
            <p class="tm-sub">
              Guest access for clinician demos. Matching runs on the private API —
              this UI only submits and displays results.
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    expected_user, expected_password = _guest_creds()
    if not expected_user or not expected_password:
        st.error(
            "Demo credentials are not configured. Set DEMO_GUEST_USERNAME and "
            "DEMO_GUEST_PASSWORD (env or `.streamlit/secrets.toml`)."
        )
        return

    with st.form("login_form"):
        username = st.text_input("Guest username", autocomplete="username")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            if username == expected_user and password == expected_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid username or password.")


def _render_trial_card(rank: int, item: dict[str, Any]) -> None:
    nct = str(item.get("nct_id") or "")
    score = float(item.get("score") or 0.0)
    evidence = item.get("evidence") or {}
    if not isinstance(evidence, dict):
        evidence = {}
    title = str(evidence.get("title") or "Untitled trial")
    vector_score = evidence.get("vector_score")
    condition_hits = list(evidence.get("condition_hits") or [])
    condition_misses = list(evidence.get("condition_misses") or [])
    lab_hits = list(evidence.get("lab_hits") or [])
    lab_misses = list(evidence.get("lab_misses") or [])
    pct = max(0.0, min(score, 1.0)) * 100.0
    nct_url = f"https://clinicaltrials.gov/study/{nct}" if nct else "#"
    safe_url = _escape(nct_url)
    safe_nct = _escape(nct)

    vector_line = ""
    if vector_score is not None:
        try:
            vector_line = f'<div class="tm-meta">Vector score: {float(vector_score):.3f}</div>'
        except (TypeError, ValueError):
            vector_line = ""

    st.markdown(
        f"""
        <div class="tm-trial">
          <div class="tm-trial-head">
            <div class="tm-nct">
              #{rank} ·
              <a href="{safe_url}" target="_blank" rel="noopener noreferrer">
                {safe_nct}
              </a>
            </div>
            <div class="tm-score">{pct:.1f}%</div>
          </div>
          <div class="tm-title">{_escape(title)}</div>
          <div class="tm-bar"><span style="width:{pct:.2f}%"></span></div>
          {vector_line}
          <div class="tm-section-label">Condition hits</div>
          {_chips(condition_hits, kind="hit")}
          <div class="tm-section-label">Condition misses</div>
          {_chips(condition_misses[:8], kind="miss")}
          <div class="tm-section-label">Lab hits</div>
          {_chips(lab_hits, kind="hit")}
          <div class="tm-section-label">Lab misses (sample)</div>
          {_chips(lab_misses[:8], kind="miss")}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_results(payload: dict[str, Any]) -> None:
    status = str(payload.get("status") or "failed")
    ok = status.lower() == "ok"
    badge_cls = "tm-badge-ok" if ok else "tm-badge-fail"
    badge_label = "Match complete" if ok else "Match failed"
    patient_id = _escape(payload.get("patient_id"))
    correlation_id = _escape(payload.get("correlation_id"))
    justification = payload.get("justification_summary")
    error = payload.get("error")
    matches = payload.get("matches") or []

    just_html = ""
    if justification:
        just_html = f'<div class="tm-justification">{_escape(justification)}</div>'
    err_html = ""
    if error:
        err_html = (
            '<div class="tm-meta" style="color:var(--tm-fail);margin-top:0.75rem;">'
            f"Error: {_escape(error)}</div>"
        )

    st.markdown(
        f"""
        <div class="tm-panel">
          <span class="tm-badge {badge_cls}">{badge_label}</span>
          <div class="tm-meta">
            Patient <code>{patient_id}</code>
            · Correlation <code>{correlation_id}</code>
          </div>
          {just_html}
          {err_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if matches:
        st.markdown("### Ranked trial recommendations")
        for i, item in enumerate(matches, start=1):
            if isinstance(item, dict):
                _render_trial_card(i, item)

    with st.expander("Audit & pipeline metadata"):
        st.json(
            {
                "written_match_ids": payload.get("written_match_ids") or [],
                "agent_versions": payload.get("agent_versions") or {},
                "content_hash": payload.get("content_hash"),
                "match_count": len(matches),
            }
        )


def _render_workspace() -> None:
    presets = _load_presets()
    labels = [f"{p['label']}  ·  {p['patient_id'][:8]}…" for p in presets]
    by_label = dict(zip(labels, presets, strict=True))

    st.markdown(
        """
        <div class="tm-shell">
          <div class="tm-hero">
            <p class="tm-brand">TrialMatch</p>
            <p class="tm-sub">
              Select a demo patient, review the clinical note, and request ranked
              trial matches from the private backend.
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("**Session**")
        st.caption(f"API: `{_api_base()}`")
        if st.button("Check API health"):
            try:
                body = healthz(_api_base())
                st.success(f"API healthy: {body}")
            except TrialMatchApiError as exc:
                st.error(str(exc))
        if st.button("Sign out"):
            st.session_state.clear()
            st.rerun()

    st.markdown('<div class="tm-panel">', unsafe_allow_html=True)
    selected_label = st.selectbox("Demo patient", labels, index=0)
    preset = by_label[selected_label]

    if st.session_state.get("preset_id") != preset["id"]:
        st.session_state["preset_id"] = preset["id"]
        st.session_state["note_text"] = preset["note_text"]
        st.session_state["patient_id_input"] = preset["patient_id"]

    patient_id = st.text_input(
        "Patient ID",
        key="patient_id_input",
        help="Override the preset UUID if needed.",
    )
    note_text = st.text_area(
        "Clinical note",
        key="note_text",
        height=140,
        help="Sent to the backend only. The API does not echo note text.",
    )
    run = st.button("Find matching trials", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if run:
        if not patient_id.strip() or not note_text.strip():
            st.warning("Patient ID and clinical note are required.")
        else:
            with st.spinner("Running compliance → parser → matcher → auditor on the backend…"):
                try:
                    result = match_patient(
                        _api_base(),
                        patient_id=patient_id,
                        note_text=note_text,
                    )
                    st.session_state["last_result"] = result
                except TrialMatchApiError as exc:
                    st.session_state["last_result"] = None
                    st.error(str(exc))

    if st.session_state.get("last_result"):
        _render_results(st.session_state["last_result"])

    st.markdown(
        """
        <p class="tm-footer-note">
          Demo only — synthetic patients / open trial registry data.
          Not a clinical decision system. Guest login protects casual access;
          keep the API tunnel private.
        </p>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="TrialMatch · Clinician Demo",
        page_icon="🩺",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    _load_css()
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        _render_login()
        return
    _render_workspace()


if __name__ == "__main__":
    main()
