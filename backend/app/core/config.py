from functools import lru_cache

from pydantic import EmailStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = "EduCode Enterprise 2.0"
    app_version: str = "0.16.11.5"
    build_identifier: str = "sprint-16.11.5-hq-adaptation-interventions"
    commit_sha: str = ""
    environment: str = Field(
        default="development",
        pattern="^(development|test|homologation|staging|production)$",
    )
    debug: bool = True
    maintenance_mode: bool = False
    maintenance_access_mode: str = Field(
        default="available",
        pattern="^(available|read_only|maintenance)$",
    )
    public_base_url: str = "http://localhost:5173"
    deployment_strategy: str = Field(default="rolling", pattern="^(rolling|blue_green|canary)$")
    reverse_proxy_enabled: bool = False
    require_release_backup: bool = True
    require_release_approval: bool = True
    release_monitoring_minutes: int = Field(default=30, ge=1, le=1440)
    default_rpo_minutes: int = Field(default=1440, ge=1, le=525600)
    default_rto_minutes: int = Field(default=240, ge=1, le=525600)
    worker_drain_timeout_seconds: int = Field(default=300, ge=30, le=3600)
    secret_provider: str = Field(
        default="environment",
        pattern="^(environment|docker_secret|external_vault)$",
    )
    kubernetes_enabled: bool = False
    gitops_enabled: bool = False
    infrastructure_cluster_name: str = "educode-local"
    infrastructure_region: str = "local"
    object_storage_provider: str = Field(default="local", pattern="^(local|s3)$")
    object_storage_local_path: str = "/app/storage/objects"
    s3_endpoint_url: str = ""
    s3_bucket_name: str = "educode"
    s3_region: str = "us-east-1"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_prefix: str = "educode"
    s3_use_ssl: bool = True
    dr_automatic_failover_enabled: bool = False
    gitops_repository_url: str = ""
    gitops_target_revision: str = "main"
    health_dependency_timeout_seconds: int = Field(default=3, ge=1, le=30)
    rate_limit_window_seconds: int = Field(default=60, ge=10, le=3600)
    rate_limit_default_requests: int = Field(default=300, ge=10, le=10000)
    rate_limit_login_requests: int = Field(default=10, ge=3, le=1000)
    rate_limit_ai_requests: int = Field(default=30, ge=1, le=1000)
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    database_url: str = "postgresql+asyncpg://educode:educode_dev_password@db:5432/educode"
    document_storage_path: str = "/app/storage/documents"
    max_document_size_mb: int = Field(default=25, ge=1, le=200)
    creative_storage_path: str = "/app/storage/creative"
    max_creative_asset_size_mb: int = Field(default=25, ge=1, le=200)
    institutional_asset_storage_path: str = "/app/storage/institutional-assets"
    backup_storage_path: str = "/app/storage/backups"
    observability_metrics_token: str = ""
    metric_snapshot_interval_seconds: int = Field(default=60, ge=10, le=3600)
    metric_retention_days: int = Field(default=30, ge=1, le=3650)
    otel_enabled: bool = False
    otel_service_name: str = "educode-backend"
    otel_exporter_otlp_endpoint: str = ""
    trace_sample_ratio: float = Field(default=0.1, ge=0.0, le=1.0)
    max_institutional_asset_size_mb: int = Field(default=50, ge=1, le=500)
    retrieval_chunk_target_chars: int = Field(default=1000, ge=300, le=4000)
    retrieval_chunk_overlap_chars: int = Field(default=160, ge=0, le=800)
    retrieval_chunk_min_chars: int = Field(default=200, ge=50, le=1200)
    retrieval_default_top_k: int = Field(default=8, ge=1, le=30)

    ai_execution_mode: str = Field(default="hybrid", pattern="^(mock|hybrid|real)$")
    ai_default_timeout_seconds: int = Field(default=60, ge=5, le=300)
    redis_url: str = "redis://redis:6379/0"
    job_queue_prefix: str = "educode"
    worker_heartbeat_seconds: int = Field(default=10, ge=2, le=120)
    worker_step_delay_ms: int = Field(default=150, ge=0, le=10000)
    job_event_retention_days: int = Field(default=30, ge=1, le=365)
    max_concurrent_jobs_per_user: int = Field(default=5, ge=1, le=100)

    jwt_secret_key: str = "change-me-with-at-least-32-characters"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=240)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)
    standard_session_hours: int = Field(default=12, ge=1, le=72)
    standard_session_idle_hours: int = Field(default=8, ge=1, le=48)
    persistent_session_days: int = Field(default=30, ge=1, le=180)
    persistent_session_idle_days: int = Field(default=14, ge=1, le=90)
    auth_refresh_cookie_name: str = "educode_refresh_token"
    auth_refresh_cookie_path: str = "/api/v1/auth"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = Field(default="lax", pattern="^(lax|strict|none)$")
    password_min_length: int = Field(default=10, ge=8, le=64)
    intervention_evidence_window_days: int = Field(default=90, ge=7, le=730)
    intervention_minimum_improvement: float = Field(default=0.03, ge=0.0, le=1.0)
    intervention_retention_tolerance: float = Field(default=0.05, ge=0.0, le=1.0)
    intervention_effectiveness_min_group_size: int = Field(default=5, ge=3, le=100)
    intervention_effectiveness_refresh_limit: int = Field(default=500, ge=10, le=5000)
    governance_enforcement_mode: str = Field(default="monitor")
    governance_min_approvals: int = Field(default=2, ge=1, le=10)
    governance_min_group_size: int = Field(default=5, ge=3, le=100)
    governance_monitoring_lookback_days: int = Field(default=90, ge=7, le=730)
    governance_min_documentation_completeness: float = Field(default=0.85, ge=0.0, le=1.0)
    comic_editor_max_pages: int = Field(default=100, ge=1, le=300)
    comic_editor_default_zoom: int = Field(default=110, ge=60, le=160)
    comic_editor_ai_story_review_required: bool = Field(default=True)
    comic_editor_autosave_delay_ms: int = Field(default=2200, ge=500, le=30000)
    comic_editor_history_limit: int = Field(default=50, ge=10, le=500)
    comic_editor_cover_variations: int = Field(default=4, ge=1, le=8)
    comic_editor_readability_word_limit: int = Field(default=120, ge=20, le=500)
    comic_editor_warning_word_limit: int = Field(default=70, ge=10, le=300)
    comic_editor_custom_layout_limit: int = Field(default=100, ge=1, le=500)
    password_reset_expire_minutes: int = Field(default=30, ge=5, le=1440)
    password_reset_rate_limit: int = Field(default=3, ge=1, le=20)
    password_reset_rate_window_minutes: int = Field(default=60, ge=5, le=1440)
    rate_limit_password_reset_requests: int = Field(default=5, ge=1, le=100)
    auth_mail_delivery_mode: str = Field(default="file", pattern="^(file|smtp|disabled)$")
    auth_mail_outbox_path: str = "/app/storage/auth-mail-outbox"
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_starttls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = Field(default=15, ge=3, le=120)

    initial_admin_email: EmailStr = "admin@educode.com"
    initial_admin_password: str = "Admin@123456"
    initial_admin_name: str = "Administrador EduCode"
    initial_organization_name: str = "EduCode Enterprise"
    initial_organization_slug: str = "educode-enterprise"


def validate_runtime_security(settings: Settings) -> None:
    """Block known development credentials outside local development."""
    secret = settings.jwt_secret_key.strip().lower()
    insecure_secret = (
        len(secret) < 32
        or secret.startswith("change-me")
        or secret.startswith("troque-")
    )
    if settings.environment != "development" and insecure_secret:
        raise RuntimeError(
            "JWT_SECRET_KEY must be replaced outside the development environment."
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    validate_runtime_security(settings)
    return settings
