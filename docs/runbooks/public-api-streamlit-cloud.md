# Public Ingress + API key + Streamlit Cloud

Expose `trialmatch-api` via the existing GCE Ingress static IP, protect
`POST /v1/match` with a shared API key, and point Streamlit Cloud at that URL so
colleagues only need the Streamlit link and guest login (no bastion tunnels).

```text
Colleague browser → Streamlit Cloud → POST /v1/match + X-API-Key → GCE Ingress → API → Snowflake / Qdrant
```

## Security model

| Layer | Role |
|-------|------|
| Guest login (Streamlit) | UI gate only — **not** API security |
| `TRIALMATCH_API_KEY` / `X-API-Key` | Shared secret on the API |
| Ingress IP | Public; assume scanners will hit it |
| TLS | Optional for a short HTTP demo; add domain + managed cert soon after |

Never put the API key in git, ConfigMaps, or client-side JavaScript. Rotate if leaked.
Synthetic / demo data only — do not paste real PHI into a public UI.

## Part A — Create and wire the API key (GKE)

### 1. Secret Manager shell (Terraform)

Ensure `trialmatch-api-key` is listed in `secret_ids` (see
`infra/terraform/envs/dev/terraform.tfvars.example`), then apply:

```bash
cd infra/terraform/envs/dev
terraform plan
terraform apply
```

Add a version (never via Terraform):

```bash
KEY="$(openssl rand -hex 32)"
echo -n "$KEY" | gcloud secrets versions add trialmatch-api-key --data-file=-
# Keep $KEY for the Kubernetes Secret and Streamlit Cloud secrets.
```

### 2. Kubernetes Secret → Deployment env

The Deployment reads `TRIALMATCH_API_KEY` from Secret `trialmatch-api-key` key
`api-key` (`optional: true` so local/internal demos without the Secret still start).

Fast path from bastion (same value as SM):

```bash
kubectl -n trialmatch create secret generic trialmatch-api-key \
  --from-literal=api-key="$KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Or copy `k8s/api/secret-api-key.yaml.example`, replace the placeholder, and apply
(do not commit the filled file).

Confirm ConfigMap does **not** contain the key:

```bash
kubectl -n trialmatch get configmap trialmatch-api-config -o yaml | grep -i api.key || true
```

### 3. Rebuild / rollout API (auth code must be in the image)

From a machine with Docker + Artifact Registry access:

```bash
export PROJECT_ID=autonomous-agent-503517
export IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/trialmatch-docker/trialmatch-api:0.1.0"
docker build -t "${IMAGE}" .
docker push "${IMAGE}"

# on bastion
kubectl apply -f k8s/api/deployment.yaml
kubectl -n trialmatch rollout restart deploy/trialmatch-api
kubectl -n trialmatch rollout status deploy/trialmatch-api
```

Empty `TRIALMATCH_API_KEY` disables auth (port-forward / unit tests). Non-empty
enforces `X-API-Key` on `POST /v1/match` only. `GET /healthz` and `GET /readyz`
stay open for probes.

## Part B — Public Ingress

```bash
# on bastion
kubectl apply -f k8s/api/service.yaml
kubectl apply -f k8s/api/ingress.yaml
kubectl -n trialmatch get ingress trialmatch-api
```

Resolve the static IP:

```bash
terraform -chdir=infra/terraform/envs/dev output -raw ingress_static_ip_address
# or
gcloud compute addresses describe trialmatch-ingress-ip --global --format='value(address)'
```

### Demo default (no custom domain)

Streamlit Cloud / curl use plaintext HTTP to the IP (server-side from Streamlit is fine):

```text
TRIALMATCH_API_BASE_URL = "http://<STATIC_IP>"
```

Traffic is **not** TLS until you add a domain and managed certificate
(`ingress_domain` in Terraform / Ingress annotations — already modeled under
`infra/terraform/modules/ingress`).

### Hardening (recommended soon)

1. Set `ingress_domain` (e.g. `api.example.com`) and apply Terraform.
2. Point DNS A record at the static IP.
3. Update Ingress for HTTPS / managed cert.
4. Switch Streamlit secrets to `https://api.example.com`.

### Smoke (any laptop — no bastion)

```bash
curl -sS "http://<STATIC_IP>/healthz"
curl -sS -X POST "http://<STATIC_IP>/v1/match" \
  -H "content-type: application/json" \
  -H "X-API-Key: $TRIALMATCH_API_KEY" \
  -d '{"patient_id":"...","note_text":"..."}'
```

Missing/wrong key → **401**. Correct key → match pipeline response.

## Part C — Streamlit Cloud

1. Deploy this repo on [Streamlit Community Cloud](https://streamlit.io/cloud).
   Main file path: `streamlit_app/app.py`.
2. App secrets (Cloud UI → Settings → Secrets):

```toml
DEMO_GUEST_USERNAME = "guest"
DEMO_GUEST_PASSWORD = "<share-out-of-band>"
TRIALMATCH_API_BASE_URL = "http://<STATIC_IP>"
TRIALMATCH_API_KEY = "<same-as-GKE-secret>"
```

3. Colleagues open the Streamlit URL → guest login → presets → match.
   They never see the API key (server-side `requests` only).

### Local tunnel path (unchanged)

Bastion `kubectl port-forward` + optional SSH `-L 18080` remains valid for
developers. Use `TRIALMATCH_API_BASE_URL = "http://127.0.0.1:18080"` and leave
`TRIALMATCH_API_KEY` empty **unless** the cluster Deployment has the key set
(then local Streamlit must send the same key).

See [streamlit_app/README.md](../../streamlit_app/README.md).
