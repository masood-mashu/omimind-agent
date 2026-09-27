"""
test_task_dispatcher.py - Unit & Format Tests for LyzrTaskDispatcher
Covers:
- Email draft composition, subject generation, participant addressing
- Jira ticket structure, schema, labels, and ticket keys
- Edge cases: 0 action items, empty participants list
"""
import pytest

from agents.task_dispatcher import LyzrTaskDispatcher


class TestLyzrTaskDispatcher:
    @pytest.fixture
    def dispatcher(self):
        return LyzrTaskDispatcher()

    def test_email_generation_with_actions(self, dispatcher):
        summary = {
            "title": "Quarterly Planning",
            "participants": ["Alice", "Bob"],
            "executive_summary": "Reviewed roadmap and confirmed milestones.",
            "key_decisions": ["Launch v2 in October"],
            "risks_and_blockers": ["Database migration window"]
        }
        actions = [
            {
                "id": "act_1",
                "title": "Provision staging cluster",
                "assignee": "Alice",
                "due_date": "By Friday",
                "priority": "High",
                "quote": "I will provision staging cluster by Friday."
            }
        ]
        email = dispatcher.generate_followup_email(summary, actions)
        assert "[Action Required]" in email["subject"]
        assert "Quarterly Planning" in email["subject"]
        assert "Alice, Bob" in email["to"]
        assert "Provision staging cluster" in email["body"]
        assert "✓ Launch v2 in October" in email["body"]
        assert "⚠️ Database migration window" in email["body"]

    def test_email_generation_zero_actions(self, dispatcher):
        summary = {"title": "Check-in", "participants": []}
        email = dispatcher.generate_followup_email(summary, [])
        assert "No open action items pending" in email["body"]

    def test_jira_tickets_formatting(self, dispatcher):
        actions = [
            {
                "id": "act_42",
                "title": "Setup Prometheus alerting",
                "assignee": "Charlie",
                "due_date": "Tomorrow",
                "priority": "Critical",
                "quote": "I will setup Prometheus alerting tomorrow."
            }
        ]
        tickets = dispatcher.generate_jira_tickets(actions)
        assert len(tickets) == 1
        t = tickets[0]
        assert t["ticket_key"] == "OMI-42"
        assert t["summary"] == "Setup Prometheus alerting"
        assert t["assignee"] == "Charlie"
        assert t["priority"] == "Critical"
        assert "OmiVoice" in t["labels"]
        assert "LyzrAgent" in t["labels"]
        assert "QdrantMemory" in t["labels"]
