"""
api_models.py - Request and Response Pydantic Schemas for OmiMind API
"""
from typing import Any

from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    meeting_id: str


class CustomVoiceRequest(BaseModel):
    title: str = "Live Omi Voice Memo"
    speaker: str = "User"
    transcript: str


class QueryRequest(BaseModel):
    question: str
    limit: int = Field(default=4, ge=1, le=20)
    uid: str = "default_user"


class OmiWebhookRequest(BaseModel):
    """Native Omi device webhook payload format."""
    session_id: str | None = None
    segments: list[dict[str, Any]] | None = None
    transcript: str | None = None
    speaker: str | None = "Omi User"
    uid: str | None = "default_user"
