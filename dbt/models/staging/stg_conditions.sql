{{ config(alias='stg_conditions') }}

select
  patient as patient_id,
  "START" as condition_start,
  "STOP" as condition_stop,
  code as condition_code,
  description as condition_description,
  loaded_at
from {{ source('raw', 'raw_synthea_conditions') }}
where patient is not null
  and code is not null
