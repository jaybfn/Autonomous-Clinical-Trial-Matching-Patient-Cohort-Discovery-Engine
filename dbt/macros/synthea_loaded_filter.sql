{% macro synthea_loaded_filter(column_name='loaded_at') %}
  {{ column_name }} is not null
{% endmacro %}
