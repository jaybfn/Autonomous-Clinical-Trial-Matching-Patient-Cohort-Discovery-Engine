# Moving the dev machine to Ubuntu Linux: what changes (and what doesn't)

This guide explains what happens if you stop developing this project on **Windows + WSL2 + Docker Desktop** and switch to a machine running **Ubuntu Linux** natively.

Short version: **the deployed app does not change at all.** Everything that runs in GCP (GKE pods, Snowflake, Qdrant, Ollama, Secret Manager, Terraform-managed infra) is completely independent of your laptop's operating system. The only things that change are on your **development workstation** — and several Windows-specific annoyances actually go away.

---

## 1. What does NOT change (the important part)

| Component | Why it is unaffected |
|-----------|----------------------|
| GKE cluster, pods, manifests | They run in Google's cloud. `kubectl apply` output is identical from any OS. |
| Docker image `trialmatch-api` | Built `FROM python:3.11-slim` — it is already a **Linux** image. You were always building Linux containers, even on Windows. |
| Snowflake (roles, keys, data) | Cloud service; only reachable over HTTPS. Nothing local. |
| Secret Manager secrets | Stored in GCP. The PEM you uploaded stays valid. |
| Terraform state & infra | State lives in the GCS backend. Any machine with `terraform` + your credentials can plan/apply. |
| Bastion + IAP SSH | `gcloud compute ssh --tunnel-through-iap` works the same on Linux. |
| Git repo / CI | GitHub Actions already runs on Ubuntu runners — CI has been "on Linux" the whole time. |
| Python code and tests | Pure Python; `make test` behaves identically. |

**Conclusion:** this is a *workstation* migration, not an *application* migration. No redeploys required.

---

## 2. What DOES change on the workstation

### 2.1 Docker Desktop → native Docker Engine

On Windows you needed Docker Desktop (a licensed product with a WSL2 VM underneath). On Ubuntu, Docker runs natively:

```bash
# Install Docker Engine (official repo)
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Let your user run docker without sudo (log out/in afterwards)
sudo usermod -aG docker "$USER"
```

Everything else is identical:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
docker build -t "${IMAGE}" . && docker push "${IMAGE}"
```

> **CPU architecture note:** if the Ubuntu machine is standard x86_64, nothing changes. Only if you ever use an ARM machine (rare for Ubuntu laptops) would you need `docker build --platform linux/amd64` so GKE's amd64 nodes can run the image.

### 2.2 gcloud ADC location: `%APPDATA%\gcloud` → `~/.config/gcloud`

This is the **one real config change in the repo**.

On Windows, gcloud stores Application Default Credentials under `%APPDATA%\gcloud`, and our Dev Container bind-mounts that path:

```50:51:.devcontainer/devcontainer.json
  "mounts": [
    "source=${localEnv:APPDATA}/gcloud,target=/mnt/host-gcloud,type=bind,readonly,consistency=cached"
  ]
```

On Linux, `APPDATA` is not set, so that mount source resolves to `/gcloud` and the container fails to start (or starts without ADC).

**Fix — make the mount cross-platform.** In devcontainer variable substitution, unset variables become empty strings, so concatenating both works on either OS (exactly one side is non-empty):

```json
"mounts": [
  "source=${localEnv:APPDATA}${localEnv:HOME}/.config/gcloud,target=/mnt/host-gcloud,type=bind,readonly,consistency=cached"
]
```

- Windows: `APPDATA=C:\Users\you\AppData\Roaming`, `HOME` unset → resolves near `.../AppData/Roaming/.config/gcloud` (adjust if you keep the old pure-Windows path; simplest is to keep two mount lines or just edit once when you switch).
- Ubuntu: `APPDATA` unset, `HOME=/home/you` → `/home/you/.config/gcloud`. Correct.

If you are switching to Ubuntu permanently (not dual-OS), the cleaner edit is simply:

```json
"mounts": [
  "source=${localEnv:HOME}/.config/gcloud,target=/mnt/host-gcloud,type=bind,readonly,consistency=cached"
]
```

**Heads-up on tests:** `tests/test_project_skeleton.py` asserts the string `APPDATA` exists in `devcontainer.json` (a Phase 0 contract). If you remove `APPDATA`, update that test in the same commit — otherwise `make test` and the pre-push hook fail:

```63:64:tests/test_project_skeleton.py
    assert "APPDATA" in cfg
    assert "/mnt/host-gcloud" in cfg
