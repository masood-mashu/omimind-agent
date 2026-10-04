"""
test_calendar_scheduler.py - Tests for LyzrCalendarScheduler agent
"""
import pytest
from agents.calendar_scheduler import LyzrCalendarScheduler


class TestLyzrCalendarScheduler:
    @pytest.fixture
    def scheduler(self):
        return LyzrCalendarScheduler()

    def test_extract_followup_meeting(self, scheduler):
        transcript = [
            {"speaker": "David", "text": "Let's schedule a follow-up review next Tuesday at 2 PM with Elena."},
            {"speaker": "Elena", "text": "Sounds good, I will prepare the telemetry graphs."}
        ]
        events = scheduler.extract_calendar_events(transcript)
        assert len(events) >= 1
        event = events[0]
        assert "Review" in event["title"] or "Follow-up" in event["title"]
        assert "tuesday" in event["date_str"].lower() or "next tuesday" in event["date_str"].lower()
        assert "2" in event["time_str"] or "14:00" in event["time_str"]
        assert "google_calendar_url" in event
        assert event["google_calendar_url"].startswith("https://calendar.google.com/calendar/render")

    def test_extract_sync_with_specific_time(self, scheduler):
        transcript = [
            {"speaker": "Marcus", "text": "Can we sync tomorrow at 10:30 AM to finalize the architecture?"}
        ]
        events = scheduler.extract_calendar_events(transcript)
        assert len(events) == 1
        assert "10:30" in events[0]["time_str"]
        assert "sync" in events[0]["title"].lower() or "architecture" in events[0]["title"].lower()

    def test_generate_ics_format(self, scheduler):
        event = {
            "title": "OmiMind Executive Sync",
            "description": "Follow-up discussion on Q4 budget.",
            "date_str": "2026-10-15",
            "time_str": "14:00",
            "duration_minutes": 30
        }
        ics = scheduler.generate_ics(event)
        assert "BEGIN:VCALENDAR" in ics
        assert "BEGIN:VEVENT" in ics
        assert "SUMMARY:OmiMind Executive Sync" in ics
        assert "END:VEVENT" in ics
        assert "END:VCALENDAR" in ics

    def test_empty_transcript_returns_empty_list(self, scheduler):
        events = scheduler.extract_calendar_events([])
        assert events == []

    def test_transcript_without_scheduling_returns_empty(self, scheduler):
        transcript = [
            {"speaker": "Alice", "text": "The server latency dropped by 40% after deploying the cache."},
            {"speaker": "Bob", "text": "Great job everyone, moving on to the next topic."}
        ]
        events = scheduler.extract_calendar_events(transcript)
        assert events == []
