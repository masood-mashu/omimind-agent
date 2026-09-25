"""
action_extractor.py - Lyzr Action Item & Commitment Extractor
Detects verbal promises, task assignments, deadlines, and priority levels from meeting transcripts.
"""
import re
from typing import List, Dict, Any

COMMITMENT_TRIGGERS = [
    r"i will\s+(.+)",
    r"i'll\s+(.+)",
    r"we need to\s+(.+)",
    r"let's make sure to\s+(.+)",
    r"please ensure\s+(.+)",
    r"can you take care of\s+(.+)",
    r"assigned to\s+([a-zA-Z]+)",
    r"action item:\s*(.+)",
    r"todo:\s*(.+)"
]

DEADLINE_PATTERNS = [
    r"(by (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))",
    r"(by eod|by end of day|by tomorrow|by tonight)",
    r"(by next week|before end of month|by q[1-4])",
    r"(within \d+ days|in \d+ hours)"
]

class LyzrActionExtractor:
    def __init__(self):
        self.extracted_items: List[Dict[str, Any]] = []

    def extract_from_utterance(self, speaker: str, text: str, timestamp_str: str) -> List[Dict[str, Any]]:
        text_lower = text.lower()
        items = []

        # Detect deadline
        found_deadline = "Next Sprint"
        for d_pat in DEADLINE_PATTERNS:
            match = re.search(d_pat, text_lower)
            if match:
                found_deadline = match.group(1).title()
                break

        # Detect priority
        priority = "Medium"
        if any(w in text_lower for w in ["urgent", "critical", "asap", "blocker", "p0", "immediately"]):
            priority = "Critical"
        elif any(w in text_lower for w in ["high priority", "important", "p1", "soon"]):
            priority = "High"
        elif any(w in text_lower for w in ["low priority", "nice to have", "when you have time"]):
            priority = "Low"

        # Detect commitment
        for trigger in COMMITMENT_TRIGGERS:
            match = re.search(trigger, text_lower)
            if match:
                action_text = match.group(1).strip()
                # Clean up sentence end
                action_text = re.split(r"[.?!;]", action_text)[0].strip()
                if len(action_text) > 8:
                    item = {
                        "id": f"act_{len(self.extracted_items) + len(items) + 1}",
                        "title": action_text.capitalize(),
                        "assignee": speaker,
                        "due_date": found_deadline,
                        "priority": priority,
                        "quote": text,
                        "timestamp": timestamp_str,
                        "status": "OPEN"
                    }
                    items.append(item)
                    break

        self.extracted_items.extend(items)
        return items

    def extract_from_transcript(self, transcript_lines: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        results = []
        for line in transcript_lines:
            items = self.extract_from_utterance(
                speaker=line.get("speaker", "Unknown"),
                text=line.get("text", ""),
                timestamp_str=line.get("timestamp_str", "00:00")
            )
            results.extend(items)
        return results
