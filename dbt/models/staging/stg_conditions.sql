{{ config(alias='stg_conditions') }}

select
  patient as patient_id,
  start as condition_start,
  stop as condition_stop,
  code as condition_code,
  description as condition_description,
  loaded_at
from {{ source('raw', 'raw_synthea_conditions') }}
where patient is not null
  and code is not null
