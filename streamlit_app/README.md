# TrialMatch clinician demo (Streamlit)

Thin UI for demos: guest login → pick a preset patient/note → `POST /v1/match` on the
private GKE API → render ranked trials. Matching, Snowflake, and Qdrant stay on the backend.

## Prerequisites

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

## Install & run

```bash
cd /workspace
pip install -r streamlit_app/requirements.txt

mkdir -p .streamlit
cp streamlit_app/secrets.toml.example .streamlit/secrets.toml
# edit DEMO_GUEST_USERNAME / DEMO_GUEST_PASSWORD / TRIALMATCH_API_BASE_URL

streamlit run streamlit_app/app.py --server.address 0.0.0.0 --server.port 8501
```

Open the printed local URL. Sign in with the guest credentials from secrets.

## Environment variables

| Name | Purpose | Default |
|------|---------|---------|
| `DEMO_GUEST_USERNAME` | Guest login user | (required) |
| `DEMO_GUEST_PASSWORD` | Guest login password | (required) |
| `TRIALMATCH_API_BASE_URL` | FastAPI base URL | `http://127.0.0.1:18080` |

Secrets in `.streamlit/secrets.toml` override env when present. Do not commit `.streamlit/secrets.toml`.

## Demo flow

1. Sign in as guest.
2. Choose one of ~10 presets (or override patient ID / note).
3. Click **Find matching trials** (spinner while backend runs; timeout ~180s).
4. Review justification, ranked NCT cards (CT.gov links), hits/misses, audit metadata.

## Sharing with someone else

This app is **not** deployed on GKE by default. For a private demo:

- Run Streamlit on a machine you control,
- Keep the API port-forward/tunnel up,
- Share the Streamlit URL **and** guest credentials over a secure channel,
- Remind guests this is synthetic/demo data only.

## Files

| File | Role |
|------|------|
| `app.py` | Login + workspace + results |
| `api_client.py` | `GET /healthz`, `POST /v1/match` |
| `presets.json` | Demo patient IDs + notes |
| `styles.css` | Clinical slate/teal theme |
| `secrets.toml.example` | Credential / API URL template |
