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
    dotenv_module.load_dotenv()
except Exception:
    pass


class Settings(BaseModel):
    # Application
    app_name: str = Field(default="OmiMind Agent", description="Service Name")
    app_version: str = Field(default="2.0.0", description="API Version")
    environment: str = Field(default="production", description="Environment runtime")
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

    # Identity & Authorization
    default_user_id: str = Field(
        default="default_user",
        description="Configured server-side user identity for single-user deployment"
    )

    # API Security (Token / Bearer Protection)
    api_secret_key: str | None = Field(
        default=None,
        description="API secret key for endpoint protection."
    )

    def __init__(self, **data):
        super().__init__(**data)
        env_mappings = {
            "environment": "ENVIRONMENT",
            "qdrant_url": "QDRANT_URL",
            "qdrant_api_key": "QDRANT_API_KEY",
            "collection_name": "COLLECTION_NAME",
            "lyzr_api_key": "LYZR_API_KEY",
            "lyzr_agent_id": "LYZR_AGENT_ID",
            "lyzr_manager_agent_id": "LYZR_MANAGER_AGENT_ID",
            "lyzr_timeout_seconds": "LYZR_TIMEOUT_SECONDS",
            "api_secret_key": "API_SECRET_KEY",
            "omi_api_key": "OMI_API_KEY",
            "omi_webhook_secret": "OMI_WEBHOOK_SECRET",
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
    return "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ or os.environ.get("ENVIRONMENT") == "test"


def validate_production_config(cfg: Settings | None = None) -> None:
    """
    Validates required configuration in production environment.
    Fails clearly when persistence, API authentication, Qdrant, or webhook secrets are missing.
    """
    active_cfg = cfg or settings
    if active_cfg.environment.lower() == "production" and not is_testing():
        missing: list[str] = []
        if not active_cfg.api_secret_key:
            missing.append("API_SECRET_KEY")
        if not active_cfg.qdrant_url:
            missing.append("QDRANT_URL")
        if not active_cfg.omi_webhook_secret:
            missing.append("OMI_WEBHOOK_SECRET")
        if missing:
            raise RuntimeError(
                f"Missing required production configuration: {', '.join(missing)}. "
                "Production mode requires persistent Qdrant, API authentication, and Omi webhook secrets."
            )

# Singleton instance
settings = Settings()
