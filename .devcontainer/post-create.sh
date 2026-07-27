#!/usr/bin/env bash
# Dev Container post-create: editable install + local gcloud config (never write to host mount).
set -euo pipefail

pip install -r requirements-dev.txt

# Bind-mounted workspace is often owned by a different UID than vscode (Docker/Windows).
git config --global --add safe.directory /workspace || true

# Git hooks: Ruff/terraform on commit; pytest on push.
python -m pre_commit install --hook-type pre-commit --hook-type pre-push || true

mkdir -p "${CLOUDSDK_CONFIG:-/home/vscode/.config/gcloud}"

# Project via env is enough for most SDKs; also set active gcloud config in the
# *container-local* CLOUDSDK_CONFIG (writable). Host ADC stays on /mnt/host-gcloud.
if [[ -n "${GCP_PROJECT_ID:-}" ]]; then
  gcloud config set project "${GCP_PROJECT_ID}" --quiet
fi

if [[ -f /mnt/host-gcloud/application_default_credentials.json ]]; then
  echo "Host ADC available at /mnt/host-gcloud/application_default_credentials.json"
else
  echo "WARNING: Host ADC not found. On the host run: gcloud auth application-default login" >&2
fi
