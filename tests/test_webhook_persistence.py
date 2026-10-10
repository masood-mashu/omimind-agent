"""
tests/test_webhook_persistence.py
Tests for Phase 3: Durable webhook inbox persistence, retry semantics, deduplication across process restarts,
and multi-tenant isolation.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app
from backend.webhook_inbox import WebhookInbox, default_webhook_inbox

client = TestClient(app)
VALID_WEBHOOK_SECRET = "test_webhook_secret_xyz_98765"


@pytest.fixture(autouse=True)
def setup_webhook_env(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "api_secret_key", "test_api_key_valid")
    monkeypatch.setattr(settings, "omi_webhook_secret", VALID_WEBHOOK_SECRET)
    monkeypatch.setattr(settings, "default_user_id", "default_user")

    test_db = str(tmp_path / "test_inbox.db")
    monkeypatch.setenv("WEBHOOK_INBOX_DB_PATH", test_db)
    # Replace default inbox db_path and initialize
    default_webhook_inbox.db_path = test_db
    default_webhook_inbox._init_db()


def _valid_headers(timestamp: float | None = None, token_suffix: str = "") -> dict[str, str]:
    ts = str(timestamp if timestamp is not None else time.time())
    token = f"{VALID_WEBHOOK_SECRET}:{token_suffix}" if token_suffix else VALID_WEBHOOK_SECRET
    return {
        "x-omi-webhook-secret": token,
        "x-omi-timestamp": ts,
    }


class TestWebhookPersistenceAndRetry:
    def test_first_delivery_persists_and_marks_completed(self):
        payload = {
            "session_id": "sess_durable_1",
            "segments": [
                {"speaker": "David", "text": "We are deploying the ambient intelligence node.", "start": 10}
            ],
        }
        resp = client.post("/api/omi-webhook", json=payload, headers=_valid_headers())
        assert resp.status_code == 202
        assert resp.json()["status"] == "accepted"

        # Verify inbox record is durably stored and marked completed
        event_key = "default_user:sess_durable_1"
        event = default_webhook_inbox.get_event(event_key)
        assert event is not None
        assert event["status"] == "completed"
        assert event["attempt_count"] == 1
        assert event["session_id"] == "sess_durable_1"

    def test_duplicate_delivery_is_safe_and_returns_duplicate(self):
        payload = {
            "session_id": "sess_dup_1",
            "transcript": "First delivery transcript message.",
        }
        # First delivery
        resp1 = client.post("/api/omi-webhook", json=payload, headers=_valid_headers())
        assert resp1.status_code == 202
        assert resp1.json()["status"] == "accepted"

        # Duplicate delivery
        resp2 = client.post("/api/omi-webhook", json=payload, headers=_valid_headers())
        assert resp2.status_code == 202
        assert resp2.json()["status"] == "duplicate"
        assert "already processed" in resp2.json()["message"]

    def test_retry_after_processing_failure_is_allowed(self):
        payload = {
            "session_id": "sess_fail_retry",
            "transcript": "Testing failure and retry recovery.",
        }
        event_key = "default_user:sess_fail_retry"

        # 1. Simulate failure during vector persistence
        with patch("backend.shared.orchestrator.memory.index_utterance", side_effect=RuntimeError("Qdrant write failed")):
            resp_fail = client.post("/api/omi-webhook", json=payload, headers=_valid_headers())
            assert resp_fail.status_code == 500

        # Verify inbox has marked it as failed with attempt_count 1
        record = default_webhook_inbox.get_event(event_key)
        assert record is not None
        assert record["status"] == "failed"
        assert "Qdrant write failed" in record["last_error"]
        assert record["attempt_count"] == 1

        # 2. Retry delivery (now succeeding)
        resp_retry = client.post("/api/omi-webhook", json=payload, headers=_valid_headers())
        assert resp_retry.status_code == 202
        assert resp_retry.json()["status"] == "accepted"

        # Verify inbox updated to completed with attempt_count 2
        record_after = default_webhook_inbox.get_event(event_key)
        assert record_after["status"] == "completed"
        assert record_after["attempt_count"] == 2

    def test_restart_preserves_deduplication_across_new_inbox_instance(self, tmp_path):
        payload = {
            "session_id": "sess_restart_1",
            "transcript": "Will survive process restart.",
        }
        resp = client.post("/api/omi-webhook", json=payload, headers=_valid_headers())
        assert resp.status_code == 202

        # Simulate fresh process opening the same SQLite DB file
        fresh_inbox = WebhookInbox(db_path=default_webhook_inbox.db_path)
        event = fresh_inbox.get_event("default_user:sess_restart_1")
        assert event is not None
        assert event["status"] == "completed"

        # Another delivery should still be recognized as duplicate
        resp2 = client.post("/api/omi-webhook", json=payload, headers=_valid_headers())
        assert resp2.status_code == 202
        assert resp2.json()["status"] == "duplicate"

    def test_invalid_signature_rejected(self):
        payload = {"session_id": "sess_sig_invalid", "transcript": "test"}
        headers = {
            "x-omi-signature": "sha256=bad_hex_signature",
            "x-omi-timestamp": str(time.time()),
        }
        resp = client.post("/api/omi-webhook", json=payload, headers=headers)
        assert resp.status_code == 401
        assert "Invalid webhook credentials" in resp.json()["detail"]

    def test_expired_timestamp_rejected(self):
        payload = {"session_id": "sess_expired", "transcript": "test"}
        # 10 minutes in the past
        old_headers = _valid_headers(timestamp=time.time() - 600)
        resp = client.post("/api/omi-webhook", json=payload, headers=old_headers)
        assert resp.status_code == 401
        assert "outside allowable 5-minute window" in resp.json()["detail"]

    def test_malformed_payload_rejected_before_persistence(self):
        # Empty payload
        resp = client.post("/api/omi-webhook", json={}, headers=_valid_headers())
        assert resp.status_code == 400
        # No event was registered in inbox
        assert len(default_webhook_inbox.get_event("default_user:None") or {}) == 0

    def test_cross_tenant_event_isolation(self):
        payload = {
            "session_id": "shared_event_id",
            "transcript": "Tenant isolated content.",
        }
        # Delivery for tenant A
        resp_a = client.post("/api/omi-webhook", json=payload, headers=_valid_headers(token_suffix="tenant_a"))
        assert resp_a.status_code == 202
        assert resp_a.json()["status"] == "accepted"

        # Delivery for tenant B with same session_id should NOT be blocked by tenant A
        resp_b = client.post("/api/omi-webhook", json=payload, headers=_valid_headers(token_suffix="tenant_b"))
        assert resp_b.status_code == 202
        assert resp_b.json()["status"] == "accepted"

        # Verify both exist separately in inbox
        assert default_webhook_inbox.get_event("tenant_a:shared_event_id") is not None
        assert default_webhook_inbox.get_event("tenant_b:shared_event_id") is not None

    def test_processing_event_is_claimed_by_only_one_delivery(self):
        is_dup, first = default_webhook_inbox.record_incoming_event(
            event_id="concurrent_event",
            payload_hash="hash-a",
            uid="default_user",
            session_id="concurrent_session",
            payload={"text": "one"},
        )
        assert is_dup is False

        is_dup, second = default_webhook_inbox.record_incoming_event(
            event_id="concurrent_event",
            payload_hash="hash-a",
            uid="default_user",
            session_id="concurrent_session",
            payload={"text": "one"},
        )
        assert is_dup is True
        assert second["attempt_count"] == first["attempt_count"]

    def test_realtime_delivery_is_deduplicated_and_persisted(self):
        payload = {
            "event_id": "realtime_chunk_1",
            "segments": [{"speaker": "A", "text": "Realtime durable chunk", "start": 1}],
        }
        resp = client.post("/omi/realtime?session_id=realtime_session", json=payload, headers=_valid_headers())
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"

        duplicate = client.post("/omi/realtime?session_id=realtime_session", json=payload, headers=_valid_headers())
        assert duplicate.status_code == 200
        assert duplicate.json()["status"] == "duplicate"
        assert default_webhook_inbox.get_event("default_user:realtime_chunk_1")["status"] == "completed"

    def test_serverless_requires_explicit_durable_inbox_path(self, monkeypatch):
        from backend import webhook_inbox

        monkeypatch.setattr(webhook_inbox, "is_testing", lambda: False)
        monkeypatch.setenv("VERCEL", "1")
        monkeypatch.delenv("WEBHOOK_INBOX_DB_PATH", raising=False)
        with pytest.raises(RuntimeError, match="Durable webhook inbox storage"):
            webhook_inbox._get_db_path()
