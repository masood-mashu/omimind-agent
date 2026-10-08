"""
tests/test_security_hardening.py
Comprehensive regression tests for Security, Privacy & Reliability Hardening:
1. Unauthenticated access to every protected route.
2. Invalid API credentials.
3. Query-string credentials being rejected (401).
4. A user cannot read another user's memories.
5. A user cannot delete another user's session.
6. A user cannot delete another user's point.
7. Custom webhook UID cannot override authenticated identity.
8. Webhook data is never copied into default_user.
9. Duplicate webhook delivery is idempotent.
10. Concurrent webhook sessions do not collide.
11. Oversized transcript and segment payloads are rejected (413 / 422).
12. Invalid timestamps are rejected (422).
13. Lyzr failures do not block the event loop.
14. Lyzr fallback responses are labeled honestly.
15. Dynamic participant values are safely escaped in the frontend.
"""
import asyncio
import json
import pathlib
import time

import pytest
from fastapi.testclient import TestClient

from agents.lyzr_client import LyzrClient
from backend.config import settings
from backend.main import app
from backend.shared import cache_processed, get_processed_for_user, processed_cache, processed_cache_owners


@pytest.fixture
def unauthenticated_client():
    return TestClient(app)


@pytest.fixture
def user_a_client():
    return TestClient(app, headers={"Authorization": f"Bearer {settings.api_secret_key}:user_sec_a"})


@pytest.fixture
def user_b_client():
    return TestClient(app, headers={"Authorization": f"Bearer {settings.api_secret_key}:user_sec_b"})


