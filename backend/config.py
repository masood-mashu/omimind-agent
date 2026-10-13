"""
backend/config.py
Centralized, typed application configuration using Pydantic BaseModel.
Manages environment variables, Qdrant Cloud settings, Lyzr credentials, and security keys.
"""
import os

from pydantic import BaseModel, Field

# Gracefully load local .env if python-dotenv is installed
try:
    import importlib
    dotenv_module = importlib.import_module("dotenv")
    dotenv_module.load_dotenv(override=True)
except Exception:
    pass


class Settings(BaseModel):
    # Application
    app_name: str = Field(default="OMIMIND Agent", description="Service Name")
    app_version: str = Field(default="2.0.0", description="API Version")
    environment: str = Field(default="production", description="Environment runtime")
    deployment_mode: str = Field(default="multi_user", description="Supported deployment identity model")
    port: int = Field(default=8000, description="Service listen port")
    log_level: str = Field(default="INFO", description="Logging verbosity")

    # Qdrant Vector Database
    qdrant_url: str | None = Field(
        default=None,
        description="Qdrant Cloud cluster endpoint or local URL"
    )
    qdrant_host: str = Field(default="localhost", description="Qdrant fallback host")
    qdrant_port: int = Field(default=6333, description="Qdrant fallback port")
    qdrant_api_key: str | None = Field(
        default=None,
        description="Qdrant Cloud API access key"
    )
    collection_name: str = Field(
        default="omi_ambient_memory",
        description="Persistent Qdrant collection name"
    )

    # Lyzr Agent Studio
    lyzr_api_key: str | None = Field(
        default=None,
        description="Lyzr Studio API key"
    )
    lyzr_agent_id: str | None = Field(
        default=None,
        description="Lyzr Studio Agent ID"
    )
    lyzr_manager_agent_id: str | None = Field(default=None, description="Lyzr Manager Agent ID")
    lyzr_memory_recall_agent_id: str | None = Field(default=None, description="Lyzr memory recall agent ID")
    lyzr_meeting_analyst_agent_id: str | None = Field(default=None, description="Lyzr meeting analyst agent ID")
    lyzr_action_extractor_agent_id: str | None = Field(default=None, description="Lyzr action extractor agent ID")
    lyzr_followup_planner_agent_id: str | None = Field(default=None, description="Lyzr follow-up planner agent ID")
    lyzr_inference_url: str = Field(
        default="https://agent-prod.studio.lyzr.ai/v3/inference/chat/",
        description="Lyzr Studio inference endpoint"
    )
    lyzr_timeout_seconds: float = Field(
        default=45.0,
        description="Lyzr Studio inference timeout in seconds (accommodates multi-agent delegation)"
    )

    # Omi Voice Wearable
    omi_api_key: str | None = Field(
        default=None,
        description="Omi device webhook authentication key"
    )
    omi_webhook_secret: str | None = Field(default=None, description="Secret supported by the configured Omi webhook")
    webhook_database_url: str | None = Field(default=None, description="Shared Postgres URL for durable webhook deduplication")

    # Supabase multi-user identity and application database
    supabase_url: str | None = Field(default=None, description="Supabase project URL")
    supabase_publishable_key: str | None = Field(default=None, description="Supabase browser-safe publishable key")
    supabase_jwks_url: str | None = Field(default=None, description="Supabase JWT JWKS endpoint")
    supabase_service_role_key: str | None = Field(default=None, description="Server-only Supabase service role key")
    database_url: str | None = Field(default=None, description="Supabase Postgres connection URL")

    # Legacy identity setting retained only for local migration compatibility.
    default_user_id: str = Field(default="", description="Deprecated single-user identity")

    # API Security (Token / Bearer Protection)
    api_secret_key: str | None = Field(
        default=None,
        description="API secret key for endpoint protection."
    )

    def __init__(self, **data):
        super().__init__(**data)
        env_mappings = {
            "environment": "ENVIRONMENT",
            "deployment_mode": "DEPLOYMENT_MODE",
            "qdrant_url": "QDRANT_URL",
            "qdrant_api_key": "QDRANT_API_KEY",
            "collection_name": "COLLECTION_NAME",
            "lyzr_api_key": "LYZR_API_KEY",
            "lyzr_agent_id": "LYZR_AGENT_ID",
            "lyzr_manager_agent_id": "LYZR_MANAGER_AGENT_ID",
            "lyzr_memory_recall_agent_id": "LYZR_MEMORY_RECALL_AGENT_ID",
            "lyzr_meeting_analyst_agent_id": "LYZR_MEETING_ANALYST_AGENT_ID",
            "lyzr_action_extractor_agent_id": "LYZR_ACTION_EXTRACTOR_AGENT_ID",
            "lyzr_followup_planner_agent_id": "LYZR_FOLLOWUP_PLANNER_AGENT_ID",
            "lyzr_timeout_seconds": "LYZR_TIMEOUT_SECONDS",
            "api_secret_key": "API_SECRET_KEY",
            "omi_api_key": "OMI_API_KEY",
            "omi_webhook_secret": "OMI_WEBHOOK_SECRET",
            "webhook_database_url": "WEBHOOK_DATABASE_URL",
            "database_url": "DATABASE_URL",
            "supabase_url": "SUPABASE_URL",
            "supabase_publishable_key": "SUPABASE_PUBLISHABLE_KEY",
            "supabase_jwks_url": "SUPABASE_JWKS_URL",
            "supabase_service_role_key": "SUPABASE_SERVICE_ROLE_KEY",
            "default_user_id": "DEFAULT_USER_ID",
        }
        for attr, env_var in env_mappings.items():
            if attr not in data and env_var in os.environ:
                setattr(self, attr, os.environ[env_var])

        if "port" not in data and "PORT" in os.environ:
            try:
                self.port = int(os.environ["PORT"])
            except ValueError:
                pass


