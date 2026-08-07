# TrialMatch clinician demo (Streamlit)

Thin UI for demos: guest login → pick a preset patient/note → `POST /v1/match` →
render ranked trials. Matching, Snowflake, and Qdrant stay on the backend.

Two ways to reach the API:

| Path | Who | `TRIALMATCH_API_BASE_URL` | API key |
|------|-----|---------------------------|---------|
| **Local tunnel** | Developers | `http://127.0.0.1:18080` | Empty unless GKE has a key set |
| **Streamlit Cloud** | Colleagues | `http://<ingress-ip>` (or HTTPS domain) | Same as GKE `TRIALMATCH_API_KEY` |

Full ops checklist: [docs/runbooks/public-api-streamlit-cloud.md](../docs/runbooks/public-api-streamlit-cloud.md).

**New GCP account / full stack rebuild** (Terraform → data → Ingress → this app): [docs/guides/DEPLOY-FROM-SCRATCH.md](../docs/guides/DEPLOY-FROM-SCRATCH.md).

## Prerequisites (local tunnel)

1. API reachable from this machine (typical bastion port-forward):

```bash
# on bastion
kubectl -n trialmatch port-forward svc/trialmatch-api 18080:80
```

If Streamlit runs in the Dev Container, also SSH-tunnel that port (same pattern as Qdrant):

```bash
gcloud compute ssh trialmatch-bastion \
  --project=autonomous-agent-503517 \
  --zone=us-central1-a \
  --tunnel-through-iap \
  -- -N -L 18080:127.0.0.1:18080
```

2. Guest credentials configured (env **or** Streamlit secrets).

## Install & run (local)

```bash
cd /workspace
pip install -r streamlit_app/requirements.txt

mkdir -p .streamlit
cp streamlit_app/secrets.toml.example .streamlit/secrets.toml
# edit DEMO_GUEST_USERNAME / DEMO_GUEST_PASSWORD / TRIALMATCH_API_BASE_URL
# set TRIALMATCH_API_KEY only if the API enforces it

streamlit run streamlit_app/app.py --server.address 0.0.0.0 --server.port 8501
```

Open the printed local URL. Sign in with the guest credentials from secrets.

## Streamlit Cloud

1. Connect the GitHub repo; main file `streamlit_app/app.py`.
2. Secrets in the Cloud UI:

```toml
DEMO_GUEST_USERNAME = "guest"
DEMO_GUEST_PASSWORD = "<share-out-of-band>"
TRIALMATCH_API_BASE_URL = "http://<STATIC_IP>"
TRIALMATCH_API_KEY = "<same-as-GKE>"
```

3. Share only the Streamlit URL + guest password with colleagues.
   Guest login is **not** API security; the API key is.

## Environment variables

| Name | Purpose | Default |
|------|---------|---------|
| `DEMO_GUEST_USERNAME` | Guest login user | (required) |
| `DEMO_GUEST_PASSWORD` | Guest login password | (required) |
| `TRIALMATCH_API_BASE_URL` | FastAPI base URL | `http://127.0.0.1:18080` |
| `TRIALMATCH_API_KEY` | Sent as `X-API-Key` on match | empty (no header) |

Secrets in `.streamlit/secrets.toml` override env when present. Do not commit `.streamlit/secrets.toml`.

## Demo flow

1. Sign in as guest.
2. Choose one of ~10 presets (or override patient ID / note).
3. Click **Find matching trials** (spinner while backend runs; timeout ~180s).
4. Review justification, ranked NCT cards (CT.gov links), hits/misses, audit metadata.

## Files

| File | Role |
|------|------|
| `app.py` | Login + tabs (match / architecture / agents) |
| `diagrams.py` | Themed Mermaid (GCP / Snowflake / Qdrant / agents) |
| `api_client.py` | `GET /healthz`, `POST /v1/match` (+ optional `X-API-Key`) |
| `presets.json` | Demo patient IDs + notes |
| `styles.css` | Clinical slate/teal theme + diagram legend |
| `secrets.toml.example` | Credential / API URL / API key template |
