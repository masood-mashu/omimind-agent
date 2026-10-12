"""Small persistence layer for multi-user connections and agent traces.

Production uses the configured Supabase Postgres URL. Local development uses
an explicit SQLite file, never serverless scratch storage.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import tempfile
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from backend.config import is_testing, settings


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class TenantStore:
    def __init__(self, database_url: str | None = None, sqlite_path: str | None = None):
        if database_url is not None:
            self.database_url = database_url
        elif is_testing() or sqlite_path is not None:
            self.database_url = None
        else:
            self.database_url = settings.database_url or settings.webhook_database_url

        if sqlite_path:
            self.sqlite_path = sqlite_path
        elif is_testing():
            self.sqlite_path = os.path.join(tempfile.gettempdir(), f"omimind_test_tenant_{os.getpid()}.db")
        else:
            self.sqlite_path = "./qdrant_storage/omimind_app.db"

        self.dialect = "postgres" if self.database_url else "sqlite"
        self._init_db()

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        if self.dialect == "postgres":
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:
                raise RuntimeError("Postgres tenant storage requires psycopg[binary].") from exc
            with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
                yield conn
            return
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _sql(self, query: str) -> str:
        return query.replace("?", "%s") if self.dialect == "postgres" else query

    def _json_value(self, value: Any) -> Any:
        if self.dialect != "postgres":
            return json.dumps(value, default=str)
        from psycopg.types.json import Json
        return Json(value)

    def _init_db(self) -> None:
        if self.dialect == "sqlite":
            import os
            os.makedirs(os.path.dirname(self.sqlite_path) or ".", exist_ok=True)
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS omi_connections (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                omi_user_id TEXT,
                device_label TEXT,
                token_hash TEXT NOT NULL UNIQUE,
                pairing_code_hash TEXT,
                pairing_expires_at DOUBLE PRECISION,
                status TEXT NOT NULL DEFAULT 'pairing',
                last_event_at DOUBLE PRECISION,
                created_at DOUBLE PRECISION NOT NULL,
                rotated_at DOUBLE PRECISION
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS meeting_runs (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                meeting_id TEXT,
                session_id TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                provider TEXT,
                dossier_json TEXT,
                created_at DOUBLE PRECISION NOT NULL,
                completed_at DOUBLE PRECISION
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                title TEXT NOT NULL,
                transcript_json TEXT NOT NULL DEFAULT '[]',
                summary_json TEXT,
                created_at DOUBLE PRECISION NOT NULL,
                updated_at DOUBLE PRECISION NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS action_items (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                meeting_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                assignee TEXT,
                due_at DOUBLE PRECISION,
                status TEXT NOT NULL DEFAULT 'open',
                source_event_id TEXT,
                metadata TEXT,
                created_at DOUBLE PRECISION NOT NULL,
                updated_at DOUBLE PRECISION NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_events (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                role TEXT,
                agent_id TEXT,
                status TEXT,
                provider TEXT,
                execution_source TEXT,
                payload_json TEXT NOT NULL,
                created_at DOUBLE PRECISION NOT NULL
            )
            """,
        ]
        with self._connection() as conn:
            for statement in ddl:
                conn.execute(self._sql(statement))
            if self.dialect == "sqlite":
                columns = {row[1] for row in conn.execute("PRAGMA table_info(meeting_runs)").fetchall()}
                if "meeting_id" not in columns:
                    conn.execute("ALTER TABLE meeting_runs ADD COLUMN meeting_id TEXT")
            else:
                required_columns = {
                    "omi_connections": {"id", "owner_id", "token_hash"},
                    "meeting_runs": {"id", "owner_id", "meeting_id", "dossier_json"},
                    "agent_events": {"id", "run_id", "owner_id", "payload_json"},
                    "meetings": {"id", "owner_id", "transcript", "summary"},
                    "action_items": {"id", "owner_id", "meeting_id", "metadata"},
                }
                for table, required in required_columns.items():
                    columns = {row["column_name"] for row in conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = %s", (table,)).fetchall()}
                    missing = sorted(required - columns)
                    if missing:
                        raise RuntimeError(f"Tenant schema for {table} is out of date; apply Supabase migrations 0001 and 0002. Missing columns: {', '.join(missing)}")

    def start_pairing(self, owner_id: str) -> dict[str, Any]:
        connection_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        code = f"{secrets.randbelow(1_000_000):06d}"
        now = time.time()
        expires = now + 15 * 60
        with self._connection() as conn:
            conn.execute(
                self._sql("INSERT INTO omi_connections (id,owner_id,token_hash,pairing_code_hash,pairing_expires_at,status,created_at) VALUES (?,?,?,?,?,?,?)"),
                (connection_id, owner_id, hash_secret(token), hash_secret(code), expires, "pairing", now),
            )
        return {"id": connection_id, "pairing_code": code, "connection_token": token, "expires_at": expires}

    def complete_pairing(self, owner_id: str, pairing_code: str, omi_user_id: str, device_label: str | None = None) -> dict[str, Any]:
        now = time.time()
        with self._connection() as conn:
            row = conn.execute(
                self._sql("SELECT * FROM omi_connections WHERE owner_id=? AND pairing_code_hash=? AND status='pairing'"),
                (owner_id, hash_secret(pairing_code)),
            ).fetchone()
            if not row or float(row["pairing_expires_at"]) < now:
                raise ValueError("Pairing code is invalid or expired.")
            conn.execute(
                self._sql("UPDATE omi_connections SET omi_user_id=?,device_label=?,pairing_code_hash=NULL,pairing_expires_at=NULL,status='active' WHERE id=? AND owner_id=?"),
                (omi_user_id, device_label, row["id"], owner_id),
            )
            return dict(row) | {"omi_user_id": omi_user_id, "device_label": device_label, "status": "active"}

    def list_connections(self, owner_id: str) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(self._sql("SELECT id,omi_user_id,device_label,status,last_event_at,created_at,rotated_at FROM omi_connections WHERE owner_id=? ORDER BY created_at DESC"), (owner_id,)).fetchall()
            return [dict(row) for row in rows]

    def rotate_connection(self, owner_id: str, connection_id: str) -> dict[str, Any]:
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self._connection() as conn:
            result = conn.execute(self._sql("UPDATE omi_connections SET token_hash=?,rotated_at=?,status='active' WHERE id=? AND owner_id=?"), (hash_secret(token), now, connection_id, owner_id))
            if result.rowcount != 1:
                raise KeyError("Omi connection not found")
        return {"id": connection_id, "connection_token": token, "rotated_at": now}

    def delete_connection(self, owner_id: str, connection_id: str) -> bool:
        with self._connection() as conn:
            result = conn.execute(self._sql("DELETE FROM omi_connections WHERE id=? AND owner_id=?"), (connection_id, owner_id))
            return result.rowcount == 1

    def resolve_connection(self, token: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute(self._sql("SELECT * FROM omi_connections WHERE token_hash=? AND status='active'"), (hash_secret(token),)).fetchone()
            return dict(row) if row else None

    def resolve_pending_connection(self, token: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute(self._sql("SELECT * FROM omi_connections WHERE token_hash=? AND status='pairing'"), (hash_secret(token),)).fetchone()
            return dict(row) if row else None

    def touch_connection(self, connection_id: str) -> None:
        with self._connection() as conn:
            conn.execute(self._sql("UPDATE omi_connections SET last_event_at=? WHERE id=?"), (time.time(), connection_id))

    def create_run(self, owner_id: str, session_id: str, title: str) -> str:
        run_id = str(uuid.uuid4())
        with self._connection() as conn:
            conn.execute(self._sql("INSERT INTO meeting_runs (id,owner_id,session_id,title,status,created_at) VALUES (?,?,?,?,?,?)"), (run_id, owner_id, session_id, title, "running", time.time()))
        return run_id

    def append_event(self, owner_id: str, run_id: str, event: dict[str, Any]) -> str:
        event_id = str(uuid.uuid4())
        role = event.get("role") or event.get("agent") or "pipeline"
        status = event.get("status") or "unknown"
        with self._connection() as conn:
            conn.execute(self._sql("INSERT INTO agent_events (id,run_id,owner_id,event_type,role,agent_id,status,provider,execution_source,payload_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)"), (event_id, run_id, owner_id, event.get("type", "event"), role, event.get("agent_id"), status, event.get("provider"), event.get("execution_source"), self._json_value(event), time.time()))
        return event_id

    def complete_run(
        self,
        owner_id: str,
        run_id: str,
        dossier: dict[str, Any],
        provider: str | None = None,
        transcript_lines: list[dict[str, Any]] | None = None,
    ) -> None:
        now = time.time()
        title = str(dossier.get("title") or "Untitled meeting")
        transcript = transcript_lines or dossier.get("transcript_lines") or []
        db_now = datetime.fromtimestamp(now, tz=timezone.utc) if self.dialect == "postgres" else now
        with self._connection() as conn:
            if self.dialect == "postgres":
                conn.execute("INSERT INTO meetings (id,owner_id,title,transcript,summary,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title,transcript=EXCLUDED.transcript,summary=EXCLUDED.summary,updated_at=EXCLUDED.updated_at", (run_id, owner_id, title, self._json_value(transcript), self._json_value(dossier.get("summary", {})), db_now, db_now))
            else:
                conn.execute("INSERT INTO meetings (id,owner_id,title,transcript_json,summary_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title,transcript_json=EXCLUDED.transcript_json,summary_json=EXCLUDED.summary_json,updated_at=EXCLUDED.updated_at", (run_id, owner_id, title, self._json_value(transcript), self._json_value(dossier.get("summary", {})), db_now, db_now))
            conn.execute(self._sql("DELETE FROM action_items WHERE meeting_id=? AND owner_id=?"), (run_id, owner_id))
            for item in dossier.get("action_items", []) or []:
                item_id = str(uuid.uuid4())
                conn.execute(self._sql("INSERT INTO action_items (id,owner_id,meeting_id,title,description,assignee,due_at,status,source_event_id,metadata,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"), (item_id, owner_id, run_id, str(item.get("title") or "Untitled action"), str(item.get("quote") or item.get("description") or ""), str(item.get("assignee") or "Team"), None, str(item.get("status") or "open").lower(), None, self._json_value(item), now, now))
            conn.execute(self._sql("UPDATE meeting_runs SET status='completed',meeting_id=?,provider=?,dossier_json=?,completed_at=? WHERE id=? AND owner_id=?"), (run_id, provider, self._json_value(dossier), now, run_id, owner_id))

    def fail_run(self, owner_id: str, run_id: str, error: str) -> None:
        with self._connection() as conn:
            conn.execute(self._sql("UPDATE meeting_runs SET status='failed',dossier_json=?,completed_at=? WHERE id=? AND owner_id=?"), (self._json_value({"error": error}), time.time(), run_id, owner_id))

    def list_events(self, owner_id: str, run_id: str) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(self._sql("SELECT payload_json FROM agent_events WHERE owner_id=? AND run_id=? ORDER BY created_at ASC"), (owner_id, run_id)).fetchall()
            return [row["payload_json"] if isinstance(row["payload_json"], dict) else json.loads(row["payload_json"]) for row in rows]

    def delete_owner(self, owner_id: str) -> None:
        with self._connection() as conn:
            for table in ("agent_events", "action_items", "meetings", "meeting_runs", "omi_connections"):
                conn.execute(self._sql(f"DELETE FROM {table} WHERE owner_id=?"), (owner_id,))

    def list_actions(self, owner_id: str) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(self._sql("SELECT a.id,a.title,a.description,a.assignee,a.due_at,a.status,a.metadata,m.title AS source_meeting FROM action_items a LEFT JOIN meetings m ON m.id=a.meeting_id WHERE a.owner_id=? ORDER BY a.created_at DESC"), (owner_id,)).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                data = dict(row)
                metadata = data.pop("metadata", None)
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = None
                if isinstance(metadata, dict):
                    metadata.update({k: v for k, v in data.items() if k not in metadata or v is not None})
                    data = metadata
                data["source_meeting"] = data.get("source_meeting") or "Untitled meeting"
                result.append(data)
            return result


tenant_store = TenantStore()
