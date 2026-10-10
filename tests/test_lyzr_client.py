from unittest.mock import Mock, patch

import pytest

from agents.lyzr_client import LyzrClient


def test_unconfigured_client_is_explicitly_non_lyzr(monkeypatch):
    monkeypatch.delenv("LYZR_API_KEY", raising=False)
    monkeypatch.delenv("LYZR_AGENT_ID", raising=False)
    monkeypatch.delenv("LYZR_MANAGER_AGENT_ID", raising=False)

    result = LyzrClient().reason(
        uid="user-1",
        question="What happened?",
        context=[],
    )
    assert result.provider == "unconfigured"
    assert result.text == ""
    assert result.error


def test_configured_client_returns_cloud_result():
    response = Mock()
    response.json.return_value = {"response": "Sarah will review the contract."}
    response.raise_for_status.return_value = None
    with patch("httpx.post", return_value=response) as post:
        result = LyzrClient(api_key="secret", agent_id="manager-1").reason(
            uid="user-1",
            question="What is the action?",
            context=[{"speaker": "Sarah", "timestamp_str": "01:20", "text": "I will review it."}],
        )
    assert result.provider == "lyzr_studio_cloud"
    assert result.text.startswith("Sarah")
    assert post.call_args.kwargs["json"]["agent_id"] == "manager-1"


def test_manager_id_precedence(monkeypatch):
    monkeypatch.setenv("LYZR_API_KEY", "test-key")
    monkeypatch.setenv("LYZR_AGENT_ID", "fallback-worker-id")
    monkeypatch.setenv("LYZR_MANAGER_AGENT_ID", "6ac5795151dce5f00e746950")

    client = LyzrClient()
    assert client.agent_id == "6ac5795151dce5f00e746950"


def test_manager_timeout_configuration(monkeypatch):
    monkeypatch.setenv("LYZR_API_KEY", "test-key")
    monkeypatch.setenv("LYZR_MANAGER_AGENT_ID", "6ac5795151dce5f00e746950")
    monkeypatch.delenv("LYZR_TIMEOUT_SECONDS", raising=False)

    client = LyzrClient()
    assert client.timeout == 45.0

    client_custom = LyzrClient(timeout=60.0)
    assert client_custom.timeout == 60.0


def test_no_direct_worker_calls():
    worker_ids = {
        "6ac577cccf263d0b068d001a",  # Meeting Analyst
        "6ac578bf4b079480ed4ea5a5",  # Action Extractor
        "6ac2646b367124ed07f49bdd",  # Recall Agent
    }
    manager_id = "6ac5795151dce5f00e746950"

    response = Mock()
    response.json.return_value = {"response": "Delegated multi-agent synthesis"}
    response.raise_for_status.return_value = None

    with patch("httpx.post", return_value=response) as post:
        client = LyzrClient(api_key="secret", agent_id=manager_id)
        result = client.reason(uid="u1", question="Summarize", context=[])

    assert result.provider == "lyzr_studio_cloud"
    called_agent_id = post.call_args.kwargs["json"]["agent_id"]
    assert called_agent_id == manager_id
    assert called_agent_id not in worker_ids


def test_client_error_4xx_does_not_retry():
    import httpx

    req = httpx.Request("POST", "https://api.lyzr.ai")
    resp_400 = httpx.Response(400, request=req)

    with patch("httpx.post", side_effect=httpx.HTTPStatusError("Bad Request", request=req, response=resp_400)) as mock_post:
        client = LyzrClient(api_key="secret-key", agent_id="manager-1", max_retries=2)
        result = client.reason(uid="u1", question="Summarize", context=[])

    assert result.provider == "lyzr_error"
    assert "HTTP 400" in result.error
    # 4xx error breaks immediately without retries
    assert mock_post.call_count == 1


def test_server_error_5xx_retries_and_recovers():
    import httpx

    req = httpx.Request("POST", "https://api.lyzr.ai")
    resp_503 = httpx.Response(503, request=req)
    good_resp = Mock()
    good_resp.json.return_value = {"response": "Recovered response after 503"}
    good_resp.raise_for_status.return_value = None

    # First attempt fails with 503, second attempt succeeds
    with patch("httpx.post", side_effect=[httpx.HTTPStatusError("Service Unavailable", request=req, response=resp_503), good_resp]) as mock_post:
        with patch("time.sleep"):  # Avoid sleep delays
            client = LyzrClient(api_key="secret-key", agent_id="manager-1", max_retries=2)
            result = client.reason(uid="u1", question="Summarize", context=[])

    assert result.provider == "lyzr_studio_cloud"
    assert result.text == "Recovered response after 503"
    assert mock_post.call_count == 2


def test_timeout_classified_cleanly_without_secrets():
    import httpx

    with patch("httpx.post", side_effect=httpx.TimeoutException("Connection to api timed out with key secret_xyz")):
        client = LyzrClient(api_key="secret_xyz", agent_id="manager-1", timeout=5.0)
        result = client.reason(uid="u1", question="Summarize", context=[])

    assert result.provider == "lyzr_error"
    assert "timed out" in result.error
    assert "secret_xyz" not in result.error


def test_malformed_empty_response_handled():
    bad_resp = Mock()
    bad_resp.json.return_value = {"response": "   "}
    bad_resp.raise_for_status.return_value = None

    with patch("httpx.post", return_value=bad_resp):
        client = LyzrClient(api_key="secret", agent_id="manager-1")
        result = client.reason(uid="u1", question="Summarize", context=[])

    assert result.provider == "lyzr_error"
    assert "empty response" in result.error


@pytest.mark.asyncio
async def test_async_areason_success():
    good_resp = Mock()
    good_resp.json.return_value = {"response": "Async reasoning response"}
    good_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", return_value=good_resp):
        client = LyzrClient(api_key="secret", agent_id="manager-1")
        result = await client.areason(uid="u1", question="Summarize", context=[])

    assert result.provider == "lyzr_studio_cloud"
    assert result.text == "Async reasoning response"

