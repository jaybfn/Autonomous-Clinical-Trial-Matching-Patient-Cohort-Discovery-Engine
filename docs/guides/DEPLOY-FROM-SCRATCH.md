# Deploy TrialMatch from scratch (new GCP account)

**One document to rebuild the full stack** on a new Google Cloud project: Terraform → private GKE → Snowflake data (sample or full) → Qdrant trials → public API + Streamlit Cloud.

Use this when migrating to another GCP account or reproducing the demo environment. Specialized deep-dives stay in the linked runbooks; this file is the ordered checklist.

---

## Table of contents

1. [What you end up with](#1-what-you-end-up-with)
2. [Fill in your constants](#2-fill-in-your-constants)
3. [Prerequisites](#3-prerequisites)
4. [Phase 0 — Clone and auth](#4-phase-0--clone-and-auth)
5. [Phase 1 — Terraform (VPC, GKE, bastion, secrets shells)](#5-phase-1--terraform-vpc-gke-bastion-secrets-shells)
6. [Phase 2 — Bastion + kubectl](#6-phase-2--bastion--kubectl)
7. [Phase 3 — Snowflake (account, keypair, SQL)](#7-phase-3--snowflake-account-keypair-sql)
8. [Phase 4 — Secrets into GCP + ConfigMap](#8-phase-4--secrets-into-gcp--configmap)
9. [Phase 5 — Build API image and deploy workloads](#9-phase-5--build-api-image-and-deploy-workloads)
10. [Phase 6 — Load patient data (sample vs full)](#10-phase-6--load-patient-data-sample-vs-full)
11. [Phase 7 — Index trials into Qdrant](#11-phase-7--index-trials-into-qdrant)
12. [Phase 8 — Prove match via bastion tunnel](#12-phase-8--prove-match-via-bastion-tunnel)
13. [Phase 9 — Public Ingress + API key](#13-phase-9--public-ingress--api-key)
14. [Phase 10 — Streamlit (Cloud or local)](#14-phase-10--streamlit-cloud-or-local)
15. [Checklist summary](#15-checklist-summary)
16. [Pitfalls we hit (read before you apply)](#16-pitfalls-we-hit-read-before-you-apply)
17. [Safety rules](#17-safety-rules)
18. [Related docs](#18-related-docs)

---

## 1. What you end up with

```text
Colleague browser
       │
       ▼
Streamlit Cloud  ──POST /v1/match + X-API-Key──►  GCE Ingress (public IP)
                                                       │
                                                       ▼
                                              trialmatch-api (GKE)
                                                 ├─► Snowflake (patients / marts / audit)
                                                 ├─► Qdrant (trial vectors)
                                                 └─► Ollama (parser LLM)
```

Developers can still use bastion `port-forward` instead of Ingress.

---

## 2. Fill in your constants

Copy this block and replace every value. Use the replacements in **all** commands below.

```bash
# === EDIT THESE ===
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export ZONE="us-central1-a"                    # bastion + qdrant disk zone
export YOUR_GOOGLE_USER="user:you@gmail.com"  # must match gcloud auth login

export SNOWFLAKE_ACCOUNT="ORG-ACCOUNT"        # e.g. TRKSNJS-AL41445 (full identifier)
export SNOWFLAKE_USER="YOUR_SF_LOGIN"         # e.g. JAYBFN
export SNOWFLAKE_APP_USER="TRIALMATCH_APP"    # optional dedicated app user; or reuse login

export TF_STATE_BUCKET="${PROJECT_ID}-tf-state"
export IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/trialmatch-docker/trialmatch-api:0.1.0"

# Generated later — leave empty for now
export TRIALMATCH_API_KEY=""
export INGRESS_IP=""
```

Update these repo files to match (never commit real secrets):

| File | What to change |
|------|----------------|
| `infra/terraform/envs/dev/terraform.tfvars` | `project_id`, `bastion_iap_members`, `secret_ids` |
| `infra/terraform/envs/dev/backend.hcl` | `bucket`, `prefix = "trialmatch/dev"` |
| `k8s/api/deployment.yaml` | `GCP_PROJECT_ID`, image project path |
| `k8s/api/configmap.yaml` | `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, … |
| `.env` (local only, gitignored) | Same Snowflake + `GCP_PROJECT_ID` |

---

## 3. Prerequisites

- [ ] New (or empty) **GCP project** with billing enabled; your Google account is Owner
- [ ] [Snowflake](https://signup.snowflake.com/) account with `ACCOUNTADMIN` (or equivalent)
- [ ] Laptop or Dev Container with: `git`, Docker, `gcloud`, Terraform, Python 3.11+
- [ ] Cursor/VS Code **Dev Containers** recommended (see `.devcontainer/`)
- [ ] GitHub repo access (for Streamlit Cloud later)

---

## 4. Phase 0 — Clone and auth

```bash
git clone https://github.com/jaybfn/Autonomous-Clinical-Trial-Matching-Patient-Cohort-Discovery-Engine.git
cd Autonomous-Clinical-Trial-Matching-Patient-Cohort-Discovery-Engine

# Dev Container: "Reopen in Container", then:

gcloud auth login
gcloud auth application-default login
gcloud config set project "${PROJECT_ID}"

pip install -e ".[dev,runtime]"
cp .env.example .env
# edit .env: GCP_PROJECT_ID, Snowflake placeholders

make test   # optional sanity check
```

---

## 5. Phase 1 — Terraform (VPC, GKE, bastion, secrets shells)

### 1a. State bucket (once per project)

```bash
gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${TF_STATE_BUCKET}"
gsutil versioning set on "gs://${TF_STATE_BUCKET}"
```

### 1b. Configure Terraform

```bash
cd infra/terraform/envs/dev
cp terraform.tfvars.example terraform.tfvars
cp backend.hcl.example backend.hcl
```

Edit **`terraform.tfvars`**:

```hcl
project_id = "your-gcp-project-id"
# ... keep defaults or adjust sizes ...

secret_ids = [
  "trialmatch-snowflake-private-key",
  "trialmatch-snowflake-passphrase",
  "trialmatch-api-key",
]

bastion_iap_members = [
  "user:you@gmail.com",   # REAL email — never leave YOU@example.com
]
```

Edit **`backend.hcl`**:

```hcl
bucket = "your-gcp-project-id-tf-state"
prefix = "trialmatch/dev"    # REQUIRED — empty prefix causes 409 "already exists" on re-apply
```

```bash
terraform init -reconfigure -backend-config=backend.hcl
terraform plan    # expect creates, not 60+ re-creates of existing resources
terraform apply
```

Capture outputs:

```bash
terraform output
terraform output -raw ingress_static_ip_address   # reserved IP (may differ until Ingress binds it)
terraform output -raw bastion_iap_ssh_command
terraform output -json nat_static_ips             # for optional Snowflake network policy
```

**Critical:** always `terraform init -backend-config=backend.hcl` with `prefix = "trialmatch/dev"`. Wrong/empty prefix → empty state → Terraform tries to recreate everything → `409 already exists`.

---

## 6. Phase 2 — Bastion + kubectl

### Laptop → bastion

```bash
# from repo root
make bastion-ssh
# or:
gcloud compute ssh trialmatch-bastion \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --tunnel-through-iap
```

### On bastion — kubeconfig + repo clone

```bash
export USE_GKE_GCLOUD_AUTH_PLUGIN=True
gcloud config set project "${PROJECT_ID}"
gcloud container clusters get-credentials trialmatch-gke \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --internal-ip

kubectl get nodes

cd ~
git clone https://github.com/jaybfn/Autonomous-Clinical-Trial-Matching-Patient-Cohort-Discovery-Engine.git
cd Autonomous-Clinical-Trial-Matching-Patient-Cohort-Discovery-Engine
git checkout main && git pull
```

**Rule:** `kubectl` / Ingress / rollout → **bastion**. `docker build/push`, Terraform, Secret Manager upload, data scripts → **laptop / Dev Container**.

---

## 7. Phase 3 — Snowflake (account, keypair, SQL)

### 3a. Account identifier

In Snowflake UI → Account details. Use the **full** identifier (`ORG-ACCOUNT`), not the short name alone.

### 3b. RSA keypair (laptop)

```bash
mkdir -p ~/snowflake-keys && chmod 700 ~/snowflake-keys
cd ~/snowflake-keys
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
chmod 600 rsa_key.p8

# one-line public key body for SQL:
grep -v 'PUBLIC KEY' rsa_key.pub | tr -d '\n'; echo
```

### 3c. Attach public key + run SQL (Snowflake worksheets, `ACCOUNTADMIN`)

```sql
ALTER USER YOUR_SF_LOGIN SET RSA_PUBLIC_KEY='MIIBIjAN...';  -- body only, no BEGIN/END

-- Then run repo files in order:
--   snowflake/sql/01_roles.sql
--   GRANT ROLE AGENT_READ_ROLE TO USER YOUR_SF_LOGIN;
--   GRANT ROLE AUDIT_WRITE_ROLE TO USER YOUR_SF_LOGIN;
--   snowflake/sql/03_schemas_tables.sql
-- Optional later: snowflake/sql/02_network_policy.sql (NAT IPs from terraform output)
```

### 3d. Local `.env` (laptop, gitignored)

```bash
GCP_PROJECT_ID=your-gcp-project-id
SNOWFLAKE_ACCOUNT=ORG-ACCOUNT
SNOWFLAKE_USER=YOUR_SF_LOGIN
SNOWFLAKE_WAREHOUSE=TRIALMATCH_WH
SNOWFLAKE_DATABASE=TRIALMATCH_DEV
SNOWFLAKE_SCHEMA=MARTS
SNOWFLAKE_PRIVATE_KEY_PATH=/home/vscode/snowflake-keys/rsa_key.p8   # absolute path
```

Also create `~/.dbt/profiles.yml` from `dbt/profiles.yml.example`.

---

## 8. Phase 4 — Secrets into GCP + ConfigMap

### 4a. Upload Snowflake private key (laptop)

```bash
gcloud secrets versions add trialmatch-snowflake-private-key \
  --project="${PROJECT_ID}" \
  --data-file="$HOME/snowflake-keys/rsa_key.p8"
```

(Terraform only creates empty secret **shells**; values are always out-of-band.)

### 4b. ConfigMap (bastion)

Edit `k8s/api/configmap.yaml` with your Snowflake account/user, then:

```bash
kubectl apply -f k8s/api/configmap.yaml
kubectl apply -f k8s/serviceaccounts/trialmatch-ksa.yaml
```

Do **not** put PEM material or API keys in the ConfigMap.

---

## 9. Phase 5 — Build API image and deploy workloads

### 5a. Build / push (laptop)

Update `k8s/api/deployment.yaml` image + `GCP_PROJECT_ID` for the new project.

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
docker build -t "${IMAGE}" .
docker push "${IMAGE}"
```

### 5b. Deploy Qdrant, Ollama, API (bastion)

```bash
kubectl apply -f k8s/qdrant/deployment.yaml -f k8s/qdrant/service.yaml
kubectl apply -f k8s/ollama/deployment.yaml -f k8s/ollama/service.yaml
kubectl apply -f k8s/api/configmap.yaml -f k8s/api/deployment.yaml -f k8s/api/service.yaml

kubectl -n trialmatch get pods -w
# Wait until ollama has pulled the model (logs show success) and API is Ready
kubectl -n trialmatch logs -l app.kubernetes.io/name=trialmatch-api --tail=50
# expect: startup: live graph_runner ready
```

First Ollama boot downloads ~1GB+ — be patient.

---

## 10. Phase 6 — Load patient data (sample vs full)

Matching needs rows in Snowflake **MARTS** (via dbt) for the `patient_id` you query.

### Path A — Tiny samples (fast smoke / CI-shaped)

Uses committed files under `data/synthea/samples/`.

```bash
# laptop, with .env + keypair working
python scripts/load_synthea_samples_to_snowflake.py

cd dbt && dbt run && cd ..
```

Then use a `patient_id` that appears in `data/synthea/samples/patients.csv` (or Streamlit presets after you swap IDs).

### Path B — Full Synthea dump (production-scale demo)

1. Obtain / download the bulk Synthea CSVs into `data/raw/` (gitignored). Example layout used in this project: HuggingFace Synthea dump under `data/raw/synthea-hf/...`.

2. Prepare slim CSVs + load:

```bash
# --limit N for a subset; --limit 0 = all rows (long-running)
python scripts/prepare_synthea_for_snowflake.py --limit 0

python scripts/put_copy_synthea_to_snowflake.py --truncate
# PUT + COPY into RAW.RAW_SYNTHEA_*

cd dbt && dbt run && cd ..
```

3. Sanity-check in Snowflake:

```sql
SELECT COUNT(*) FROM TRIALMATCH_DEV.RAW.RAW_SYNTHEA_PATIENTS;
SELECT COUNT(*) FROM TRIALMATCH_DEV.MARTS.DIM_TRIAL_ELIGIBILITY_FEATURES;
```

**Good demo patient** (after full load — UUID present in Synthea dump):

```text
7cd119b6-4aa3-4d17-be38-03311e40f1c0
```

Streamlit presets in `streamlit_app/presets.json` should use IDs that exist in your loaded mart.

---

## 11. Phase 7 — Index trials into Qdrant

Qdrant is in-cluster. From the laptop you need a **double tunnel**.

### Terminal 1 — bastion

```bash
kubectl -n trialmatch port-forward svc/qdrant 6333:6333
```

### Terminal 2 — laptop SSH forward

```bash
gcloud compute ssh trialmatch-bastion \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --tunnel-through-iap \
  -- -N -L 6333:127.0.0.1:6333
```

### Terminal 3 — fetch + index (laptop)

```bash
curl -sS -m 5 http://127.0.0.1:6333/readyz   # expect ready

# Demo default: recruiting diabetes (~2k studies)
python -u scripts/fetch_clinicaltrials_eligibility.py \
  --query "diabetes" \
  --status RECRUITING \
  --max-studies 0

python scripts/index_trials_to_qdrant.py \
  --sample-path data/raw/clinicaltrials/eligibility.jsonl \
  --live
# expect indexed ~1953 for recruiting-diabetes
```

| Goal | Fetch flags |
|------|-------------|
| Demo default | `--query "diabetes" --status RECRUITING` |
| Larger diabetes set | `--query "diabetes" --status "" --max-studies 0` |
| Tighter T2D | `--query "type 2 diabetes" --status RECRUITING` |

`--max-studies 0` = paginate until CT.gov ends for that query (not “all of CT.gov”).

---

## 12. Phase 8 — Prove match via bastion tunnel

### Bastion

```bash
kubectl -n trialmatch port-forward svc/trialmatch-api 18080:80
```

### Laptop (optional second hop)

```bash
gcloud compute ssh trialmatch-bastion \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --tunnel-through-iap \
  -- -N -L 18080:127.0.0.1:18080
```

### Curl

```bash
curl -sS http://127.0.0.1:18080/healthz

curl -sS -m 180 -X POST http://127.0.0.1:18080/v1/match \
  -H 'content-type: application/json' \
  -d '{"patient_id":"7cd119b6-4aa3-4d17-be38-03311e40f1c0","note_text":"Type 2 diabetes"}'
```

Success: `"status":"ok"`, non-empty `matches`, `agent_versions` for compliance/parser/matcher/auditor, `written_match_ids` non-empty.

---

## 13. Phase 9 — Public Ingress + API key

Needed so **Streamlit Cloud** (public) can call the API without bastion tunnels.

### 9a. API key in Secret Manager + GKE

```bash
# laptop — ensure Terraform created shell trialmatch-api-key, then:
export TRIALMATCH_API_KEY="$(openssl rand -hex 32)"
echo -n "${TRIALMATCH_API_KEY}" | gcloud secrets versions add trialmatch-api-key \
  --project="${PROJECT_ID}" --data-file=-
echo "SAVE THIS KEY: ${TRIALMATCH_API_KEY}"
```

```bash
# bastion — same value into Kubernetes
kubectl -n trialmatch create secret generic trialmatch-api-key \
  --from-literal=api-key="${TRIALMATCH_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f k8s/api/deployment.yaml   # must include TRIALMATCH_API_KEY secretKeyRef
kubectl -n trialmatch rollout restart deploy/trialmatch-api
kubectl -n trialmatch rollout status deploy/trialmatch-api

# confirm env present (length only)
kubectl -n trialmatch exec deploy/trialmatch-api -- printenv TRIALMATCH_API_KEY | wc -c
```

Empty `TRIALMATCH_API_KEY` = auth off. Non-empty = require header `X-API-Key` on `POST /v1/match`. Probes `/healthz` and `/readyz` stay open.

### 9b. Ingress + backend timeout

Match often exceeds GCE’s default **30s** timeout — apply BackendConfig (180s):

```bash
# bastion
kubectl apply -f k8s/api/backendconfig.yaml
kubectl apply -f k8s/api/service.yaml      # annotation → BackendConfig
kubectl apply -f k8s/api/ingress.yaml
kubectl -n trialmatch get ingress trialmatch-api -w
# wait until ADDRESS is populated
```

```bash
# laptop — prefer Ingress ADDRESS for demos
kubectl ...   # or from bastion: kubectl get ingress -o wide
export INGRESS_IP="<ADDRESS from ingress>"   # e.g. 34.54.x.x

# Note: terraform output ingress_static_ip_address may still be RESERVED /
# unused if the LB bound a different ephemeral IP. Use the Ingress ADDRESS.
```

### 9c. Smoke from any laptop (no bastion)

```bash
curl -sS "http://${INGRESS_IP}/healthz"

curl -sS -o /dev/null -w "%{http_code}\n" -X POST "http://${INGRESS_IP}/v1/match" \
  -H "content-type: application/json" \
  -d '{"patient_id":"p","note_text":"diabetes"}'
# expect 401

curl -sS -m 180 -X POST "http://${INGRESS_IP}/v1/match" \
  -H "content-type: application/json" \
  -H "X-API-Key: ${TRIALMATCH_API_KEY}" \
  -d '{"patient_id":"7cd119b6-4aa3-4d17-be38-03311e40f1c0","note_text":"Type 2 diabetes"}'
# expect 200 + matches
```

Optional later: set `ingress_domain` in Terraform, DNS A record, managed HTTPS → use `https://api.yourdomain`.

---

## 14. Phase 10 — Streamlit (Cloud or local)

### Streamlit Community Cloud (colleagues)

1. Push `main` (or your deploy branch) to GitHub.
2. [share.streamlit.io](https://share.streamlit.io) → New app → this repo → branch `main`.
3. **Main file path:** `streamlit_app/app.py`
4. **Secrets** (Cloud UI):

```toml
DEMO_GUEST_USERNAME = "guest"
DEMO_GUEST_PASSWORD = "share-out-of-band-only"
TRIALMATCH_API_BASE_URL = "http://YOUR_INGRESS_IP"
TRIALMATCH_API_KEY = "same-as-GKE-secret"
```

5. Deploy → open `*.streamlit.app` → guest login → pick preset → **Find matching trials**.

Guest login is **not** API security; the API key is. Colleagues never see the key.

### Local Streamlit (developer)

```bash
mkdir -p .streamlit
cp streamlit_app/secrets.toml.example .streamlit/secrets.toml
# For public API: BASE_URL=http://INGRESS_IP + API_KEY
# For tunnel only: BASE_URL=http://127.0.0.1:18080 (+ API_KEY if GKE enforces it)

pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/app.py --server.address 0.0.0.0 --server.port 8501
```

---

## 15. Checklist summary

| # | Phase | Where | Done when |
|---|--------|-------|-----------|
| 0 | Clone + `gcloud auth` | Laptop | `gcloud config get-value project` correct |
| 1 | Terraform apply | Laptop | GKE + bastion + secret shells exist |
| 2 | Bastion kubectl | Bastion | `kubectl get nodes` works |
| 3 | Snowflake SQL + keypair | SF UI + laptop | Keypair login works locally |
| 4 | SM key + ConfigMap | Laptop + bastion | Pods can materialize PEM |
| 5 | Image + Qdrant/Ollama/API | Both | `live graph_runner ready` |
| 6a or 6b | Sample or full Synthea + dbt | Laptop | Mart row counts > 0 |
| 7 | CT.gov → Qdrant | Laptop + tunnels | `points_count` ~2k (demo) |
| 8 | Tunnel `/v1/match` | Bastion/laptop | `status: ok` + matches |
| 9 | Ingress + API key | Both | Public healthz + 401/200 match |
| 10 | Streamlit Cloud | Browser | Guest can run presets |

---

## 16. Pitfalls we hit (read before you apply)

| Symptom | Cause | Fix |
|---------|--------|-----|
| Terraform `409 already exists` for VPC, GKE, … | State backend **missing `prefix`** or wrong bucket | `backend.hcl` with `prefix = "trialmatch/dev"` + `terraform init -reconfigure` |
| Plan destroys bastion IAP for your user | `bastion_iap_members = ["user:YOU@example.com"]` or empty | Put your real `user:you@gmail.com` in `terraform.tfvars` **before** apply |
| `kubectl: command not found` | Ran cluster commands on laptop | Use bastion |
| Bastion `git pull` / `deployment unchanged` | Wrong branch / old commit | `git checkout main && git pull` then re-apply |
| Reserved Ingress IP ≠ Ingress ADDRESS; curl reset | Static IP still `RESERVED`; LB using another IP | Use **Ingress ADDRESS** for demos |
| Match via Ingress returns **502** ~30s | GCE default backend timeout | Apply `k8s/api/backendconfig.yaml` (180s) + Service annotation |
| Match without key still **200** | Old API image without auth | Rebuild/push image + rollout restart |
| Local Streamlit 401 after enabling key | Secrets missing `TRIALMATCH_API_KEY` | Add same key to `.streamlit/secrets.toml` |
| Snowflake HTTP 404 | Used short account name | Use full `ORG-ACCOUNT` identifier |
| Ruff CI vs pre-commit fight on imports | `streamlit_app` not known-first-party | Already fixed in `pyproject.toml` `[tool.ruff.lint.isort]` |

---

## 17. Safety rules

1. Never commit `.env`, `rsa_key.p8`, `.streamlit/secrets.toml`, or filled `secret-api-key.yaml`.
2. Never put secrets in ConfigMaps or git.
3. Rotate `TRIALMATCH_API_KEY` if leaked (SM version + K8s Secret + Streamlit secrets).
4. Public Ingress is scannable — API key required; add HTTPS/domain for anything beyond a short demo.
5. Synthetic / open data only — do not paste real PHI into notes on a public UI.
6. Do not attach a Snowflake network policy that locks your UI user out of worksheets.

---

## 18. Related docs

| Doc | When to open it |
|-----|-----------------|
| [getting-started-live-path.md](getting-started-live-path.md) | Beginner-friendly plumbing narrative |
| [bastion-access.md](../runbooks/bastion-access.md) | IAP SSH / private GKE details |
| [snowflake-live-api.md](../runbooks/snowflake-live-api.md) | SM materialization + live API |
| [public-api-streamlit-cloud.md](../runbooks/public-api-streamlit-cloud.md) | Ingress + API key + Cloud secrets |
| [workload-identity.md](../security/workload-identity.md) | GSA ↔ KSA binding |
| [streamlit_app/README.md](../../streamlit_app/README.md) | UI-only runbook |
| [data/README.md](../../data/README.md) | Sample vs raw data layout |
| Root [README.md](../../README.md) | Architecture + short data-loading section |

---

## Document history

Captures the full path used to stand up private GKE + Snowflake + Qdrant + public Ingress + Streamlit Cloud (including sample vs full Synthea load and recruiting-diabetes trial index). Update when default image tag, LLM model, or Ingress/TLS defaults change.
