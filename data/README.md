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
| `scripts/prepare_synthea_for_snowflake.py` | Slim CSVs under `data/raw/synthea-hf/for_snowflake/` |
| `scripts/put_copy_synthea_to_snowflake.py` | Snowflake `RAW.RAW_SYNTHEA_*` (PUT + COPY) |
| `scripts/fetch_clinicaltrials_eligibility.py` | `data/raw/clinicaltrials/eligibility.jsonl` (CT.gov API v2) |
| `scripts/index_trials_to_qdrant.py` | Qdrant `trial_criteria` |
| `scripts/seed_snowflake_from_synthea.py` | Legacy/dry-run sample seeder |
| `scripts/publish_synthea_events.py` | Pub/Sub topics |
| `streamlit_app/` | Clinician demo UI (guest login → `/v1/match`) |

**Current Qdrant demo default:** ~2k studies (`diabetes` + `RECRUITING`). How to load Snowflake bulk data or expand the trial index is documented in the root [README.md](../README.md#data-loading-snowflake--qdrant). Streamlit demo: [streamlit_app/README.md](../streamlit_app/README.md).

All cloud calls use ADC / Workload Identity — no hardcoded secrets.
