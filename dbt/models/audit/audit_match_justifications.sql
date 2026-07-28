{{ config(alias='audit_match_justifications') }}

-- Read model over the physical AUDIT table (writes go through SnowflakeClient + AUDIT_WRITE_ROLE).
select
  match_id,
  patient_id,
  nct_id,
  justification,
  agent_name,
  correlation_id,
  created_at
from {{ source('audit', 'audit_match_justifications') }}
