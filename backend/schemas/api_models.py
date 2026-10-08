"""
api_models.py - Request and Response Pydantic Schemas for OmiMind API
Strict input validation bounds preventing resource exhaustion and abuse.
"""
from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_TRANSCRIPT_LENGTH = 50_000
MAX_QUERY_LENGTH = 1_000
MAX_TITLE_LENGTH = 200
MAX_SPEAKER_LENGTH = 100
MAX_SEGMENTS_COUNT = 500
MAX_SEGMENT_TEXT_LENGTH = 2_000
MAX_TIMESTAMP_SECONDS = 864_000.0  # 10 days


class ProcessRequest(BaseModel):
    meeting_id: str = Field(..., min_length=1, max_length=128)


class CustomVoiceRequest(BaseModel):
    title: str = Field(default="Live Omi Voice Memo", min_length=1, max_length=MAX_TITLE_LENGTH)
    speaker: str = Field(default="User", min_length=1, max_length=MAX_SPEAKER_LENGTH)
    transcript: str = Field(..., min_length=1, max_length=MAX_TRANSCRIPT_LENGTH)

    @model_validator(mode="before")
    @classmethod
    def map_title_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "meeting_title" in data and "title" not in data:
                data["title"] = data["meeting_title"]
        return data


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    limit: int = Field(default=4, ge=1, le=20)
    uid: str | None = Field(default="default_user", max_length=128)

    @model_validator(mode="before")
    @classmethod
    def map_query_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "query" in data and "question" not in data:
                data["question"] = data["query"]
        return data


class OmiWebhookRequest(BaseModel):
    """Native Omi device webhook payload format with strict validation."""
    session_id: str | None = Field(default=None, max_length=128)
    event_id: str | None = Field(default=None, max_length=128)
    segments: list[dict[str, Any]] | None = None
    transcript: str | None = None
    speaker: str | None = Field(default="Omi User", max_length=MAX_SPEAKER_LENGTH)
    uid: str | None = Field(default="default_user", max_length=128)

    @model_validator(mode="before")
    @classmethod
    def map_event_id_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "id" in data and "event_id" not in data:
            data["event_id"] = data["id"]
        return data

    @field_validator("transcript")
    @classmethod
    def validate_transcript(cls, v: str | None) -> str | None:
        if v is not None and len(v) > MAX_TRANSCRIPT_LENGTH:
            raise ValueError(f"Transcript exceeds maximum allowed length of {MAX_TRANSCRIPT_LENGTH} characters")
        return v

    @field_validator("segments")
    @classmethod
    def validate_segments(cls, v: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if v is not None:
            if len(v) > MAX_SEGMENTS_COUNT:
                raise ValueError(f"Number of segments exceeds maximum limit of {MAX_SEGMENTS_COUNT}")
            for idx, seg in enumerate(v):
                if not isinstance(seg, dict):
                    raise ValueError(f"Segment at index {idx} must be a dictionary object")
                text = seg.get("text")
                if text is not None and len(str(text)) > MAX_SEGMENT_TEXT_LENGTH:
                    raise ValueError(
                        f"Segment text at index {idx} exceeds maximum allowed length of {MAX_SEGMENT_TEXT_LENGTH} characters"
                    )
                speaker = seg.get("speaker")
                if speaker is not None and len(str(speaker)) > MAX_SPEAKER_LENGTH:
                    raise ValueError(
                        f"Segment speaker at index {idx} exceeds maximum allowed length of {MAX_SPEAKER_LENGTH} characters"
                    )
                start = seg.get("start")
                if start is not None:
                    try:
                        start_val = float(start)
                        if math.isnan(start_val) or math.isinf(start_val) or start_val < 0.0 or start_val > MAX_TIMESTAMP_SECONDS:
                            raise ValueError(f"Segment start timestamp at index {idx} must be a valid non-negative number")
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"Segment start timestamp at index {idx} must be a numeric value") from exc
        return v
