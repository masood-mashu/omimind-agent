"""
backend/config.py
Centralized, typed application configuration using Pydantic BaseSettings.
Manages environment variables, Qdrant Cloud settings, Lyzr credentials, and security keys.
"""
import os
from typing import Optional
from pydantic import Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    class _SettingsBase(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )
except Exception:
    from pydantic import BaseModel
    class _SettingsBase(BaseModel):
        pass


class Settings(_SettingsBase):
    # Application
    app_name: str = Field(default="OmiMind Agent", description="Service Name")
    app_version: str = Field(default="2.0.0", description="API Version")
    environment: str = Field(default="production", description="Environment runtime")
    port: int = Field(default=8000, description="Service listen port")
    log_level: str = Field(default="INFO", description="Logging verbosity")

    # Qdrant Vector Database
    qdrant_url: Optional[str] = Field(
        default=None,
        description="Qdrant Cloud cluster endpoint or local URL"
    )
    qdrant_host: str = Field(default="localhost", description="Qdrant fallback host")
    qdrant_port: int = Field(default=6333, description="Qdrant fallback port")
    qdrant_api_key: Optional[str] = Field(
        default=None,
        description="Qdrant Cloud API access key"
    )
    collection_name: str = Field(
        default="omi_ambient_memory",
        description="Persistent Qdrant collection name"
    )

    # Lyzr Agent Studio
    lyzr_api_key: Optional[str] = Field(
        default=None,
        description="Lyzr Studio API key"
    )
    lyzr_agent_id: Optional[str] = Field(
        default=None,
        description="Lyzr Studio Agent ID"
    )
    lyzr_inference_url: str = Field(
        default="https://agent-prod.studio.lyzr.ai/v3/inference/chat/",
        description="Lyzr Studio inference endpoint"
    )

    # Omi Voice Wearable
    omi_api_key: Optional[str] = Field(
        default=None,
        description="Omi device webhook authentication key"
    )

    # API Security (Optional Token / Bearer Protection)
    api_secret_key: Optional[str] = Field(
        default=None,
        description="Optional API secret key for endpoint protection. If None, runs in open demo mode."
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Fallback to direct os.environ if BaseSettings did not populate
        if not self.qdrant_url:
            self.qdrant_url = os.environ.get("QDRANT_URL")
        if not self.qdrant_api_key:
            self.qdrant_api_key = os.environ.get("QDRANT_API_KEY")
        if not self.lyzr_api_key:
            self.lyzr_api_key = os.environ.get("LYZR_API_KEY")
        if not self.lyzr_agent_id:
            self.lyzr_agent_id = os.environ.get("LYZR_AGENT_ID")
        if not self.api_secret_key:
            self.api_secret_key = os.environ.get("API_SECRET_KEY")


# Singleton instance
settings = Settings()
