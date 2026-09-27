"""
test_api_endpoints.py - API Integration, Route Verification & Failure Mode Tests
Covers:
- GET /health (service version, qdrant stats)
- GET /api/meetings (pre-set demo scenarios)
- POST /api/query (semantic vector search, validation)
- POST /api/omi-webhook (native Omi payloads, flat transcripts)
- POST /api/process (preset meeting processing, 404 on invalid ID)
- POST /api/process-stream & POST /api/custom-voice-stream (SSE event streaming)
- POST /api/seed (pre-population)
"""
import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)

class TestApiEndpoints:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "omimind-agent"
        assert "version" in data
        assert "qdrant_stats" in data
        assert data["qdrant_stats"]["collection"] == "omi_ambient_memory"

    def test_list_demo_meetings(self, client):
        resp = client.get("/api/meetings")
        assert resp.status_code == 200
        data = resp.json()
        assert "meetings" in data
        assert len(data["meetings"]) >= 3
        meeting_ids = [m["id"] for m in data["meetings"]]
        assert "q4_strategy" in meeting_ids
        assert "sre_postmortem" in meeting_ids
        assert "cs_lecture" in meeting_ids

    def test_query_semantic_memory(self, client):
        payload = {"question": "How much compute budget was allocated?", "limit": 2}
        resp = client.post("/api/query", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "matches" in data
        assert "relevance_top" in data
        assert isinstance(data["matches"], list)

    def test_query_validation_error(self, client):
        # Missing required 'question' field should return 422
        resp = client.post("/api/query", json={})
        assert resp.status_code == 422

    def test_process_preset_meeting_success(self, client):
        resp = client.post("/api/process", json={"meeting_id": "q4_strategy"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "q4_strategy"
        assert "summary" in data
        assert "action_items" in data
        assert "email_draft" in data
        assert "jira_tickets" in data

    def test_process_preset_meeting_not_found(self, client):
        resp = client.post("/api/process", json={"meeting_id": "invalid_id_999"})
        assert resp.status_code == 404
        assert "Meeting not found" in resp.json()["detail"]

    def test_omi_webhook_with_segments(self, client):
        payload = {
            "session_id": "pytest_omi_session",
            "segments": [
                {"speaker": "Lead", "text": "I will review the security report by Friday.", "start": 0.0},
                {"speaker": "Admin", "text": "Approved. Make this P0 priority.", "start": 5.0}
            ]
        }
        resp = client.post("/api/omi-webhook", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "indexed"
        assert data["session_id"] == "pytest_omi_session"

    def test_omi_webhook_with_flat_transcript(self, client):
        payload = {
            "transcript": "Dev Lead: We must deploy the Redis cache update by tomorrow.\nPM: Approved."
        }
        resp = client.post("/api/omi-webhook", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "indexed"

    def test_seed_endpoint(self, client):
        resp = client.post("/api/seed")
        assert resp.status_code == 200
        data = resp.json()
        assert "seeded" in data
        assert "qdrant_stats" in data

    def test_process_stream_sse(self, client):
        with client.stream("POST", "/api/process-stream", json={"meeting_id": "cs_lecture"}) as stream_resp:
            assert stream_resp.status_code == 200
            assert "text/event-stream" in stream_resp.headers["content-type"]
            events = []
            for line in stream_resp.iter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[5:]))
            assert len(events) > 0
            # Confirm agents are streamed
            agents_streamed = {e.get("agent") for e in events if e.get("agent")}
            assert "MemoryAgent" in agents_streamed
            assert "TaskDispatcher" in agents_streamed

    def test_custom_voice_stream_sse(self, client):
        payload = {
            "title": "Adhoc Sync",
            "speaker": "Engineer",
            "transcript": "Engineer: I will migrate the microservices by Monday."
        }
        with client.stream("POST", "/api/custom-voice-stream", json=payload) as stream_resp:
            assert stream_resp.status_code == 200
            assert "text/event-stream" in stream_resp.headers["content-type"]
