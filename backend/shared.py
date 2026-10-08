"""
shared.py - Shared application state, singletons, and utility functions
"""
import re
import time
from typing import Any

from agents.orchestrator import OmiMindOrchestrator

# Initialize persistent orchestrator singleton
orchestrator = OmiMindOrchestrator(storage_path="./qdrant_storage")

# Active processed sessions cache
processed_cache: dict[str, Any] = {}
processed_cache_owners: dict[str, str] = {}


def cache_processed(session_id: str, dossier: dict[str, Any], uid: str) -> None:
    processed_cache[session_id] = dossier
    processed_cache_owners[session_id] = uid


def get_processed_for_user(session_id: str, uid: str) -> dict[str, Any] | None:
    if processed_cache_owners.get(session_id) != uid:
        return None
    dossier = processed_cache.get(session_id)
    return dossier if isinstance(dossier, dict) else None


def iter_processed_for_user(uid: str):
    for session_id, dossier in processed_cache.items():
        if processed_cache_owners.get(session_id) == uid and isinstance(dossier, dict):
            yield session_id, dossier


def parse_transcript(transcript: str, default_speaker: str = "User") -> tuple[list[dict], set]:
    """Helper: parse raw transcript text blocks into structured utterances with speaker attribution."""
    raw_blocks = re.split(r"\n+", transcript.strip())
    speaker_pattern = re.compile(r"^(?:\[([\d\:\.]+)\]\s*)?([A-Z][A-Za-z0-9\s\.\(\)\-_]{1,35}):\s*(.+)$")
    lines = []
    detected_speakers = set()
    current_speaker = default_speaker

    for block in raw_blocks:
        block_str = block.strip()
        if not block_str:
            continue
        m = speaker_pattern.match(block_str)
        if m:
            timestamp_match = m.group(1)
            current_speaker = m.group(2).strip()
            content = m.group(3).strip()
            detected_speakers.add(current_speaker)
            timestamp_str = timestamp_match if timestamp_match else time.strftime("%H:%M:%S", time.gmtime())
        else:
            content = block_str
            timestamp_str = time.strftime("%H:%M:%S", time.gmtime())

        sentences = re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"'\-])", content)
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 3:
                lines.append({
                    "speaker": current_speaker,
                    "timestamp_str": timestamp_str,
                    "text": s_clean
                })

    return lines, detected_speakers
