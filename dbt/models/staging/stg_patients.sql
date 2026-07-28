{{ config(alias='stg_patients') }}

select
  id as patient_id,
  birthdate,
  gender,
  race,
  ethnicity,
  city,
  state,
  loaded_at
from {{ source('raw', 'raw_synthea_patients') }}
where id is not null
