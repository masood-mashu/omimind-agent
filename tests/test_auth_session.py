"""
tests/test_auth_session.py
Unit and integration tests for Phase 2: Session cookie authentication flow.
Tests login success, login failure, missing session, protected endpoint access,
logout, SSE authentication with cookies, and server-derived tenant identity.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.auth import COOKIE_NAME, verify_session_token
from backend.config import settings
from backend.main import app

client = TestClient(app)
VALID_SECRET = "test_valid_api_secret_key_123456"


@pytest.fixture(autouse=True)
def configure_secret(monkeypatch):
    monkeypatch.setattr(settings, "api_secret_key", VALID_SECRET)
    monkeypatch.setattr(settings, "default_user_id", "default_user")


class TestSessionAuthFlow:
    def test_login_success_sets_httponly_cookie(self):
        res = client.post("/api/auth/login", json={"secret_key": VALID_SECRET})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["uid"] == "default_user"
        # Verify cookie is set
        assert COOKIE_NAME in res.cookies
        cookie_val = res.cookies[COOKIE_NAME]
        verified_uid = verify_session_token(cookie_val, VALID_SECRET)
        assert verified_uid == "default_user"

    def test_login_failure_with_wrong_secret(self):
        res = client.post("/api/auth/login", json={"secret_key": "wrong_secret"})
        assert res.status_code == 401
        assert COOKIE_NAME not in res.cookies

    def test_login_when_secret_not_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "api_secret_key", None)
        res = client.post("/api/auth/login", json={"secret_key": VALID_SECRET})
        assert res.status_code == 503

    def test_protected_endpoint_rejected_without_session_or_headers(self):
        # Client without cookies or Authorization header
        fresh_client = TestClient(app)
        res = fresh_client.get("/api/meetings")
        assert res.status_code == 401
        assert "Missing authentication credentials" in res.json().get("detail", "")

    def test_protected_endpoints_accessible_with_session_cookie(self):
        session_client = TestClient(app)
        # 1. Login
        login_res = session_client.post("/api/auth/login", json={"secret_key": VALID_SECRET})
        assert login_res.status_code == 200

        # 2. Access /api/meetings
        res = session_client.get("/api/meetings")
        assert res.status_code == 200
        assert "meetings" in res.json()

        # 3. Access /api/actions
        res_actions = session_client.get("/api/actions")
        assert res_actions.status_code == 200

        # 4. Access /api/memories
        res_mem = session_client.get("/api/memories")
        assert res_mem.status_code == 200

    def test_auth_status_endpoint(self):
        fresh_client = TestClient(app)
        # Unauthenticated
        status_unauth = fresh_client.get("/api/auth/status")
        assert status_unauth.status_code == 200
        assert status_unauth.json()["authenticated"] is False

        # Authenticate
        login_res = fresh_client.post("/api/auth/login", json={"secret_key": VALID_SECRET})
        assert login_res.status_code == 200

        # Authenticated
        status_auth = fresh_client.get("/api/auth/status")
        assert status_auth.status_code == 200
        assert status_auth.json()["authenticated"] is True
        assert status_auth.json()["uid"] == "default_user"
        assert status_auth.json()["auth_type"] == "session_cookie"

    def test_logout_clears_cookie_and_revokes_access(self):
        session_client = TestClient(app)
        session_client.post("/api/auth/login", json={"secret_key": VALID_SECRET})

        # Can access
        assert session_client.get("/api/meetings").status_code == 200

        # Logout
        logout_res = session_client.post("/api/auth/logout")
        assert logout_res.status_code == 200

        # Cannot access anymore
        assert session_client.get("/api/meetings").status_code == 401

    def test_tenant_identity_remains_server_derived_despite_custom_param(self):
        session_client = TestClient(app)
        session_client.post("/api/auth/login", json={"secret_key": VALID_SECRET})

        # Caller provides arbitrary uid in query parameter
        res = session_client.get("/api/memories?uid=attacker_tenant")
        assert res.status_code == 200
        # The authenticated identity used is server-derived default_user, not attacker_tenant
        status = session_client.get("/api/auth/status").json()
        assert status["uid"] == "default_user"

    def test_sse_endpoint_authenticates_with_session_cookie(self):
        session_client = TestClient(app)
        session_client.post("/api/auth/login", json={"secret_key": VALID_SECRET})

        # Request SSE endpoint with session cookie
        res = session_client.post(
            "/api/process-stream",
            json={"meeting_id": "q4_strategy"},
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers.get("content-type", "")

    def test_forged_session_cookie_rejected(self):
        session_client = TestClient(app)
        # Mint invalid cookie
        session_client.cookies.set(COOKIE_NAME, "default_user:12345678:invalid_signature")
        res = session_client.get("/api/meetings")
        assert res.status_code == 401
        assert "Invalid or expired session cookie" in res.json().get("detail", "")
