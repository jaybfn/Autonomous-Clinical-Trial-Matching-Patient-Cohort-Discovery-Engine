{{ config(alias='dim_trial_eligibility_features') }}

-- Compact eligibility feature rows for hybrid matching (one row per patient×feature).
with condition_features as (
  select
    patient_id,
    'condition' as feature_type,
    condition_code as feature_code,
    condition_description as feature_label,
    condition_start as feature_start,
    condition_stop as feature_end,
    null::float as feature_value,
    null::varchar as feature_units
  from {{ ref('stg_conditions') }}
),
lab_features as (
  select
    patient_id,
    'lab' as feature_type,
    lab_code as feature_code,
    lab_description as feature_label,
    observed_at as feature_start,
    null::date as feature_end,
    lab_value as feature_value,
    lab_units as feature_units
  from {{ ref('stg_labs') }}
)

select * from condition_features
union all
select * from lab_features
