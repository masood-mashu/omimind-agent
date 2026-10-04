"""
calendar_scheduler.py - Lyzr Calendar Scheduler & Follow-Up Event Agent (Agent 5)
Extracts meeting commitments, scheduling intent, and generates iCal/Google Calendar invites.
"""
import re
import urllib.parse
from datetime import UTC, datetime
from typing import Any


class LyzrCalendarScheduler:
    def __init__(self):
        self.trigger_patterns = [
            re.compile(r"(?:let's|let us|can we|we should|i will|we need to)\s+(?:schedule|meet|sync|set up a meeting|have a call|review)", re.IGNORECASE),
            re.compile(r"(?:schedule|meeting|sync|follow-up)\s+(?:on|next|tomorrow|this|at)", re.IGNORECASE),
        ]
        self.time_pattern = re.compile(r"\b(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))\b")
        self.date_pattern = re.compile(
            r"\b(tomorrow|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
            r"(?:this\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
            r"(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?)\b",
            re.IGNORECASE
        )

    def extract_calendar_events(self, transcript_lines: list[dict[str, str]]) -> list[dict[str, Any]]:
        """
        Scans conversation transcript for meeting and sync commitments.
        """
        events = []
        for line in transcript_lines:
            text = line.get("text", "").strip()
            speaker = line.get("speaker", "Speaker")

            if not any(pattern.search(text) for pattern in self.trigger_patterns):
                continue

            time_match = self.time_pattern.search(text)
            date_match = self.date_pattern.search(text)

            time_str = time_match.group(1).strip() if time_match else "10:00 AM"
            date_str = date_match.group(1).strip() if date_match else "Upcoming"

            # Derive title from utterance
            title = "Follow-up Meeting"
            if re.search(r"review", text, re.IGNORECASE):
                title = "Follow-up: Architecture & Telemetry Review"
            elif re.search(r"sync", text, re.IGNORECASE):
                title = "Team Sync: Action Plan & Architecture"
            elif re.search(r"budget|strategy", text, re.IGNORECASE):
                title = "Strategy Follow-up Session"

            # Build Google Calendar Link
            params = {
                "action": "TEMPLATE",
                "text": title,
                "details": f"Automated OmiMind follow-up scheduled from ambient voice session by {speaker}.\nContext: \"{text}\"",
                "location": "Google Meet / Omi Ambient Room"
            }
            gcal_url = f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

            event = {
                "id": f"evt-{len(events) + 1}",
                "title": title,
                "speaker_source": speaker,
                "context_utterance": text,
                "date_str": date_str,
                "time_str": time_str,
                "duration_minutes": 30,
                "google_calendar_url": gcal_url
            }
            event["ics_data"] = self.generate_ics(event)
            events.append(event)

        return events

    def generate_ics(self, event: dict[str, Any]) -> str:
        """
        Generates standard RFC 5545 iCalendar content for calendar client import (.ics).
        """
        now_str = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        title = event.get("title", "OmiMind Meeting")
        desc = event.get("details", event.get("description", "Scheduled via OmiMind Voice Agent."))
        title_hash = str(abs(hash(title)))[:8]

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//OmiMind//Autonomous Chief of Staff//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:omimind-{now_str}-{title_hash}@omimind.ai",
            f"DTSTAMP:{now_str}",
            f"DTSTART:{now_str}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:{desc.replace(chr(10), ' ')}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
            "END:VCALENDAR"
        ]
        return "\r\n".join(lines)
