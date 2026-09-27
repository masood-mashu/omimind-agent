"""
test_action_extractor.py - Unit & Edge Case Tests for LyzrActionExtractor
Covers:
- Commitment trigger pattern recognition
- Deadline parsing (relative, day names, calendar dates)
- Priority inference (Critical, High, Medium, Low)
- Edge cases: empty lines, missing keys, short sentences, noise
"""
import pytest

from agents.action_extractor import LyzrActionExtractor


class TestLyzrActionExtractor:
    @pytest.fixture
    def extractor(self):
        return LyzrActionExtractor()

    def test_extract_i_will_commitment(self, extractor):
        items = extractor.extract_from_utterance(
            speaker="Alex (SRE)",
            text="I will migrate the database cluster to AWS RDS by Friday.",
            timestamp_str="04:15"
        )
        assert len(items) == 1
        item = items[0]
        assert item["assignee"] == "Alex (SRE)"
        assert "migrate the database" in item["title"].lower()
        assert item["due_date"] == "By Friday"
        assert item["priority"] == "Medium"
        assert item["status"] == "OPEN"

    def test_priority_critical_p0(self, extractor):
        items = extractor.extract_from_utterance(
            speaker="Chloe",
            text="This is a P0 critical blocker! I will patch the authentication vulnerability immediately.",
            timestamp_str="01:30"
        )
        assert len(items) == 1
        assert items[0]["priority"] == "Critical"

    def test_priority_high_and_low(self, extractor):
        items_high = extractor.extract_from_utterance(
            speaker="Dev1",
            text="We need to optimize the query execution time, this is an important task.",
            timestamp_str="02:00"
        )
        assert len(items_high) == 1
        assert items_high[0]["priority"] == "High"

        items_low = extractor.extract_from_utterance(
            speaker="Dev2",
            text="Please ensure to clean up the legacy CSS files when you have time.",
            timestamp_str="03:00"
        )
        assert len(items_low) == 1
        assert items_low[0]["priority"] == "Low"

    def test_calendar_date_deadline_detection(self, extractor):
        dates = [
            ("I will finalize the security audit by October 25th.", "By October 25Th"),
            ("We need to deploy the payment gateway by November 2nd.", "By November 2Nd"),
            ("Let's make sure to renew the domain by tomorrow.", "By Tomorrow"),
            ("Action item: conduct penetration test within 5 days.", "Within 5 Days"),
        ]
        for text, expected_deadline in dates:
            items = extractor.extract_from_utterance("Tester", text, "00:00")
            assert len(items) == 1
            assert items[0]["due_date"].lower() == expected_deadline.lower()

    def test_short_actions_ignored(self, extractor):
        # Action text <= 8 chars should be ignored to avoid false positives
        items = extractor.extract_from_utterance("Bob", "I will do it.", "00:10")
        assert len(items) == 0

    def test_empty_and_malformed_transcript(self, extractor):
        assert extractor.extract_from_transcript([]) == []
        assert extractor.extract_from_transcript([{}]) == []
        assert extractor.extract_from_transcript([{"speaker": "Ghost"}]) == []

    def test_multiple_lines_transcript(self, extractor):
        transcript = [
            {"speaker": "Alice", "text": "Good morning team, let us begin.", "timestamp_str": "00:01"},
            {"speaker": "Bob", "text": "I will prepare the presentation slides by Thursday.", "timestamp_str": "00:05"},
            {"speaker": "Charlie", "text": "We need to fix the memory leak before end of month.", "timestamp_str": "00:12"},
        ]
        results = extractor.extract_from_transcript(transcript)
        assert len(results) == 2
        assert results[0]["assignee"] == "Bob"
        assert results[1]["assignee"] == "Charlie"
