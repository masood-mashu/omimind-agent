"""Postgres-backed webhook inbox shared by all application instances."""
from __future__ import annotations

import json
import time
from typing import Any

from backend.webhook_store import PayloadConflictError

PROCESSING_LEASE_SECONDS = 300
RETENTION_SECONDS = 72 * 60 * 60


class PostgresWebhookStore:
    def __init__(self, database_url: str):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("Postgres webhook storage requires psycopg[binary].") from exc
        self._psycopg = psycopg
        self._dict_row = dict_row
        self.database_url = database_url
        self._init_db()

    def _connect(self):
        return self._psycopg.connect(self.database_url, row_factory=self._dict_row)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_inbox (
                    event_key TEXT PRIMARY KEY,
                    event_id TEXT,
                    payload_hash TEXT NOT NULL,
                    uid TEXT NOT NULL,
                    owner_id UUID,
                    session_id TEXT NOT NULL,
                    received_at DOUBLE PRECISION NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 1,
                    last_error TEXT,
                    payload JSONB,
                    lease_until DOUBLE PRECISION,
                    completed_at DOUBLE PRECISION,
                    CONSTRAINT webhook_inbox_uid_event_id UNIQUE (uid, event_id)
                )
            """)
            columns = {
                row["column_name"]
                for row in conn.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'webhook_inbox'"
                ).fetchall()
            }
            required = {"event_key", "event_id", "payload_hash", "uid", "owner_id", "session_id", "received_at", "status", "attempt_count", "payload", "lease_until", "completed_at"}
            missing = sorted(required - columns)
            if missing:
                raise RuntimeError(
                    "Webhook inbox schema is out of date; apply Supabase migrations 0001 and 0002 before starting the service. "
                    f"Missing columns: {', '.join(missing)}"
                )

    def record_incoming_event(self, event_id: str | None, payload_hash: str, uid: str,
                              session_id: str, payload: Any = None) -> tuple[bool, dict[str, Any]]:
        event_key = f"{uid}:{event_id}" if event_id else f"{uid}:hash:{payload_hash}"
        now = time.time()
        payload_json = json.dumps(payload, default=str) if payload is not None else None
        with self._connect() as conn:
            conn.execute("DELETE FROM webhook_inbox WHERE status IN ('completed','failed') AND received_at < %s", (now - RETENTION_SECONDS,))
            insert_result = conn.execute("""
                INSERT INTO webhook_inbox
                    (event_key,event_id,payload_hash,uid,owner_id,session_id,received_at,status,attempt_count,payload,lease_until)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'processing',1,%s::jsonb,%s)
                ON CONFLICT DO NOTHING
            """, (event_key, event_id, payload_hash, uid, uid, session_id, now, payload_json, now + PROCESSING_LEASE_SECONDS))
            inserted = insert_result.rowcount == 1
            row = conn.execute("SELECT * FROM webhook_inbox WHERE event_key=%s FOR UPDATE", (event_key,)).fetchone()
            if row is None and event_id:
                row = conn.execute("SELECT * FROM webhook_inbox WHERE uid=%s AND event_id=%s FOR UPDATE", (uid, event_id)).fetchone()
            if row is None:
                raise RuntimeError("Webhook event claim could not be read after insert.")
            record = dict(row)
            if record["payload_hash"] != payload_hash:
                raise PayloadConflictError("Webhook event ID was previously used with a different payload.")
            if inserted:
                return False, record
            if record["status"] == "completed":
                return True, record
            lease_until = record.get("lease_until")
            if record["status"] == "processing" and ((lease_until is not None and now < float(lease_until)) or (lease_until is None and now - record["received_at"] < PROCESSING_LEASE_SECONDS)):
                return True, record
            record = conn.execute("""
                UPDATE webhook_inbox SET attempt_count=attempt_count+1, status='processing',
                    received_at=%s, lease_until=%s, last_error=NULL WHERE event_key=%s RETURNING *
            """, (now, now + PROCESSING_LEASE_SECONDS, record["event_key"])).fetchone()
            return False, dict(record)

    def mark_completed(self, event_key: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE webhook_inbox SET status='completed',last_error=NULL,completed_at=%s,lease_until=NULL WHERE event_key=%s", (time.time(), event_key))

    def mark_failed(self, event_key: str, error_message: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE webhook_inbox SET status='failed',last_error=%s,completed_at=%s,lease_until=NULL WHERE event_key=%s", (error_message[:2000], time.time(), event_key))

    def get_event(self, event_key: str) -> dict[str, Any] | None:
        self.cleanup_expired()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM webhook_inbox WHERE event_key=%s", (event_key,)).fetchone()
            return dict(row) if row else None

    def cleanup_expired(self, now: float | None = None) -> int:
        cutoff = (now or time.time()) - RETENTION_SECONDS
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM webhook_inbox WHERE status IN ('completed','failed') AND received_at < %s", (cutoff,))
            return cur.rowcount

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM webhook_inbox")

    def clear_event(self, event_key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM webhook_inbox WHERE event_key=%s", (event_key,))

    def delete_owner(self, owner_id: str) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM webhook_inbox WHERE owner_id=%s OR uid=%s", (owner_id, owner_id))
            return cur.rowcount
