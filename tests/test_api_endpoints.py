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
    return TestClient(app, headers={"x-api-key": "test-secret"})

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

    def test_query_limit_is_bounded(self, client):
        resp = client.post("/api/query", json={"question": "budget", "limit": 21})
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
        assert data["status"] == "accepted"
        assert data["session_id"] == "pytest_omi_session"
        assert data["vectors_queued"] == 2

    def test_omi_webhook_with_flat_transcript(self, client):
        payload = {
            "transcript": "Dev Lead: We must deploy the Redis cache update by tomorrow.\nPM: Approved."
        }
        resp = client.post("/api/omi-webhook", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"

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
            assert "QdrantRetrieval" in agents_streamed
            assert "LyzrManager" in agents_streamed
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

    def test_official_omi_conversation_webhook(self, client):
        payload = {
            "transcript_segments": [
                {"speaker": "Alice", "text": "I will prepare the presentation by Thursday."}
            ],
            "structured": {
                "title": "Project Review",
                "overview": "Discussion on deliverables."
            }
        }
        resp = client.post("/omi/conversation?uid=test_user", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"

    def test_official_omi_realtime_webhook(self, client):
        payload = {
            "segments": [
                {"speaker": "Bob", "text": "Starting deployment now.", "start": 0.0}
            ]
        }
        resp = client.post("/omi/realtime?uid=test_user&session_id=rt_test", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"
        assert resp.json()["indexed_queued"] == 1

    def test_official_ask_endpoint(self, client):
        resp = client.post("/ask", json={"uid": "test_user", "question": "What did Alice prepare?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "context" in data

    def test_forget_endpoint(self, client):
        resp = client.post("/api/forget?session_id=rt_test")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_protected_endpoint_rejects_invalid_key(self):
        unauthenticated = TestClient(app)
        resp = unauthenticated.post("/api/forget?session_id=rt_test")
        assert resp.status_code == 401

    def test_missing_delete_target_is_rejected(self, client):
        resp = client.post("/api/forget")
        assert resp.status_code == 400

    def test_structured_error_handling_and_telemetry(self, client):
        # 404 with structured error schema
        resp = client.post("/api/process", json={"meeting_id": "nonexistent_meeting_xyz"})
        assert resp.status_code == 404
        data = resp.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "HTTP_404"
        assert "Meeting not found" in data["error"]["message"]
        # Verify telemetry headers
        assert "X-Response-Time" in resp.headers
        assert resp.headers["X-Content-Type-Options"] == "nosniff"

    def test_typed_configuration_settings(self):
        from backend.config import Settings
        cfg = Settings(app_name="Test OmiMind", port=9000)
        assert cfg.app_name == "Test OmiMind"
        assert cfg.port == 9000
        assert cfg.collection_name == "omi_ambient_memory"

    def test_health_observability_and_lyzr_status(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "embedding_provider" in data
        assert "vector_dimension" in data
        assert data["vector_dimension"] == 384
        assert "qdrant_persistence_mode" in data
        assert "lyzr_status" in data
        assert "configured" in data["lyzr_status"]
        assert "agent_id_configured" in data["lyzr_status"]
        # Confirm credentials are NOT exposed
        assert "api_key" not in data["lyzr_status"]
        assert "LYZR_API_KEY" not in json.dumps(data)

    def test_health_degraded_returns_503(self, client, monkeypatch):
        from backend.main import orchestrator
        monkeypatch.setattr(
            orchestrator.memory,
            "get_stats",
            lambda: {
                "collection": "omi_ambient_memory",
                "points_count": 0,
                "vector_dimension": 384,
                "embedding_provider": "fastembed",
                "embedding_health": {"status": "degraded", "error": "Model initialization failed"},
                "persistence_mode": "cloud"
            }
        )
        resp = client.get("/health")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["embedding_health"]["status"] == "degraded"

    def test_query_and_ask_return_503_when_degraded(self, client, monkeypatch):
        from backend.main import orchestrator
        monkeypatch.setattr(
            orchestrator.memory,
            "get_stats",
            lambda: {
                "collection": "omi_ambient_memory",
                "points_count": 0,
                "vector_dimension": 384,
                "embedding_provider": "fastembed",
                "embedding_health": {"status": "degraded", "error": "Model initialization failed"},
                "persistence_mode": "cloud"
            }
        )
        # /api/process
        resp_process = client.post("/api/process", json={"meeting_id": "cs_lecture"})
        assert resp_process.status_code == 503
        assert resp_process.json()["error"]["code"] == "EMBEDDING_SERVICE_DEGRADED"

        # /api/query
        resp_query = client.post("/api/query", json={"question": "What is FlashAttention?"})
        assert resp_query.status_code == 503
        assert resp_query.json()["error"]["code"] == "EMBEDDING_SERVICE_DEGRADED"

        # /ask
        resp_ask = client.post("/ask", json={"question": "What is FlashAttention?"})
        assert resp_ask.status_code == 503
        assert resp_ask.json()["error"]["code"] == "EMBEDDING_SERVICE_DEGRADED"

    def test_process_stream_sse_error_event(self, client, monkeypatch):
        from backend.main import orchestrator
        monkeypatch.setattr(
            orchestrator.memory,
            "index_utterance",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Qdrant write failed"))
        )
        with client.stream("POST", "/api/process-stream", json={"meeting_id": "cs_lecture"}) as stream_resp:
            assert stream_resp.status_code == 200
            events = []
            for line in stream_resp.iter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[5:]))
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) >= 1
            assert error_events[0]["agent"] == "PipelineCoordinator"
            assert "Pipeline processing failed" in error_events[0]["message"]

    def test_favicon_endpoints(self, client):
        resp_ico = client.get("/favicon.ico")
        assert resp_ico.status_code == 200
        assert "image" in resp_ico.headers.get("content-type", "")
        assert len(resp_ico.content) > 0

        resp_svg = client.get("/favicon.svg")
        assert resp_svg.status_code == 200
        assert len(resp_svg.content) > 0
