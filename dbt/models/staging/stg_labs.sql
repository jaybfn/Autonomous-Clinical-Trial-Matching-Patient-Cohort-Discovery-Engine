{{ config(alias='stg_labs') }}

select
  patient as patient_id,
  date as observed_at,
  code as lab_code,
  description as lab_description,
  value as lab_value,
  units as lab_units,
  loaded_at
from {{ source('raw', 'raw_synthea_labs') }}
where patient is not null
  and code is not null
