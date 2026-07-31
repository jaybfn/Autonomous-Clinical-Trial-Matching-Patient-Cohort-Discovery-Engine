#!/usr/bin/env bash
# Shorthand: SSH to the private TrialMatch bastion via IAP.
# Usage: ./scripts/bastion-ssh.sh
#        make bastion-ssh

set -euo pipefail

PROJECT="${GCP_PROJECT_ID:-autonomous-agent-503517}"
ZONE="${BASTION_ZONE:-us-central1-a}"
INSTANCE="${BASTION_NAME:-trialmatch-bastion}"

exec gcloud compute ssh "${INSTANCE}" \
  --project="${PROJECT}" \
  --zone="${ZONE}" \
  --tunnel-through-iap \
  "$@"
