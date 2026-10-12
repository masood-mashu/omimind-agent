"""Focused regression coverage for the multi-user release contract."""
from __future__ import annotations

import time

import pytest
from starlette.requests import Request

from agents.lyzr_swarm import LyzrAgentRegistry
from backend.auth import _verify_webhook_timestamp, check_no_query_secrets
from backend.tenant_store import TenantStore
from backend.webhook_inbox import WebhookInbox


def test_tenant_store_pairing_rotation_and_owner_isolation(tmp_path):
    store = TenantStore(sqlite_path=str(tmp_path / "tenant.db"))
    pair = store.start_pairing("owner-a")
    assert store.list_connections("owner-b") == []
    connected = store.complete_pairing("owner-a", pair["pairing_code"], "omi-a")
    assert connected["status"] == "active"
    rotated = store.rotate_connection("owner-a", connected["id"])
    assert store.resolve_connection(pair["connection_token"]) is None
    assert store.resolve_connection(rotated["connection_token"])["owner_id"] == "owner-a"


def test_registry_keeps_agent_ids_server_side(monkeypatch):
    from backend.config import settings
    monkeypatch.setattr(settings, "lyzr_manager_agent_id", "manager")
    monkeypatch.setattr(settings, "lyzr_memory_recall_agent_id", "recall")
    registry = LyzrAgentRegistry()
    assert registry.get("manager").agent_id == "manager"
    assert registry.get("memory_recall").agent_id == "recall"


def test_webhook_rejects_query_credentials_and_stale_timestamp(monkeypatch):
    request = Request({"type": "http", "method": "POST", "path": "/omi", "query_string": b"token=bad", "headers": []})
    with pytest.raises(Exception) as query_error:
        check_no_query_secrets(request)
    assert query_error.value.status_code == 401
    monkeypatch.setattr("backend.auth.is_testing", lambda: False)
    monkeypatch.setattr("backend.auth.allow_test_tenant_overrides", lambda: False)
    stale = Request({"type": "http", "method": "POST", "path": "/omi", "query_string": b"", "headers": [(b"x-omi-timestamp", str(time.time() - 301).encode())]})
    with pytest.raises(Exception) as timestamp_error:
        _verify_webhook_timestamp(stale)
    assert timestamp_error.value.status_code == 401


def test_workspace_outputs_survive_store_restart(tmp_path):
    path = str(tmp_path / "tenant.db")
    store = TenantStore(sqlite_path=path)
    run_id = store.create_run("owner-a", "session-a", "Planning")
    store.complete_run(
        "owner-a",
        run_id,
        {
            "session_id": "session-a",
            "title": "Planning",
            "summary": {"executive_summary": "Ship the release."},
            "transcript_lines": [{"speaker": "A", "text": "Ship the release."}],
            "action_items": [{"title": "Ship release", "assignee": "A", "priority": "High"}],
        },
        provider="deterministic_fallback",
    )
    restarted = TenantStore(sqlite_path=path)
    actions = restarted.list_actions("owner-a")
    assert len(actions) == 1
    assert actions[0]["title"] == "Ship release"
    assert restarted.list_actions("owner-b") == []


def test_webhook_owner_cleanup_is_scoped(tmp_path):
    inbox = WebhookInbox(str(tmp_path / "inbox.db"))
    inbox.record_incoming_event("a", "hash-a", "owner-a", "session-a", {"text": "a"})
    inbox.record_incoming_event("b", "hash-b", "owner-b", "session-b", {"text": "b"})
    assert inbox.delete_owner("owner-a") == 1
    assert inbox.get_event("owner-a:a") is None
    assert inbox.get_event("owner-b:b") is not None
