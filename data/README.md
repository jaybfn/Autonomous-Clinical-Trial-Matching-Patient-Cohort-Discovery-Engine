# Data sources

Primary prototype datasets for this project:

| Source | Purpose | Location |
|--------|---------|----------|
| **Synthea** | Synthetic patient EPR (CSV + clinical notes) | `data/synthea/samples/` |
| **ClinicalTrials.gov** | Open trial eligibility criteria | `data/clinicaltrials/samples/` |

## Samples vs raw downloads

- **`data/*/samples/`** — small, committed subsets used by unit tests, local demos, and CI. Safe to commit.
- **`data/raw/`** — optional bulk downloads (gitignored). Use `scripts/download_*.py` to populate.

Never commit real patient / EHR extracts. Prototype with synthetic/open data only.

## Licenses / attribution

- **Synthea** — synthetic data generator; sample rows here are hand-authored Synthea-shaped fixtures for demos (not a full Synthea dump). See [Synthea](https://github.com/synthetichealth/synthea).
- **ClinicalTrials.gov** — public trial registry data; sample eligibility text is illustrative/open-style criteria for indexing demos. See [ClinicalTrials.gov](https://clinicaltrials.gov/).

## Feed scripts

| Script | Destination |
|--------|-------------|
| `scripts/seed_snowflake_from_synthea.py` | Snowflake landing tables |
| `scripts/publish_synthea_events.py` | Pub/Sub topics |
| `scripts/index_trials_to_qdrant.py` | Qdrant collection |

All cloud calls use ADC / Workload Identity — no hardcoded secrets.
