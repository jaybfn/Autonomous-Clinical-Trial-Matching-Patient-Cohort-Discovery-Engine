# Tracked operator documentation

These files are **committed** for ops, security, and onboarding.

| Doc | Audience |
|-----|----------|
| [guides/DEPLOY-FROM-SCRATCH.md](guides/DEPLOY-FROM-SCRATCH.md) | **New GCP account / full rebuild** — one step-by-step checklist (Terraform → data → Ingress → Streamlit) |
| [architecture.md](architecture.md) | Engineers / auditors |
| [guides/getting-started-live-path.md](guides/getting-started-live-path.md) | New joiners — clone → live `/v1/match` (detailed, beginner-friendly plumbing) |
| [guides/migrate-dev-machine-to-ubuntu.md](guides/migrate-dev-machine-to-ubuntu.md) | Moving the dev workstation from Windows/WSL to Ubuntu |
| [runbooks/incident-matching.md](runbooks/incident-matching.md) | On-call |
| [runbooks/bastion-access.md](runbooks/bastion-access.md) | Private GKE via IAP bastion |
| [runbooks/snowflake-live-api.md](runbooks/snowflake-live-api.md) | Enable live API (SM key + ConfigMap) |
| [runbooks/public-api-streamlit-cloud.md](runbooks/public-api-streamlit-cloud.md) | Public Ingress + API key + Streamlit Cloud |
| [security/workload-identity.md](security/workload-identity.md) | Platform / security |

> Local learning guides live in gitignored `doc/` and per-file `*.README.md` — do not confuse with this folder.
