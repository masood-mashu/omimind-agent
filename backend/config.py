"""
backend/config.py
Centralized, typed application configuration using Pydantic BaseModel.
Manages environment variables, Qdrant Cloud settings, Lyzr credentials, and security keys.
"""
import os

from pydantic import BaseModel, Field

# Gracefully load local .env if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
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
    lyzr_inference_url: str = Field(
        default="https://agent-prod.studio.lyzr.ai/v3/inference/chat/",
        description="Lyzr Studio inference endpoint"
    )

    # Omi Voice Wearable
    omi_api_key: str | None = Field(
        default=None,
        description="Omi device webhook authentication key"
    )

    # API Security (Optional Token / Bearer Protection)
    api_secret_key: str | None = Field(
        default=None,
        description="Optional API secret key for endpoint protection. If None, runs in open demo mode."
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Populate from os.environ only if not explicitly passed in data
        if "qdrant_url" not in data and "QDRANT_URL" in os.environ:
            self.qdrant_url = os.environ["QDRANT_URL"]
        if "qdrant_api_key" not in data and "QDRANT_API_KEY" in os.environ:
            self.qdrant_api_key = os.environ["QDRANT_API_KEY"]
        if "lyzr_api_key" not in data and "LYZR_API_KEY" in os.environ:
            self.lyzr_api_key = os.environ["LYZR_API_KEY"]
        if "lyzr_agent_id" not in data and "LYZR_AGENT_ID" in os.environ:
            self.lyzr_agent_id = os.environ["LYZR_AGENT_ID"]
        if "api_secret_key" not in data and "API_SECRET_KEY" in os.environ:
            self.api_secret_key = os.environ["API_SECRET_KEY"]
        if "omi_api_key" not in data and "OMI_API_KEY" in os.environ:
            self.omi_api_key = os.environ["OMI_API_KEY"]
        if "port" not in data and "PORT" in os.environ:
            try:
                self.port = int(os.environ["PORT"])
            except ValueError:
                pass


# Singleton instance
settings = Settings()
