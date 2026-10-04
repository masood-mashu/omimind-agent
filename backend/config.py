"""
backend/config.py
Centralized, typed application configuration using Pydantic BaseSettings.
Manages environment variables, Qdrant Cloud settings, Lyzr credentials, and security keys.
"""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

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


# Singleton instance
settings = Settings()
