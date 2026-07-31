# Runbook: Matching failures

What to do when trial matching fails or stalls in production.

## Symptoms

- FastAPI `POST /v1/match` returns `status=failed`
- Ingestion logs `ingestion.retry` / `ingestion.poison`
- Growing Pub/Sub backlog or DLQ depth (`clinical-records-dlq`)
- Empty `matches` for notes that should hit indexed trials
- Auditor / Snowflake insert errors

## Triage (PHI-safe)

1. Capture **`correlation_id`** (message id or API field). Prefer logs/spans over raw notes.
2. Check graph stage from logs:
   - `compliance.*` — scrub failure
   - `parser.*` / `LLM` — model unavailable
   - `matcher.*` / `Qdrant` / `Snowflake` — retrieval/warehouse
   - `auditor.*` / `Audit sink` — audit write / role
3. Confirm pods use Workload Identity (`trialmatch-ksa`) — see [workload-identity.md](../security/workload-identity.md).
4. Confirm Snowflake network policy still allows NAT IPs:
   - `136.112.132.174`
   - `34.61.252.214`
5. Confirm Qdrant Service DNS: `http://qdrant.trialmatch.svc.cluster.local:6333`
6. Inspect DLQ envelopes (reason + payload_keys only — **no note body** by design).

## Common remediations

| Cause | Action |
|-------|--------|
| Transient LLM / Snowflake / Qdrant | Let Pub/Sub retry; scale or fix dependency |
| Poison / invalid schema | Fix producer; drain DLQ after fix |
| Empty Qdrant index | Re-run trial indexer (`scripts/index_trials_to_qdrant.py`) |
| Role / grant drift | Re-apply `snowflake/sql/*` grants; verify `AGENT_READ_ROLE` vs `AUDIT_WRITE_ROLE` |
| Bad image | Roll Deployment to last good tag in Artifact Registry |

## Safe replay

- Ingestion is **at-least-once**. Auditor `MATCH_ID` is deterministic from `correlation_id` + NCT + `content_hash` — retries may collide if the table lacks a uniqueness constraint; prefer fixing forward and monitoring duplicates.
- Do **not** paste clinical notes into tickets; use `correlation_id` + `content_hash`.

## Escalation

1. Platform / GKE (WI, networking, Pub/Sub)
2. Data (Snowflake grants, dbt marts)
3. ML / Parser (Ollama or Vertex availability)
