{{ config(alias='fct_patient_history') }}

-- Matcher-facing patient history: demographics + active conditions + recent labs.
with patients as (
  select * from {{ ref('stg_patients') }}
),
conditions as (
  select * from {{ ref('stg_conditions') }}
),
labs as (
  select * from {{ ref('stg_labs') }}
)

select
  p.patient_id,
  p.birthdate,
  p.gender,
  c.condition_code,
  c.condition_description,
  c.condition_start,
  c.condition_stop,
  l.lab_code,
  l.lab_description,
  l.lab_value,
  l.lab_units,
  l.observed_at
from patients p
left join conditions c on p.patient_id = c.patient_id
left join labs l on p.patient_id = l.patient_id
