"""
backend/webhook_inbox.py
Durable webhook inbox and deduplication store backed by SQLite.
Guarantees deduplication across process restarts and worker processes.
Tracks event status (received, processing, completed, failed) and attempt counts.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import tempfile
import time
from typing import Any

from backend.config import is_testing

logger = logging.getLogger("omimind.webhook_inbox")
PROCESSING_LEASE_SECONDS = 300


def _get_db_path() -> str:
    override = os.environ.get("WEBHOOK_INBOX_DB_PATH")
    if override:
        return override
    if is_testing():
        return os.path.join(tempfile.gettempdir(), f"omimind_test_inbox_{os.getpid()}.db")
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("LAMBDA_TASK_ROOT"):
        return os.path.join(tempfile.gettempdir(), "omimind_webhook_inbox.db")
    storage_dir = os.path.abspath("qdrant_storage")
    os.makedirs(storage_dir, exist_ok=True)
    return os.path.join(storage_dir, "webhook_inbox.db")


class WebhookInbox:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or _get_db_path()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000;")
        # Enable WAL mode for concurrent multi-process reading and writing
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_inbox (
                    event_key TEXT PRIMARY KEY,
                    event_id TEXT,
                    payload_hash TEXT NOT NULL,
                    uid TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    received_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 1,
                    last_error TEXT,
                    payload_json TEXT
                );
                """
            )
            conn.commit()

    def record_incoming_event(
        self,
        event_id: str | None,
        payload_hash: str,
        uid: str,
        session_id: str,
        payload: Any = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Durable deduplication and inbox record insertion.
        Returns:
            (is_duplicate, record_dict)
            - is_duplicate is True only if status is 'completed'.
            - If status is 'failed' or 'received', allows retry and increments attempt_count.
        """
        event_key = f"{uid}:{event_id}" if event_id else f"{uid}:hash:{payload_hash}"
        now = time.time()
        payload_json = json.dumps(payload, default=str) if payload is not None else None

        with self._get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM webhook_inbox WHERE event_key = ?", (event_key,))
            existing = cursor.fetchone()

            if existing:
                existing_dict = dict(existing)
                # If already completed, safe duplicate
                if existing_dict["status"] == "completed":
                    return True, existing_dict

                # A recent processing record is owned by another request. Do not
                # run the same event concurrently. A stale lease may be retried.
                if existing_dict["status"] == "processing" and now - existing_dict["received_at"] < PROCESSING_LEASE_SECONDS:
                    return True, existing_dict

                # Failed or stale processing events may be retried.
                new_attempts = existing_dict["attempt_count"] + 1
                cursor.execute(
                    """
                    UPDATE webhook_inbox
                    SET attempt_count = ?, status = 'processing', received_at = ?, last_error = NULL
                    WHERE event_key = ?
                    """,
                    (new_attempts, now, event_key),
                )
                conn.commit()
                existing_dict["attempt_count"] = new_attempts
                existing_dict["status"] = "processing"
                return False, existing_dict

            # New incoming event: persist before processing
            cursor.execute(
                """
                INSERT INTO webhook_inbox (
                    event_key, event_id, payload_hash, uid, session_id,
                    received_at, status, attempt_count, last_error, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, 'processing', 1, NULL, ?)
                """,
                (event_key, event_id, payload_hash, uid, session_id, now, payload_json),
            )
            conn.commit()
            return False, {
                "event_key": event_key,
                "event_id": event_id,
                "payload_hash": payload_hash,
                "uid": uid,
                "session_id": session_id,
                "received_at": now,
                "status": "processing",
                "attempt_count": 1,
            }

    def mark_completed(self, event_key: str) -> None:
        """Marks event durably completed after successful processing/indexing."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE webhook_inbox SET status = 'completed', last_error = NULL WHERE event_key = ?",
                (event_key,),
            )
            conn.commit()

    def mark_failed(self, event_key: str, error_message: str) -> None:
        """Marks event failed so subsequent retries are permitted."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE webhook_inbox SET status = 'failed', last_error = ? WHERE event_key = ?",
                (error_message[:2000], event_key),
            )
            conn.commit()

    def get_event(self, event_key: str) -> dict[str, Any] | None:
        """Retrieves durable event record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM webhook_inbox WHERE event_key = ?", (event_key,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def clear(self) -> None:
        """Utility for test isolation."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM webhook_inbox")
            conn.commit()


# Singleton instance
default_webhook_inbox = WebhookInbox()
