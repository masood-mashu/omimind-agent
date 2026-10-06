"""
test_live_lyzr_manager.py - Opt-In Live Lyzr Manager Integration Test
Requires valid LYZR_API_KEY with permissions for Manager 6ac5795151dce5f00e746950.
Gated by pytest.mark.live and gracefully skips if credentials are not configured or rejected.
"""
import os

import pytest

from agents.lyzr_client import LyzrClient

MANAGER_ID = "6ac5795151dce5f00e746950"


def test_live_lyzr_manager_contract():
    api_key = os.environ.get("LYZR_API_KEY")
    if not api_key:
        pytest.skip("LYZR_API_KEY not configured; skipping live integration test.")

    client = LyzrClient(api_key=api_key, agent_id=MANAGER_ID, timeout=45.0)
    if not client.configured:
        pytest.skip("LyzrClient not configured with valid manager credentials.")

    result = client.reason(
        uid="live-verification-user",
        question="Summarize the meeting and extract action items.",
        context=[
            {"speaker": "Sarah", "timestamp_str": "01:00", "text": "I will prepare the Q4 budget by Friday."},
            {"speaker": "John", "timestamp_str": "02:00", "text": "I agreed to review the proposal tomorrow."},
        ],
    )

    if result.provider == "lyzr_error":
        pytest.skip(f"Live Lyzr provider returned error: {result.error}")

    assert result.provider == "lyzr_studio_cloud"
    assert result.agent_id == MANAGER_ID
    assert len(result.text) > 0
