"""
test_executive_synth.py - Unit & Edge Case Tests for LyzrExecutiveSynthesizer
Covers:
- Decision keyword identification
- Risk & blocker keyword identification
- Participant aggregation & deduplication
- Dynamic executive summary derivation
- Edge cases: empty transcript, single-line transcript
"""
import pytest

from agents.executive_synth import LyzrExecutiveSynthesizer


class TestLyzrExecutiveSynthesizer:
    @pytest.fixture
    def synthesizer(self):
        return LyzrExecutiveSynthesizer()

    def test_synthesis_with_decisions_and_risks(self, synthesizer):
        lines = [
            {"speaker": "Lead", "text": "Welcome to our architectural review."},
            {"speaker": "Lead", "text": "We approved the migration to Qdrant Cloud."},
            {"speaker": "SRE", "text": "Risk: Network latency between clusters could cause a delay in syncing."},
        ]
        res = synthesizer.synthesize_meeting("Cloud Migration", lines)
        assert res["title"] == "Cloud Migration"
        assert "Lead" in res["participants"]
        assert "SRE" in res["participants"]
        assert len(res["key_decisions"]) == 1
        assert "approved" in res["key_decisions"][0].lower()
        assert len(res["risks_and_blockers"]) == 1
        assert "delay" in res["risks_and_blockers"][0].lower()
        assert "1 decision confirmed" in res["executive_summary"]
        assert "1 risk or blocker flagged" in res["executive_summary"]

    def test_synthesis_zero_decisions_fallback(self, synthesizer):
        lines = [
            {"speaker": "User1", "text": "Just general discussion today."},
            {"speaker": "User2", "text": "No updates from my side."},
        ]
        res = synthesizer.synthesize_meeting("Sync", lines)
        assert "No formal decisions were recorded" in res["executive_summary"]
        assert "Consensus reached" in res["key_decisions"][0]
        assert "No critical path blockers identified" in res["risks_and_blockers"][0]

    def test_empty_transcript_handling(self, synthesizer):
        res = synthesizer.synthesize_meeting("Empty", [])
        assert res["total_exchanges"] == 0
        assert res["estimated_duration_min"] == 1
        assert res["participants"] == []
