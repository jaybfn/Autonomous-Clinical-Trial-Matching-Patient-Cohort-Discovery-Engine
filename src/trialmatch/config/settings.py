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

    # Embeddings (Phase 6) — provider: deterministic | vertex
    embedding_provider: str = Field(default="deterministic", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-004", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=768, alias="EMBEDDING_DIMENSION")

    snowflake_account: str = Field(default="", alias="SNOWFLAKE_ACCOUNT")
    snowflake_user: str = Field(default="", alias="SNOWFLAKE_USER")
    snowflake_warehouse: str = Field(default="", alias="SNOWFLAKE_WAREHOUSE")
    snowflake_database: str = Field(default="", alias="SNOWFLAKE_DATABASE")
    snowflake_schema: str = Field(default="PUBLIC", alias="SNOWFLAKE_SCHEMA")
    # Path to PEM on disk (often fetched from Secret Manager) — never the key material itself.
    snowflake_private_key_path: str = Field(default="", alias="SNOWFLAKE_PRIVATE_KEY_PATH")
    agent_read_role: str = Field(default="AGENT_READ_ROLE", alias="AGENT_READ_ROLE")
    audit_write_role: str = Field(default="AUDIT_WRITE_ROLE", alias="AUDIT_WRITE_ROLE")

    pubsub_clinical_topic: str = Field(default="clinical-records", alias="PUBSUB_CLINICAL_TOPIC")
    pubsub_lab_topic: str = Field(default="lab-updates", alias="PUBSUB_LAB_TOPIC")

    # OpenTelemetry (Phase 1.5) — empty OTLP endpoint means no remote export
    otel_service_name: str = Field(default="trialmatch", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str = Field(default="", alias="OTEL_EXPORTER_OTLP_ENDPOINT")

    # LLM provider for Parser (Phase 8): ollama (local, $0 tokens) | vertex (ADC)
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")
    # Vertex LLM — ADC / Workload Identity only; never API keys
    vertex_llm_model: str = Field(default="gemini-2.0-flash-001", alias="VERTEX_LLM_MODEL")
    vertex_llm_location: str = Field(default="us-central1", alias="VERTEX_LLM_LOCATION")
    # Ollama (local / self-hosted) — native /api/chat, no API keys
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_llm_model: str = Field(default="llama3.1:8b", alias="OLLAMA_LLM_MODEL")