def is_testing() -> bool:
    import sys
    return "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ


def allow_test_tenant_overrides() -> bool:
    """Explicit test harness switch; never enabled by production configuration."""
    return is_testing() and os.environ.get("TEST_ALLOW_TENANT_OVERRIDES", "").lower() == "true"


def _missing_production_settings(cfg: Settings) -> list[str]:
    required = {
        "SUPABASE_URL": cfg.supabase_url,
        "SUPABASE_PUBLISHABLE_KEY": cfg.supabase_publishable_key,
        "SUPABASE_JWKS_URL": cfg.supabase_jwks_url or (f"{cfg.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json" if cfg.supabase_url else None),
        "SUPABASE_SERVICE_ROLE_KEY": cfg.supabase_service_role_key,
        "DATABASE_URL": cfg.database_url or cfg.webhook_database_url,
        "QDRANT_URL": cfg.qdrant_url,
        "QDRANT_API_KEY": cfg.qdrant_api_key,
        "LYZR_API_KEY": cfg.lyzr_api_key,
        "LYZR_MANAGER_AGENT_ID": cfg.lyzr_manager_agent_id,
        "LYZR_MEMORY_RECALL_AGENT_ID": cfg.lyzr_memory_recall_agent_id,
        "LYZR_MEETING_ANALYST_AGENT_ID": cfg.lyzr_meeting_analyst_agent_id,
        "LYZR_ACTION_EXTRACTOR_AGENT_ID": cfg.lyzr_action_extractor_agent_id,
        "LYZR_FOLLOWUP_PLANNER_AGENT_ID": cfg.lyzr_followup_planner_agent_id,
        "OMI_WEBHOOK_SECRET": cfg.omi_webhook_secret,
    }
    return [key for key, value in required.items() if not value]


def validate_production_config(cfg: Settings | None = None) -> None:
    """Reject unsupported identity modes and incomplete production secrets/storage."""
    active_cfg = cfg or settings
    if active_cfg.deployment_mode != "multi_user":
        raise RuntimeError("Unsupported DEPLOYMENT_MODE. This release supports only multi_user; configure DATABASE_URL (or WEBHOOK_DATABASE_URL for legacy local migrations).")
    if active_cfg.environment.lower() == "production" and not is_testing():
        missing = _missing_production_settings(active_cfg)
        if missing:
            raise RuntimeError(
                f"Missing required production configuration: {', '.join(missing)}. "
                "Production mode requires Supabase Auth, Postgres, persistent Qdrant, Omi webhook signing, and server-side identity configuration."
            )

# Singleton instance
settings = Settings()
