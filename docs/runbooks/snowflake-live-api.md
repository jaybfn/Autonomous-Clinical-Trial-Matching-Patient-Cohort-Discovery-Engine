# Runbook: Enable live TrialMatch API (Snowflake + Secret Manager)

Use this after bastion access works and `/healthz` returns ok on the health-only image.

## Prerequisites

- Snowflake account with `TRIALMATCH_APP` (or your user) + keypair auth
- Roles/SQL from `snowflake/sql/` applied
- Network policy allowlisting Cloud NAT IPs: `136.112.132.174`, `34.61.252.214`
- Runtime GSA can access secrets (`roles/secretmanager.secretAccessor` via Terraform)

## 1) Upload key material to Secret Manager (laptop / Dev Container)

```bash
export PROJECT=autonomous-agent-503517

# Required — PEM private key (never commit this file)
gcloud secrets versions add trialmatch-snowflake-private-key \
  --project="${PROJECT}" \
  --data-file=/path/to/snowflake_key.pem

# Optional — only if the PEM is encrypted
printf '%s' 'your-passphrase' | gcloud secrets versions add trialmatch-snowflake-passphrase \
  --project="${PROJECT}" \
  --data-file=-

# Confirm a version exists
gcloud secrets versions list trialmatch-snowflake-private-key --project="${PROJECT}"
```

## 2) Set account + user in the ConfigMap

Edit `k8s/api/configmap.yaml` (or patch live):

```bash
# example values — use your Snowflake account locator / user
kubectl -n trialmatch create configmap trialmatch-api-config \
  --from-literal=SNOWFLAKE_ACCOUNT='xy12345.us-central1.gcp' \
  --from-literal=SNOWFLAKE_USER='TRIALMATCH_APP' \
  --from-literal=SNOWFLAKE_WAREHOUSE='TRIALMATCH_WH' \
  --from-literal=SNOWFLAKE_DATABASE='TRIALMATCH_DEV' \
  --from-literal=SNOWFLAKE_SCHEMA='MARTS' \
  --from-literal=MATCHER_SNOWFLAKE_SCHEMA='MARTS' \
  --from-literal=AUDITOR_SNOWFLAKE_SCHEMA='AUDIT' \
  --from-literal=AGENT_READ_ROLE='AGENT_READ_ROLE' \
  --from-literal=AUDIT_WRITE_ROLE='AUDIT_WRITE_ROLE' \
  --from-literal=SNOWFLAKE_PRIVATE_KEY_SM_ID='trialmatch-snowflake-private-key' \
  --from-literal=SNOWFLAKE_PRIVATE_KEY_PASSPHRASE_SM_ID='trialmatch-snowflake-passphrase' \
  --from-literal=SNOWFLAKE_PRIVATE_KEY_PATH='/tmp/trialmatch/snowflake-private-key.pem' \
  --dry-run=client -o yaml | kubectl apply -f -
```

## 3) Rebuild + push image (includes snowflake / secret-manager extras)

```bash
export IMAGE=us-central1-docker.pkg.dev/autonomous-agent-503517/trialmatch-docker/trialmatch-api:0.1.0
docker build -t "${IMAGE}" .
docker push "${IMAGE}"
```

## 4) Deploy Qdrant + API (from bastion)

```bash
make bastion
# on bastion, after kubeconfig:
kubectl apply -f k8s/qdrant/deployment.yaml
kubectl apply -f k8s/qdrant/service.yaml
kubectl apply -f k8s/api/configmap.yaml   # if you edited the file instead of step 2
kubectl apply -f k8s/api/deployment.yaml
kubectl apply -f k8s/api/service.yaml

# Clear any prior health-only command override by re-applying deployment.yaml
kubectl -n trialmatch rollout status deploy/trialmatch-api
kubectl -n trialmatch get pods
kubectl -n trialmatch logs -l app.kubernetes.io/name=trialmatch-api --tail=80
```

Pods must use the image `CMD` (`create_live_app`), not a patched `uvicorn …:app`.

## 5) Verify

```bash
kubectl -n trialmatch port-forward svc/trialmatch-api 8080:80
curl -sS http://127.0.0.1:8080/healthz
curl -sS http://127.0.0.1:8080/readyz

curl -sS -X POST http://127.0.0.1:8080/v1/match \
  -H 'content-type: application/json' \
  -d '{"patient_id":"p-demo-001","note_text":"Adult with type 2 diabetes mellitus, HbA1c 8.1%."}'
```

## Failure checklist

| Symptom | Likely cause |
|---------|----------------|
| `SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER are required` | ConfigMap account/user empty |
| Secret Manager 404 / permission denied | No secret version, or WI/GSA missing `secretAccessor` |
| Snowflake auth failed | Wrong PEM, user, or network policy (NAT IPs) |
| Qdrant connection errors | Qdrant not deployed in `trialmatch` ns |
| Vertex / LLM errors | Runtime GSA missing Vertex AI User, or API not enabled |