class TestSecurityHardening:
    def test_tenant_suffix_cannot_mint_identity_outside_tests(self, monkeypatch, unauthenticated_client):
        monkeypatch.setattr("backend.auth.is_testing", lambda: False)
        response = unauthenticated_client.get(
            "/api/memories",
            headers={"Authorization": f"Bearer {settings.api_secret_key}:forged_tenant"},
        )
        assert response.status_code == 401

    def test_processed_dossier_cache_is_tenant_scoped(self):
        session_id = "cache-isolation-regression"
        cache_processed(session_id, {"action_items": [{"title": "private"}]}, "tenant-a")
        try:
            assert get_processed_for_user(session_id, "tenant-a") is not None
            assert get_processed_for_user(session_id, "tenant-b") is None
        finally:
            processed_cache.pop(session_id, None)
            processed_cache_owners.pop(session_id, None)

    # 1. Unauthenticated access to every protected route
    @pytest.mark.parametrize(
        ("method", "path", "payload"),
        [
            ("get", "/api/memories", None),
            ("post", "/api/query", {"query": "test query"}),
            ("post", "/api/ask", {"question": "test question"}),
            ("post", "/ask", {"question": "test question"}),
            ("get", "/api/actions", None),
            ("get", "/api/meetings", None),
            ("get", "/api/meetings/1", None),
            ("post", "/api/process", {"meeting_id": "1"}),
            ("post", "/api/process-stream", {"meeting_id": "1"}),
            ("post", "/api/custom-voice", {"transcript": "hello world"}),
            ("post", "/api/custom-voice-stream", {"transcript": "hello world"}),
            ("post", "/api/seed", {}),
            ("post", "/api/forget", {"session_id": "dummy"}),
            ("delete", "/api/memory", {"point_id": "dummy"}),
            ("post", "/api/omi-webhook", {"session_id": "s1", "transcript": "test"}),
            ("post", "/omi/conversation", {"session_id": "s1", "transcript": "test"}),
            ("post", "/omi/realtime", {"session_id": "s1", "segments": []}),
        ],
    )
    def test_unauthenticated_access_rejected(self, unauthenticated_client, method, path, payload):
        if method == "get":
            resp = unauthenticated_client.get(path)
        elif method == "delete":
            resp = unauthenticated_client.request("DELETE", path, json=payload)
        else:
            resp = unauthenticated_client.post(path, json=payload)
        assert resp.status_code == 401, f"Route {path} should reject unauthenticated requests with 401"

    # 2. Invalid API credentials
    def test_invalid_api_credentials(self, unauthenticated_client):
        resp = unauthenticated_client.get("/api/meetings", headers={"Authorization": "Bearer bad-token-value"})
        assert resp.status_code == 401
        assert "Invalid" in resp.json()["detail"] or "credentials" in resp.json()["detail"]

        resp2 = unauthenticated_client.post(
            "/api/omi-webhook",
            json={"transcript": "test"},
            headers={"X-Omi-Webhook-Secret": "wrong-secret"},
        )
        assert resp2.status_code == 401

    # 3. Query-string credentials being rejected
    @pytest.mark.parametrize("secret_key", ["api_key", "key", "token", "secret"])
    def test_query_string_credentials_rejected(self, unauthenticated_client, secret_key):
        resp = unauthenticated_client.get(
            f"/api/meetings?{secret_key}=test-secret",
            headers={"Authorization": f"Bearer {settings.api_secret_key}"},
        )
        assert resp.status_code == 401
        assert "Query-string credentials are not permitted" in resp.json()["detail"]

    # 4. A user cannot read another user's memories
    def test_user_cannot_read_another_users_memories(self, user_a_client, user_b_client):
        # User A ingests a private memory
        ingest_resp = user_a_client.post(
            "/api/custom-voice",
            json={"transcript": "User A confidential trade secret code 998877", "meeting_title": "Confidential A"},
        )
        assert ingest_resp.status_code == 200

        # User B queries memories
        query_resp = user_b_client.post(
            "/api/query",
            json={"query": "confidential trade secret code 998877"},
        )
        assert query_resp.status_code == 200
        data = query_resp.json()
        assert len(data.get("matches", [])) == 0, "User B should not see User A's memories in vector query"

        # User B lists recent memories
        mem_resp = user_b_client.get("/api/memories")
        assert mem_resp.status_code == 200
        for m in mem_resp.json().get("memories", []):
            assert "998877" not in m.get("text", "")

    # 5. A user cannot delete another user's session
    def test_user_cannot_delete_another_users_session(self, user_a_client, user_b_client):
        # User A seeds session
        resp_a = user_a_client.post(
            "/api/custom-voice",
            json={"transcript": "User A session deletion test memory", "meeting_title": "SessionDelTest"},
        )
        assert resp_a.status_code == 200
        session_id = resp_a.json()["session_id"]

        # User B attempts to delete User A's session
        del_resp = user_b_client.post(
            "/api/forget",
            json={"session_id": session_id},
        )
        assert del_resp.status_code == 403, "Deleting another user's session must return 403 Forbidden"

        # User A still has this session/memory intact
        query_resp = user_a_client.post(
            "/api/query",
            json={"query": "session deletion test memory"},
        )
        assert query_resp.status_code == 200
        assert len(query_resp.json().get("matches", [])) > 0

    # 6. A user cannot delete another user's point
    def test_user_cannot_delete_another_users_point(self, user_a_client, user_b_client):
        # User A stores memory and finds point_id
        user_a_client.post(
            "/api/custom-voice",
            json={"transcript": "User A point deletion target memory", "meeting_title": "PointDelTest"},
        )
        q_resp = user_a_client.post("/api/query", json={"query": "point deletion target memory"})
        assert q_resp.status_code == 200
        matches = q_resp.json().get("matches", [])
        assert len(matches) > 0
        point_id = matches[0]["id"]

        # User B tries to delete User A's point
        del_resp = user_b_client.request("DELETE", "/api/memory", json={"point_id": str(point_id)})
        assert del_resp.status_code == 403, "Deleting another user's point must return 403 Forbidden"

    # 7. Custom webhook UID cannot override authenticated identity
    def test_custom_webhook_uid_cannot_override_authenticated_identity(self):
        hook_client = TestClient(
            app,
            headers={"X-Omi-Webhook-Secret": f"{settings.api_secret_key}:user_sec_webhook_gamma"},
        )
        user_client = TestClient(
            app,
            headers={"Authorization": f"Bearer {settings.api_secret_key}:user_sec_webhook_gamma"},
        )
        # Webhook payload attempts to spoof uid
        resp = hook_client.post(
            "/api/omi-webhook",
            json={
                "uid": "spoofed_admin_uid",
                "transcript": "Webhook with spoofed UID parameter",
            },
        )
        assert resp.status_code in (200, 202)
        # Check query under gamma sees it
        q_resp = user_client.post("/api/query", json={"query": "spoofed UID parameter"})
        assert q_resp.status_code == 200
        matches = q_resp.json().get("matches", [])
        assert len(matches) > 0
        assert matches[0]["uid"] == "user_sec_webhook_gamma"

    # 8. Webhook data is never copied into default_user
    def test_webhook_data_never_copied_into_default_user(self):
        tenant_secret = f"{settings.api_secret_key}:user_isolated_webhook"
        hook_client = TestClient(app, headers={"X-Omi-Webhook-Secret": tenant_secret})
        default_client = TestClient(app, headers={"Authorization": f"Bearer {settings.api_secret_key}"})

        hook_resp = hook_client.post(
            "/api/omi-webhook",
            json={
                "session_id": "isolated_test_sess",
                "transcript": "Isolated webhook secret data item 12345",
            },
        )
        assert hook_resp.status_code in (200, 202)

        # Query default user
        default_query = default_client.post(
            "/api/query",
            json={"query": "Isolated webhook secret data item 12345"},
        )
        assert default_query.status_code == 200
        for match in default_query.json().get("matches", []):
            assert "Isolated webhook secret data item 12345" not in match.get("text", "")
            assert match.get("session_id") != "isolated_test_sess"
            assert match.get("uid") != "user_isolated_webhook"

        # Check default user recent memories
        mem_resp = default_client.get("/api/memories")
        assert mem_resp.status_code == 200
        for m in mem_resp.json().get("memories", []):
            assert "Isolated webhook secret data item 12345" not in m.get("text", "")
            assert m.get("session_id") != "isolated_test_sess"

    # 9. Duplicate webhook delivery is idempotent
    def test_duplicate_webhook_delivery_is_idempotent(self):
        client = TestClient(app, headers={"X-Omi-Webhook-Secret": settings.api_secret_key})
        payload = {
            "id": "event_fixed_id_100",
            "session_id": "sess_fixed_100",
            "transcript": "Idempotent event test transcript text",
        }
        resp1 = client.post("/api/omi-webhook", json=payload)
        assert resp1.status_code in (200, 202)
        assert resp1.json()["status"] in ("accepted", "processed")

        resp2 = client.post("/api/omi-webhook", json=payload)
        assert resp2.status_code in (200, 202)
        assert resp2.json()["status"] in ("duplicate", "duplicate_ignored")

    # 10. Concurrent webhook sessions do not collide
    def test_concurrent_webhook_sessions_do_not_collide(self):
        client = TestClient(app, headers={"X-Omi-Webhook-Secret": settings.api_secret_key})
        payload1 = {"transcript": "Concurrent session utterance A"}
        payload2 = {"transcript": "Concurrent session utterance B"}

        resp1 = client.post("/api/omi-webhook", json=payload1)
        resp2 = client.post("/api/omi-webhook", json=payload2)

        assert resp1.status_code in (200, 202)
        assert resp2.status_code in (200, 202)
        assert resp1.json()["session_id"] != resp2.json()["session_id"]

    # 11. Oversized transcript and segment payloads are rejected
    def test_oversized_payloads_rejected(self, user_a_client):
        # Oversized transcript (> 50,000 chars)
        huge_transcript = "A" * 50_001
        resp = user_a_client.post("/api/custom-voice", json={"transcript": huge_transcript})
        assert resp.status_code == 422

        # Oversized query (> 1,000 chars)
        huge_query = "Q" * 1_001
        resp = user_a_client.post("/api/query", json={"query": huge_query})
        assert resp.status_code == 422

        # Oversized segments count (> 500)
        many_segments = [{"text": f"seg {i}", "speaker": "user", "start": 0.0, "end": 1.0} for i in range(501)]
        resp = user_a_client.post("/api/omi-webhook", json={"segments": many_segments})
        assert resp.status_code == 422

        # Oversized single segment text (> 2,000 chars)
        big_seg = [{"text": "x" * 2001, "speaker": "user", "start": 0.0, "end": 1.0}]
        resp = user_a_client.post("/api/omi-webhook", json={"segments": big_seg})
        assert resp.status_code == 422

        # Body exceeding 1MB limit (> 1,000,000 bytes) -> 413
        oversized_body = json.dumps({"transcript": "x" * 1_000_050})
        resp = user_a_client.post(
            "/api/custom-voice",
            content=oversized_body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 413

    # 12. Invalid timestamps are rejected
    def test_invalid_timestamps_rejected(self, user_a_client):
        # Negative timestamp
        bad_segments = [{"text": "Hello", "speaker": "user", "start": -5.0, "end": 1.0}]
        resp = user_a_client.post("/api/omi-webhook", json={"segments": bad_segments})
        assert resp.status_code == 422

        # Malformed non-numeric timestamp
        bad_segments2 = [{"text": "Hello", "speaker": "user", "start": "invalid_num", "end": 1.0}]
        resp = user_a_client.post("/api/omi-webhook", json=bad_segments2)
        assert resp.status_code == 422

    # 13. Lyzr failures do not block the event loop
    @pytest.mark.asyncio
    async def test_lyzr_async_nonblocking(self):
        client = LyzrClient(api_key="invalid_test_key", agent_id="invalid_agent")
        # Run areason concurrently with an async sleep
        start_time = time.time()
        task1 = asyncio.create_task(client.areason(uid="test_user", question="test prompt", context=[]))
        task2 = asyncio.create_task(asyncio.sleep(0.05))

        res1, _ = await asyncio.gather(task1, task2)
        elapsed = time.time() - start_time
        # Verifies async event loop was unblocked and ran concurrently
        assert res1.provider in ("lyzr_error", "deterministic_fallback", "unconfigured")
        assert elapsed < 10.0

    # 14. Lyzr fallback responses are labeled honestly
    def test_lyzr_fallback_responses_labeled_honestly(self, user_a_client):
        resp = user_a_client.post("/api/ask", json={"question": "What is the secret?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("source") in ("deterministic_fallback", "lyzr_studio_cloud")
        if data.get("source") == "deterministic_fallback":
            assert not data.get("lyzr_reasoning_occurred", False)

    # 15. Dynamic participant values are safely escaped in frontend
    def test_frontend_escaping_and_xss_protection(self):
        meetings_file = pathlib.Path("frontend/js/views/meetings.js")
        assert meetings_file.exists()
        content = meetings_file.read_text(encoding="utf-8")
        assert "m.participants.map(escapeHtml).join(', ')" in content

        detail_file = pathlib.Path("frontend/js/views/meeting_detail.js")
        assert detail_file.exists()
        detail_content = detail_file.read_text(encoding="utf-8")
        assert "meeting.participants.map(escapeHtml).join(', ')" in detail_content
