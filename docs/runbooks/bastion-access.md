# Runbook: Private GKE access via IAP bastion

Use this when `kubectl` from your laptop/Dev Container fails with:

`dial tcp 172.16.0.2:443: connect: connection refused`

That is expected: the control plane is **private**. Access it through the bastion.

## Prerequisites

- Terraform applied with `module.bastion`
- Your Google account listed in `bastion_iap_members` (e.g. `user:you@gmail.com`)
- Local tools: `gcloud` CLI authenticated

## 1) SSH through IAP

From the repo root (simplest):

```bash
make bastion-ssh
# aliases: make bastion
# or:      bash scripts/bastion-ssh.sh
```

Equivalents:

```bash
cd infra/terraform/envs/dev
terraform output -raw bastion_iap_ssh_command
# or full gcloud:
gcloud compute ssh trialmatch-bastion \
  --project=autonomous-agent-503517 \
  --zone=us-central1-a \
  --tunnel-through-iap
```

First boot may take a few minutes while the startup script installs `gcloud` / `kubectl` / `gke-gcloud-auth-plugin`.

## 2) On the bastion — kubeconfig

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

## 3) Deploy TrialMatch API (from bastion)

For **live** Snowflake wiring (Secret Manager + ConfigMap), see
[snowflake-live-api.md](./snowflake-live-api.md).

```bash
# Optional: clone repo or copy manifests
kubectl apply -f k8s/serviceaccounts/trialmatch-ksa.yaml
kubectl apply -f k8s/qdrant/deployment.yaml
kubectl apply -f k8s/qdrant/service.yaml
kubectl apply -f k8s/ollama/deployment.yaml
kubectl apply -f k8s/ollama/service.yaml
kubectl apply -f k8s/api/configmap.yaml
kubectl apply -f k8s/api/deployment.yaml
kubectl apply -f k8s/api/service.yaml
# Ollama may take several minutes on first boot while pulling llama3.2:1b

kubectl -n trialmatch get pods
kubectl -n trialmatch port-forward svc/trialmatch-api 8080:80
# then curl localhost:8080/healthz from the bastion session
```

Image push still happens from your laptop (Artifact Registry is public to authorized gcloud users):

```bash
# on laptop / Dev Container
docker push us-central1-docker.pkg.dev/autonomous-agent-503517/trialmatch-docker/trialmatch-api:0.1.0
```

## Security notes

- Bastion has **no public IP**; SSH only from IAP ranges `35.235.240.0/20`
- OS Login is enabled; no static SSH keys in metadata
- Bastion GSA has `roles/container.developer` (not owner)
- GKE master authorizes the private subnet CIDR so the bastion can reach `172.16.0.2`

## Grant access to another engineer

Add their principal to `bastion_iap_members` in `terraform.tfvars` and re-apply:

```hcl
bastion_iap_members = [
  "user:you@gmail.com",
  "user:teammate@gmail.com",
]
```
