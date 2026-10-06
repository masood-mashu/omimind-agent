from unittest.mock import Mock, patch

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
