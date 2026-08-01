# Getting started: from clone to end-to-end live matching

This guide walks a new engineer from **cloning the repo on a laptop** to a **working live API** on private GKE that talks to Snowflake, Qdrant, and an open-source LLM (Ollama).

It is written for people with **little or no prior cloud, Kubernetes, networking, or security experience**. Concepts are explained in plain language before each set of commands.

> **Audience:** onboarding, pair-programming, and “how did we get this working?” reference.
> **Related shorter runbooks:** [bastion-access](../runbooks/bastion-access.md), [snowflake-live-api](../runbooks/snowflake-live-api.md), [workload-identity](../security/workload-identity.md).

---

## Table of contents

1. [What you are building (30-second picture)](#1-what-you-are-building-30-second-picture)
2. [Glossary (read once)](#2-glossary-read-once)
3. [Mental model of the live path](#3-mental-model-of-the-live-path)
4. [Prerequisites checklist](#4-prerequisites-checklist)
5. [Part A — Laptop / Dev Container setup](#5-part-a--laptop--dev-container-setup)
6. [Part B — Why you cannot talk to the cluster from your laptop](#6-part-b--why-you-cannot-talk-to-the-cluster-from-your-laptop)
7. [Part C — Bastion SSH (door into the private network)](#7-part-c--bastion-ssh-door-into-the-private-network)
8. [Part D — Snowflake account, keypair, roles, and tables](#8-part-d--snowflake-account-keypair-roles-and-tables)
9. [Part E — Put the private key in Google Secret Manager](#9-part-e--put-the-private-key-in-google-secret-manager)
10. [Part F — Build and push the API Docker image](#10-part-f--build-and-push-the-api-docker-image)
11. [Part G — Deploy Qdrant, Ollama, and the API (from bastion)](#11-part-g--deploy-qdrant-ollama-and-the-api-from-bastion)
12. [Part H — Configure Snowflake connection for the pods](#12-part-h--configure-snowflake-connection-for-the-pods)
13. [Part I — Prove the live path with `/v1/match`](#13-part-i--prove-the-live-path-with-v1match)
14. [Troubleshooting diary (real errors we hit and fixes)](#14-troubleshooting-diary-real-errors-we-hit-and-fixes)
15. [Success criteria and example response](#15-success-criteria-and-example-response)
16. [What comes after this guide (seeding data)](#16-what-comes-after-this-guide-seeding-data)
17. [Safety rules (do not skip)](#17-safety-rules-do-not-skip)

---

## 1. What you are building (30-second picture)

**TrialMatch** is an API that:

1. Takes a patient note (text).
2. Scrubs obvious PII (**Compliance** agent).
3. Extracts clinical features with an LLM (**Parser**).
4. Looks for matching clinical trials using Snowflake + vector search (**Matcher**).
5. Writes an audit justification to Snowflake (**Auditor**).

All of that runs as containers on **Google Kubernetes Engine (GKE)** in a **private** network. Your laptop is outside that network, so you use a small jump host called a **bastion** to reach the cluster.

```text
Laptop / Dev Container          Private GCP VPC
┌──────────────────┐            ┌──────────────────────────────────────┐
│ git, docker,     │  IAP SSH   │ Bastion VM                           │
│ gcloud (you)      │ ─────────► │  kubectl ──► Private GKE             │
│                  │            │                 │                    │
│ docker push ──────────────────┼──► Artifact Registry                 │
│ secrets upload ───────────────┼──► Secret Manager                    │
└──────────────────┘            │                 │                    │
                                │         trialmatch-api pods          │
                                │           ├─► Snowflake (internet)   │
                                │           ├─► Qdrant (in-cluster)    │
                                │           └─► Ollama (in-cluster)    │
                                └──────────────────────────────────────┘
```

---

## 2. Glossary (read once)

| Term | Plain meaning |
|------|----------------|
| **GCP project** | Your Google Cloud “folder” for billing and resources. Ours: `autonomous-agent-503517`. |
| **VPC** | Private virtual network. Resources inside can talk to each other; the public internet cannot reach them unless you allow it. |
| **Private GKE** | Kubernetes cluster whose control plane has **no public IP**. You cannot run `kubectl` from home without a tunnel. |
| **Bastion** | A locked-down VM *inside* the VPC. You SSH into it (via IAP), then run `kubectl` from there. |
| **IAP** | Identity-Aware Proxy. Google checks *who you are* before allowing SSH to the bastion. No open SSH port on the internet. |
| **Workload Identity** | Pods pretend to be a Google service account **without downloading JSON keys**. Safer than storing keys in files. |
| **GSA / KSA** | Google Service Account vs Kubernetes Service Account. Bound together for Workload Identity. |
| **Secret Manager** | Google’s vault for secrets (e.g. Snowflake private key). Pods fetch at startup. |
| **ConfigMap** | Kubernetes object for non-secret config (account name, warehouse, etc.). |
| **Artifact Registry** | Google’s Docker image registry. You `docker push` images there; GKE pulls them. |
| **Snowflake account identifier** | Not just `AL41445`. Use the full form from the UI, e.g. `TRKSNJS-AL41445`. |
| **Keypair auth** | Snowflake login with RSA keys instead of a password. Public key lives in Snowflake; private key stays in Secret Manager. |
| **Ollama** | Runs open-source LLMs (e.g. Llama) locally in the cluster — no Vertex/Gemini billing required. |
| **Qdrant** | Vector database for trial similarity search. |
| **Port-forward** | Temporary tunnel: `localhost:18080` on the bastion → API service inside the cluster. |

---

## 3. Mental model of the live path

When you `POST /v1/match`, the API process (`create_live_app`) has already wired:

| Piece | Where it lives | How the pod finds it |
|-------|----------------|----------------------|
| Snowflake | Snowflake Cloud | Env vars + PEM from Secret Manager |
| Qdrant | Pod `qdrant-0` in namespace `trialmatch` | `http://qdrant.trialmatch.svc.cluster.local:6333` |
| LLM | Pod `ollama` | `http://ollama.trialmatch.svc.cluster.local:11434` (`llama3.2:1b`) |

**Important:** `/healthz` can be green even when matching is empty. A full success looks like `status: "ok"` with all four agent versions present (see [§15](#15-success-criteria-and-example-response)).

---

## 4. Prerequisites checklist

Before you start, you need:

- [ ] Access to the GitHub repo
- [ ] A Google account added to the GCP project (Owner or sufficient IAM)
- [ ] Docker Desktop (or equivalent) + Cursor/VS Code Dev Container (recommended)
- [ ] `gcloud` CLI authenticated as **your user** (not a service account)
- [ ] A Snowflake trial/account where you can run SQL as `ACCOUNTADMIN`
- [ ] Ability to generate OpenSSL RSA keys on your machine

Dev project constants used in this guide:

| Item | Value |
|------|--------|
| GCP project | `autonomous-agent-503517` |
| Region / zone (bastion) | `us-central1` / `us-central1-a` |
| Cluster | `trialmatch-gke` |
| Namespace | `trialmatch` |
| Image | `us-central1-docker.pkg.dev/autonomous-agent-503517/trialmatch-docker/trialmatch-api:0.1.0` |
| Runtime GSA | `trialmatch-runtime@autonomous-agent-503517.iam.gserviceaccount.com` |
| Cloud NAT IPs (Snowflake network policy later) | `136.112.132.174`, `34.61.252.214` |

---

## 5. Part A — Laptop / Dev Container setup

### A1. Clone the repo

```bash
git clone https://github.com/jaybfn/Autonomous-Clinical-Trial-Matching-Patient-Cohort-Discovery-Engine.git
cd Autonomous-Clinical-Trial-Matching-Patient-Cohort-Discovery-Engine
```

### A2. Open in Dev Container (recommended)

In Cursor/VS Code: **Dev Containers: Reopen in Container**.

This gives you Python, Docker, `gcloud`, and Terraform tooling without polluting your host OS.

### A3. Authenticate to Google Cloud *as yourself*

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project autonomous-agent-503517
gcloud auth list   # ACTIVE account should be you@gmail.com — NOT a *-bastion@... SA
```

### A4. Sanity-check the code

```bash
make test
```

---

## 6. Part B — Why you cannot talk to the cluster from your laptop

The GKE control plane endpoint is private (`172.16.0.2`). From the Dev Container you will see something like:

```text
dial tcp 172.16.0.2:443: connect: connection refused
```

That is **expected**, not a broken laptop.

| Place | What you do there |
|-------|-------------------|
| Laptop / Dev Container | `git`, `docker build/push`, `gcloud` IAM/APIs/secrets, Terraform |
| Bastion | `kubectl`, `port-forward`, `curl` to the API |

**Rule of thumb:** if the command talks to the *cluster*, run it on the bastion. If it talks to *Google APIs / Docker / git*, run it on your laptop.

---

## 7. Part C — Bastion SSH (door into the private network)

### C1. Short command from the repo

```bash
make bastion
# same as: bash scripts/bastion-ssh.sh
```

Equivalent long form:

```bash
gcloud compute ssh trialmatch-bastion \
  --project=autonomous-agent-503517 \
  --zone=us-central1-a \
  --tunnel-through-iap
```

Your Google user must be listed in Terraform `bastion_iap_members` (e.g. `user:you@gmail.com`).

### C2. First-time kubeconfig on the bastion

```bash
export USE_GKE_GCLOUD_AUTH_PLUGIN=True
export PROJECT=autonomous-agent-503517
export REGION=us-central1

gcloud config set project "${PROJECT}"
gcloud container clusters get-credentials trialmatch-gke \
  --region "${REGION}" \
  --project "${PROJECT}" \
  --internal-ip

kubectl get nodes
```

### C3. Clone the repo *on the bastion* too

Manifests (`k8s/...`) must be applied from a machine that can reach the API. Keep a clone on the bastion:

```bash
cd ~
git clone https://github.com/jaybfn/Autonomous-Clinical-Trial-Matching-Patient-Cohort-Discovery-Engine.git
cd Autonomous-Clinical-Trial-Matching-Patient-Cohort-Discovery-Engine
```

Later, when you push a branch from the laptop:

```bash
git fetch origin <branch-name>
git checkout <branch-name>
```

---

## 8. Part D — Snowflake account, keypair, roles, and tables

### D1. Find your real account identifier

In Snowflake UI → account menu → **Account details**. Example:

| Field | Example value |
|-------|----------------|
| Account identifier | `TRKSNJS-AL41445` ← **use this for `SNOWFLAKE_ACCOUNT`** |
| Account name | `AL41445` (alone is **not** enough — causes HTTP 404) |
| Login name | `JAYBFN` |
| Account/Server URL | `TRKSNJS-AL41445.snowflakecomputing.com` |

### D2. Generate RSA keypair (on laptop / Dev Container)

Snowflake does **not** give you a PEM. You create one:

```bash
mkdir -p ~/snowflake-keys && cd ~/snowflake-keys && chmod 700 .

# Unencrypted PKCS#8 private key (simplest for first wire-up)
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
chmod 600 rsa_key.p8
```

**Never** commit `rsa_key.p8` into the git repo.

### D3. Attach the *public* key to your Snowflake user

In Snowflake **Worksheets** (not bash!), as a role that can alter users:

```sql
-- Paste ONE LINE of public key body only (no BEGIN/END headers)
ALTER USER JAYBFN SET RSA_PUBLIC_KEY='MIIBIjANBgkqh...IDAQAB';

DESC USER JAYBFN;  -- RSA_PUBLIC_KEY_FP should be populated
```

To extract the body locally:

```bash
grep -v 'PUBLIC KEY' ~/snowflake-keys/rsa_key.pub | tr -d '\n'; echo
```

Common mistake: pasting the PEM header/footer lines (the `BEGIN` / `END` + `PUBLIC KEY` markers) into SQL → `Invalid Public key`.

### D4. Create warehouse, DB, roles, schemas (SQL files in repo)

In Snowflake Worksheets, role = **`ACCOUNTADMIN`**, run in order:

1. `snowflake/sql/01_roles.sql` — warehouse `TRIALMATCH_WH`, DB `TRIALMATCH_DEV`, roles `AGENT_READ_ROLE` / `AUDIT_WRITE_ROLE`
2. Grant roles to your user:

```sql
USE ROLE ACCOUNTADMIN;
GRANT ROLE AGENT_READ_ROLE TO USER JAYBFN;
GRANT ROLE AUDIT_WRITE_ROLE TO USER JAYBFN;
```

3. `snowflake/sql/03_schemas_tables.sql` — `RAW` / `STAGING` / `MARTS` / `AUDIT` + landing tables
   - Note: columns `"START"` / `"STOP"` are quoted because `START` is a reserved word.

4. **Network policy (optional for now):** `snowflake/sql/02_network_policy.sql`
   - Create the policy with NAT IPs, but **do not** attach it to your interactive user yet or you may lock yourself out of the Snowflake UI from home.

### D5. Matcher mart stub (needed before seeding/dbt)

Until dbt builds marts, create an empty feature table so Matcher does not 404:

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE TRIALMATCH_DEV;
CREATE SCHEMA IF NOT EXISTS MARTS;

CREATE TABLE IF NOT EXISTS MARTS.DIM_TRIAL_ELIGIBILITY_FEATURES (
  PATIENT_ID VARCHAR,
  FEATURE_TYPE VARCHAR,
  FEATURE_CODE VARCHAR,
  FEATURE_LABEL VARCHAR,
  FEATURE_START TIMESTAMP_NTZ,
  FEATURE_END DATE,
  FEATURE_VALUE FLOAT,
  FEATURE_UNITS VARCHAR
);

GRANT SELECT ON TABLE MARTS.DIM_TRIAL_ELIGIBILITY_FEATURES TO ROLE AGENT_READ_ROLE;
```

---

## 9. Part E — Put the private key in Google Secret Manager

Terraform already created **secret shells**:

- `trialmatch-snowflake-private-key`
- `trialmatch-snowflake-passphrase` (only if your PEM is encrypted)

Upload the **private** key from the **laptop** (your user has permission; the bastion SA does not):

```bash
gcloud secrets versions add trialmatch-snowflake-private-key \
  --project=autonomous-agent-503517 \
  --data-file="$HOME/snowflake-keys/rsa_key.p8"

gcloud secrets versions list trialmatch-snowflake-private-key \
  --project=autonomous-agent-503517
```

At pod startup, the API materializes this secret to
`/tmp/trialmatch/snowflake-private-key.pem` using Workload Identity (`SNOWFLAKE_PRIVATE_KEY_SM_ID`).

---

## 10. Part F — Build and push the API Docker image

Still on the **laptop / Dev Container**:

```bash
export IMAGE=us-central1-docker.pkg.dev/autonomous-agent-503517/trialmatch-docker/trialmatch-api:0.1.0

# one-time auth to Artifact Registry if needed
gcloud auth configure-docker us-central1-docker.pkg.dev

docker build -t "${IMAGE}" .
docker push "${IMAGE}"
```

The image installs runtime extras (Snowflake connector, Secret Manager client, Qdrant client, etc.) via `pip install ".[runtime]"`.

---

## 11. Part G — Deploy Qdrant, Ollama, and the API (from bastion)

On the **bastion**, in the repo clone (correct branch):

```bash
cd ~/Autonomous-Clinical-Trial-Matching-Patient-Cohort-Discovery-Engine

kubectl apply -f k8s/serviceaccounts/trialmatch-ksa.yaml
kubectl apply -f k8s/qdrant/deployment.yaml -f k8s/qdrant/service.yaml
kubectl apply -f k8s/ollama/deployment.yaml -f k8s/ollama/service.yaml
kubectl apply -f k8s/api/configmap.yaml -f k8s/api/deployment.yaml -f k8s/api/service.yaml

kubectl -n trialmatch get pods
```

### What each component does

| Manifest | Role |
|----------|------|
| `k8s/qdrant/` | Vector DB for trial criteria (`v1.18.0` image; matches modern `qdrant-client`) |
| `k8s/ollama/` | Free open LLM (`llama3.2:1b`). First boot **downloads ~1.3 GB** — wait for logs to show `success` |
| `k8s/api/` | FastAPI + LangGraph (`create_live_app`). Uses `LLM_PROVIDER=ollama` |

```bash
# Watch Ollama model pull
kubectl -n trialmatch logs -l app.kubernetes.io/name=ollama --tail=50

kubectl -n trialmatch rollout status deploy/ollama
kubectl -n trialmatch rollout status deploy/trialmatch-api
```

Healthy API logs include:

```text
startup: live graph_runner ready
```

---

## 12. Part H — Configure Snowflake connection for the pods

Non-secret settings go in a ConfigMap. Apply with **your** account identifier (example values below — replace with yours):

```bash
kubectl -n trialmatch create configmap trialmatch-api-config \
  --from-literal=SNOWFLAKE_ACCOUNT='TRKSNJS-AL41445' \
  --from-literal=SNOWFLAKE_USER='JAYBFN' \
  --from-literal=SNOWFLAKE_WAREHOUSE='TRIALMATCH_WH' \
  --from-literal=SNOWFLAKE_DATABASE='TRIALMATCH_DEV' \
  --from-literal=SNOWFLAKE_SCHEMA='MARTS' \
  --from-literal=MATCHER_SNOWFLAKE_SCHEMA='MARTS' \
  --from-literal=AUDITOR_SNOWFLAKE_SCHEMA='AUDIT' \
  --from-literal=AGENT_READ_ROLE='AGENT_READ_ROLE' \
  --from-literal=AUDIT_WRITE_ROLE='AUDIT_WRITE_ROLE' \
  --from-literal=SNOWFLAKE_PRIVATE_KEY_SM_ID='trialmatch-snowflake-private-key' \
  --from-literal=SNOWFLAKE_PRIVATE_KEY_PASSPHRASE_SM_ID='' \
  --from-literal=SNOWFLAKE_PRIVATE_KEY_PATH='/tmp/trialmatch/snowflake-private-key.pem' \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n trialmatch rollout restart deploy/trialmatch-api
kubectl -n trialmatch rollout status deploy/trialmatch-api
kubectl -n trialmatch logs -l app.kubernetes.io/name=trialmatch-api --tail=40
```

---

## 13. Part I — Prove the live path with `/v1/match`

### I1. Port-forward (bastion)

```bash
pkill -f 'kubectl.*port-forward.*trialmatch-api' || true
kubectl -n trialmatch port-forward svc/trialmatch-api 18080:80
```

Leave that running. Open a **second** bastion SSH session for curls.

### I2. Health

```bash
curl -sS http://127.0.0.1:18080/healthz
curl -sS http://127.0.0.1:18080/readyz
```

### I3. Match (allow time for Ollama)

```bash
curl -sS -m 180 -X POST http://127.0.0.1:18080/v1/match \
  -H 'content-type: application/json' \
  -d '{"patient_id":"p-demo-001","note_text":"Adult with type 2 diabetes mellitus, HbA1c 8.1%."}'
```

Empty `matches` is OK before you seed trials/patients. The important part is `status: "ok"` and all agents listed (see below).

---

## 14. Troubleshooting diary (real errors we hit and fixes)

Use this as a search index when something breaks.

### 14.1 `make bastion` → `Permission denied` on `bastion-ssh.sh`

**Cause:** Windows/WSL `9p` mounts often ignore the Unix execute bit.
**Fix:** Makefile runs `bash scripts/bastion-ssh.sh` (no `+x` required).

### 14.2 `kubectl` from laptop → connection refused to `172.16.0.2`

**Cause:** Private control plane.
**Fix:** Use bastion + `--internal-ip` credentials.

### 14.3 `k8s/... does not exist` on bastion

**Cause:** You ran `kubectl apply` from `~` without the repo.
**Fix:** `cd` into the bastion git clone first.

### 14.4 Port-forward `address already in use` / `Empty reply from server`

**Cause:** Old `port-forward` still holding the port, or it died after a rollout.
**Fix:**

```bash
pkill -f 'kubectl.*port-forward.*trialmatch-api' || true
kubectl -n trialmatch port-forward svc/trialmatch-api 18080:80
```

### 14.5 Pods CrashLoop: `SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER are required`

**Cause:** Live app needs Snowflake env; ConfigMap empty / missing.
**Temporary workaround used during bring-up:** force health-only process:

```text
command: ["uvicorn", "trialmatch.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Proper fix:** set ConfigMap + Secret Manager key, then **remove** the override so image `CMD` uses `create_live_app`:

```bash
kubectl -n trialmatch get deploy trialmatch-api \
  -o jsonpath='{.spec.template.spec.containers[0].command}{"\n"}'

# if command is set to main:app, remove it:
kubectl -n trialmatch patch deploy trialmatch-api --type=json \
  -p='[{"op":"remove","path":"/spec/template/spec/containers/0/command"}]'
```

> Applying a YAML that *omits* `command` does **not** always clear a previous patch. Inspect and remove explicitly.

### 14.6 Snowflake `404 Not Found: post AL41445.snowflakecomputing.com`

**Cause:** Account identifier incomplete.
**Fix:** Use `TRKSNJS-AL41445` (org-account), not bare `AL41445`.

### 14.7 `ALTER USER ... Invalid Public key`

**Cause:** Headers/newlines/private key pasted into SQL.
**Fix:** One-line public key body only, run in Snowflake Worksheets.

### 14.8 `Role 'AUDIT_WRITE_ROLE' does not exist`

**Cause:** Ran `GRANT ROLE` before `01_roles.sql`.
**Fix:** Create roles first, then grant.

### 14.9 `syntax error ... unexpected 'START'` in `03_schemas_tables.sql`

**Cause:** `START` is a reserved SQL keyword.
**Fix:** Use quoted identifiers `"START"` / `"STOP"` (already fixed in repo).

### 14.10 `gcloud services enable` on bastion → `PERMISSION_DENIED`

**Cause:** Bastion uses `trialmatch-bastion@...` SA with limited roles.
**Fix:** Enable APIs / IAM bindings from your **laptop** as your user.

### 14.11 Parser failed: Vertex `SERVICE_DISABLED` or model 404

**Cause:** Deployment originally used `LLM_PROVIDER=vertex`; API/model not available.
**Fix used:** Switch to in-cluster Ollama (`LLM_PROVIDER=ollama`, model `llama3.2:1b`). Vertex is optional.

### 14.12 Matcher: `DIM_TRIAL_ELIGIBILITY_FEATURES` does not exist

**Cause:** dbt marts not built yet.
**Fix:** Create stub table (§D5) or run dbt after seeding.

### 14.13 Matcher: `'QdrantClient' object has no attribute 'search'`

**Cause:** `qdrant-client` 1.18 removed `.search()`; old adapter + server 1.13 mismatch.
**Fix:** Adapter uses `query_points`; Qdrant image `v1.18.0`; rebuild/push API image.

### 14.14 Pre-commit `detect-private-key` fails on tests

**Cause:** Test fixtures contained a contiguous PEM private-key marker string.
**Fix:** Split the marker in source (e.g. concatenate `"BEGIN "` with `"PRIVATE "` + `"KEY"`) so the hook does not false-positive.

### 14.15 `git push` succeeds but ends with `fatal: unknown error occurred while reading the configuration files`

**Cause:** Local git config quirk after a successful push (seen in Dev Container).
**Fix:** Ignore if `git ls-remote` shows your branch. Push already worked.

---

## 15. Success criteria and example response

### Minimum “live path works”

```bash
curl -sS -m 180 -X POST http://127.0.0.1:18080/v1/match \
  -H 'content-type: application/json' \
  -d '{"patient_id":"p-demo-001","note_text":"Adult with type 2 diabetes mellitus, HbA1c 8.1%."}'
```

Example of a **good** response (empty matches before seeding is fine):

```json
{
  "correlation_id": "5e21c060-d769-4d4f-b85d-991c1f4aca91",
  "patient_id": "p-demo-001",
  "status": "ok",
  "matches": [],
  "justification_summary": "No trials matched for this patient under current hybrid criteria.",
  "content_hash": "212ae0ac7bc6b46abb740a5cc2a54a7bb0390acf4428d1e36c8dbf4681b482b7",
  "written_match_ids": ["6f48eb4fec4a1a58def7a8dcbbd13455"],
  "agent_versions": {
    "compliance": "0.1.0",
    "parser": "0.1.0",
    "matcher": "0.1.0",
    "auditor": "0.1.0"
  },
  "error": null
}
```

Checklist:

| Signal | Meaning |
|--------|---------|
| `status: "ok"` | Pipeline finished without agent failure |
| `error: null` | No exception bubbled |
| All four `agent_versions` | Compliance → Parser → Matcher → Auditor ran |
| `written_match_ids` non-empty | Auditor inserted into Snowflake `AUDIT` |
| `matches: []` | No indexed trials / no patient features yet — expected pre-seed |

Pod log line you want at startup:

```text
startup: live graph_runner ready
```

---

## 16. What comes after this guide (seeding data)

To get **non-empty** `matches`:

1. Seed Synthea CSVs into Snowflake `RAW` — `scripts/seed_snowflake_from_synthea.py`
2. Run dbt models under `dbt/` to build `MARTS` (including `DIM_TRIAL_ELIGIBILITY_FEATURES`)
3. Index ClinicalTrials.gov criteria into Qdrant — trial indexer scripts/services
4. Call `/v1/match` with a `patient_id` that exists in the mart

Those steps are intentionally **out of scope** for this “live plumbing” guide.

---

## 17. Safety rules (do not skip)

1. **Never commit** `rsa_key.p8`, `.env` with secrets, or Snowflake passwords.
2. **Never** put PEM material into ConfigMaps or git.
3. Prefer **Workload Identity** / ADC — no service-account JSON keys in pods.
4. Do not attach a Snowflake network policy that only allows GKE NAT IPs to your interactive UI user until you also allowlist your home IP (or use a dedicated app user).
5. Run privileged `gcloud` IAM / API enables from your **user account**, not from the bastion SA.
6. Treat clinical note text as sensitive — do not paste real PHI into curl examples.

---

## Quick command cheat sheet

```bash
# Laptop
make bastion
make test
docker build -t "${IMAGE}" . && docker push "${IMAGE}"

# Bastion
kubectl -n trialmatch get pods
kubectl -n trialmatch logs -l app.kubernetes.io/name=trialmatch-api --tail=80
kubectl -n trialmatch port-forward svc/trialmatch-api 18080:80
curl -sS -m 180 -X POST http://127.0.0.1:18080/v1/match \
  -H 'content-type: application/json' \
  -d '{"patient_id":"p-demo-001","note_text":"Adult with type 2 diabetes mellitus, HbA1c 8.1%."}'
```

---

## Document history

This guide captures the bring-up path that reached a verified live `/v1/match` (`status: ok`, all agents, Snowflake audit write) using:

- Private GKE + IAP bastion
- Snowflake keypair + Secret Manager materialization
- In-cluster Qdrant `v1.18.0`
- In-cluster Ollama `llama3.2:1b` (instead of Vertex Gemini)

Update this file when the default LLM, image tag, or account identifier conventions change.
