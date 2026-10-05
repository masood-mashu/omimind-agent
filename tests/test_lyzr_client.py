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
