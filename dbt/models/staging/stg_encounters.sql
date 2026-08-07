{{ config(alias='stg_encounters') }}

-- Prefer dedicated encounters landing; if empty, no rows (matcher still uses conditions/labs).
select
  id as encounter_id,
  patient as patient_id,
  "START" as encounter_start,
  "STOP" as encounter_stop,
  encounterclass as encounter_class,
  code as encounter_code,
  description as encounter_description,
  loaded_at
from {{ source('raw', 'raw_synthea_encounters') }}
where id is not null
