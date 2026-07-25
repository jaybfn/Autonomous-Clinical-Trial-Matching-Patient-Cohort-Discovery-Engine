"""Env-only application settings — no hardcoded secrets."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded exclusively from environment variables."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    gcp_project_id: str = Field(..., alias="GCP_PROJECT_ID")
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="trial_criteria", alias="QDRANT_COLLECTION")

    snowflake_account: str = Field(default="", alias="SNOWFLAKE_ACCOUNT")
    snowflake_user: str = Field(default="", alias="SNOWFLAKE_USER")
    snowflake_warehouse: str = Field(default="", alias="SNOWFLAKE_WAREHOUSE")
    snowflake_database: str = Field(default="", alias="SNOWFLAKE_DATABASE")
    snowflake_schema: str = Field(default="PUBLIC", alias="SNOWFLAKE_SCHEMA")
    agent_read_role: str = Field(default="AGENT_READ_ROLE", alias="AGENT_READ_ROLE")
    audit_write_role: str = Field(default="AUDIT_WRITE_ROLE", alias="AUDIT_WRITE_ROLE")

    pubsub_clinical_topic: str = Field(default="clinical-records", alias="PUBSUB_CLINICAL_TOPIC")
    pubsub_lab_topic: str = Field(default="lab-updates", alias="PUBSUB_LAB_TOPIC")

    # OpenTelemetry (Phase 1.5) — empty OTLP endpoint means no remote export
    otel_service_name: str = Field(default="trialmatch", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str = Field(
        default="", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
