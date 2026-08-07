{% macro generate_schema_name(custom_schema_name, node) -%}
  {#- Use custom schema as-is so models land in STAGING / MARTS / AUDIT,
      not target_schema_custom (e.g. STAGING_marts). -#}
  {%- if custom_schema_name is none -%}
    {{ target.schema }}
  {%- else -%}
    {{ custom_schema_name | trim | upper }}
  {%- endif -%}
{%- endmacro %}
