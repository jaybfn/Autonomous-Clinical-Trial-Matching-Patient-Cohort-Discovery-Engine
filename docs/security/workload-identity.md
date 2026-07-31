# Workload Identity

## Policy

- **No service-account JSON keys** in git, images, or Secret Manager for runtime GCP auth.
- GKE workloads authenticate with **Workload Identity** → runtime GSA.
- Local/dev uses **Application Default Credentials** (`gcloud auth application-default login`).

## Binding (dev)

| Side | Identity |
|------|----------|
| Kubernetes | Namespace `trialmatch`, KSA `trialmatch-ksa` |
| Google | `trialmatch-runtime@autonomous-agent-503517.iam.gserviceaccount.com` |

KSA annotation (must match Terraform output `ksa_annotation`):

```yaml
iam.gke.io/gcp-service-account: trialmatch-runtime@autonomous-agent-503517.iam.gserviceaccount.com
```

Principal on the GSA IAM binding:

```text
serviceAccount:autonomous-agent-503517.svc.id.goog[trialmatch/trialmatch-ksa]
```

Manifest: `k8s/serviceaccounts/trialmatch-ksa.yaml`
IaC: `infra/terraform/modules/workload_identity`

## kubectl access (private control plane)

The GKE API (`172.16.0.2`) is not reachable from laptops. Use the **IAP bastion**:

See [Bastion access runbook](../runbooks/bastion-access.md).

## Verification

```bash
kubectl -n trialmatch get sa trialmatch-ksa -o yaml
# Confirm annotation matches terraform output

kubectl -n trialmatch get deploy trialmatch-api -o jsonpath='{.spec.template.spec.serviceAccountName}'
# Expect: trialmatch-ksa
```

From a debug pod using the same KSA, ADC should mint tokens for the runtime GSA (no key file).

## Snowflake network path

Private GKE egress uses Cloud NAT. Allowlist these IPs on the Snowflake network policy:

- `136.112.132.174`
- `34.61.252.214`

## Role separation (application)

| Role | Used by | Allowed |
|------|---------|---------|
| `AGENT_READ_ROLE` | Matcher | SELECT on RAW/STAGING/MARTS |
| `AUDIT_WRITE_ROLE` | Auditor sink | INSERT (+ SELECT) on `AUDIT` only |

Matcher must never INSERT audit/clinical tables. Auditor must never SELECT clinical marts for matching. Enforced in SQL grants + application tests (`tests/integration/test_rbac_boundaries.py`).

## Span / log hygiene

Never put note text, SSN, MRN, email, phone, or addresses on OpenTelemetry spans or structured log extras. See `trialmatch.observability.tracing.ALLOWED_SPAN_ATTRIBUTES`.