```

Then on the Ubuntu host, authenticate once:

```bash
gcloud auth login
gcloud auth application-default login   # writes ~/.config/gcloud/application_default_credentials.json
gcloud config set project autonomous-agent-503517
```

`post-create.sh` already checks `/mnt/host-gcloud/application_default_credentials.json` and warns if missing — that logic works unchanged once the mount points at the Linux path.

### 2.3 WSL2 / 9p filesystem quirks disappear

Several problems we worked around on Windows simply stop existing:

| Windows/WSL problem we hit | On Ubuntu |
|-----------------------------|-----------|
| `chmod +x scripts/bastion-ssh.sh` didn't stick (9p mount ignores the execute bit), so `make bastion` failed with `Permission denied` | Execute bits work normally. The `bash scripts/bastion-ssh.sh` workaround in the Makefile still works and can stay. |
| Workspace mounted via `D:\ → 9p`, causing odd ownership (`root:root` files) and `safe.directory` git warnings | Native ext4 filesystem; files owned by your user. The `safe.directory` setting in `devcontainer.json` is harmless to keep. |
| Slow file I/O across the Windows/WSL boundary | Native disk speed; `docker build`, `pytest`, and git get noticeably faster. |
| `fatal: unknown error occurred while reading the configuration files` after successful `git push` | This Dev Container/Windows credential-helper quirk typically goes away. |
| Possible CRLF line-ending surprises | Pure LF world. If you cloned on Windows with `core.autocrlf=true`, re-clone fresh on Ubuntu; pre-commit's `mixed line ending` hook keeps things clean either way. |

### 2.4 Dev Container vs native — you now have a real choice

**Option A — keep the Dev Container (recommended, least change).**
Install Docker Engine + VS Code/Cursor with Dev Containers, apply the mount fix from §2.2, and everything else works as before. The container itself is Debian-based (`python:3.11-bookworm`) and doesn't care what the host is.

**Option B — run natively on Ubuntu (no container).**
Now viable, since Ubuntu gives you the same Linux toolchain the container provided:

```bash
sudo apt-get install -y python3.11 python3.11-venv make git

# gcloud CLI
curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install -y google-cloud-cli

# Terraform (HashiCorp apt repo) — only needed for infra work
# https://developer.hashicorp.com/terraform/install

# Project setup
python3.11 -m venv .venv && source .venv/bin/activate
make bootstrap        # install deps + pre-commit hooks
make test
cp .env.example .env  # set GCP_PROJECT_ID
```

Trade-off: native is faster and simpler day-to-day, but you own the tool-version drift that the container pinned for you.

### 2.5 Snowflake keys and other local secrets

Anything that lived only on the Windows machine must be moved or regenerated:

- `~/snowflake-keys/rsa_key.p8` — the private key is **also** in Secret Manager (`trialmatch-snowflake-private-key`), which is what the pods use, so the app keeps working even if you lose the local copy. For local dbt runs you need the PEM on the new machine: either copy it over a secure channel, fetch it back from Secret Manager (`gcloud secrets versions access latest --secret=trialmatch-snowflake-private-key > rsa_key.p8 && chmod 600 rsa_key.p8`), or generate a fresh keypair and re-run `ALTER USER ... SET RSA_PUBLIC_KEY` + upload the new PEM.
- `.env` (gitignored) — recreate from `.env.example`.
- `~/.dbt/profiles.yml` — recreate from `dbt/profiles.yml.example`; note Linux home paths (`/home/you/...`).

### 2.6 Small path/name differences to expect

| Item | Windows habit | Ubuntu |
|------|----------------|--------|
| gcloud config dir | `%APPDATA%\gcloud` | `~/.config/gcloud` |
| Python launcher | `py -3.10 ...` (as in README's Windows example) | `python3.11 ...` |
| Paths in docs/scripts | `C:\Users\...` examples | `/home/you/...` |
| Docker socket | Docker Desktop magic | `/var/run/docker.sock` (needs `docker` group, §2.1) |

---

## 3. Migration checklist (do these in order)

1. [ ] Ubuntu: install Docker Engine, add yourself to the `docker` group (§2.1)
2. [ ] Ubuntu: install `gcloud`, run `gcloud auth login` + `gcloud auth application-default login`, set the project
3. [ ] Clone the repo fresh (avoids any CRLF/ownership baggage from the old checkout)
4. [ ] Edit `.devcontainer/devcontainer.json` mount: `APPDATA` → `HOME/.config` (§2.2) **and** update the `APPDATA` assertion in `tests/test_project_skeleton.py`
5. [ ] Open in Dev Container (or set up natively, §2.4) and run `make test` — should be green
6. [ ] Copy/refetch the Snowflake PEM if you need local dbt (§2.5); recreate `.env`
7. [ ] Smoke-test the full loop:
   - `make bastion` → `kubectl get nodes`
   - `docker build -t "${IMAGE}" . && docker push "${IMAGE}"` (optional — only if you have changes)
   - port-forward + `curl /healthz` from the bastion
8. [ ] Commit the devcontainer + test change as its own PR (e.g. `chore: cross-platform ADC mount for Linux hosts`)

---

## 4. FAQ

**Do I need to redeploy anything in GCP?**
No. Pods, images, secrets, and Terraform state are untouched by a workstation change.

**Will `make bastion` work?**
Yes — better than before. The IAP tunnel is pure `gcloud`; and the execute-bit workaround we added for WSL is no longer even needed (but harmless).

**Does the Docker image need rebuilding for Ubuntu?**
No. It was always a Linux (amd64) image. Rebuild only when code changes.

**Can I dual-develop from both Windows and Ubuntu?**
Yes. Use the concatenation trick in §2.2 so the same `devcontainer.json` resolves the ADC path on both hosts, and keep secrets (`.env`, PEM, `~/.dbt`) machine-local on each.

**Anything that gets *harder* on Ubuntu?**
Practically nothing for this project. The only cost is one-time setup (Docker group, gcloud install) and the small `devcontainer.json`/test edit.
