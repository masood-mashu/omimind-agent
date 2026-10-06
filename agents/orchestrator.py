"""
orchestrator.py - Central Coordinator for OmiMind Multi-Agent Swarm
Coordinates Qdrant vector memory indexing, Lyzr agent synthesis, and natural language recall.
"""
from typing import Any

from agents.action_extractor import LyzrActionExtractor
from agents.calendar_scheduler import LyzrCalendarScheduler
from agents.executive_synth import LyzrExecutiveSynthesizer
from agents.lyzr_client import LyzrClient
from agents.memory_agent import QdrantMemoryAgent
from agents.task_dispatcher import LyzrTaskDispatcher


class OmiMindOrchestrator:
    def __init__(self, storage_path: str = "./qdrant_storage", lyzr_client: LyzrClient | None = None):
        self.memory = QdrantMemoryAgent(storage_path=storage_path)
        self.extractor = LyzrActionExtractor()
        self.synthesizer = LyzrExecutiveSynthesizer()
        self.dispatcher = LyzrTaskDispatcher()
        self.scheduler = LyzrCalendarScheduler()
        self.lyzr = lyzr_client or LyzrClient()

    def process_session(
        self,
        session_id: str,
        title: str,
        transcript_lines: list[dict[str, str]],
        uid: str = "default_user",
    ) -> dict[str, Any]:
        """
        Ingests a complete meeting/lecture session:
        1. Embeds each line into Qdrant vector memory with metadata payloads.
        2. Extracts commitments and action items.
        3. Generates executive synthesis.
        4. Dispatches follow-up emails and Jira tickets.
        5. Extracts calendar sync commitments and generates Google Meet/iCal links.
        """
        indexed_points = []
        for i, line in enumerate(transcript_lines):
            p_id = self.memory.index_utterance(
                session_id=session_id,
                speaker=line.get("speaker", "Speaker"),
                text=line.get("text", ""),
                timestamp=float(i * 15),
                timestamp_str=line.get("timestamp_str", f"00:{i*15:02d}"),
                topic=line.get("topic", "general"),
                urgency=line.get("urgency", "normal"),
                uid=uid,
            )
            indexed_points.append(p_id)

        context = self.memory.search_memory(
            query=f"Summarize the meeting and extract decisions, risks, and action items for {title}",
            limit=min(8, max(1, len(transcript_lines))),
            uid=uid,
        )
        lyzr_result = self.lyzr.reason(
            uid=session_id,
            question="Produce grounded meeting intelligence from the supplied transcript context.",
            context=context,
        )

        # Primary intelligence: Reconcile Lyzr Manager synthesis with deterministic validation
        summary, action_items = self.reconcile_meeting_intelligence(
            lyzr_text=lyzr_result.text if lyzr_result.provider == "lyzr_studio_cloud" else "",
            title=title,
            transcript_lines=transcript_lines,
        )

        # Task dispatching (LyzrTaskDispatcher)
        email_draft = self.dispatcher.generate_followup_email(summary, action_items)
        jira_tickets = self.dispatcher.generate_jira_tickets(action_items)

        # Calendar scheduling (LyzrCalendarScheduler)
        calendar_events = self.scheduler.extract_calendar_events(transcript_lines)

        return {
            "session_id": session_id,
            "title": title,
            "indexed_vectors_count": len(indexed_points),
            "summary": summary,
            "action_items": action_items,
            "email_draft": email_draft,
            "jira_tickets": jira_tickets,
            "calendar_events": calendar_events,
            "reasoning": {
                "provider": lyzr_result.provider,
                "agent_id": lyzr_result.agent_id,
                "response": lyzr_result.text,
                "error": lyzr_result.error,
            }
        }

    def reconcile_meeting_intelligence(
        self,
        lyzr_text: str,
        title: str,
        transcript_lines: list[dict[str, str]],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """
        Reconciles Lyzr Manager multi-agent reasoning (Meeting Analyst + Action Extractor)
        with deterministic schema normalization and offline fallback.
        """
        summary = self.synthesizer.synthesize_meeting(title, transcript_lines)
        action_items = self.extractor.extract_from_transcript(transcript_lines)

        if not lyzr_text or not lyzr_text.strip():
            return summary, action_items

        summary["executive_summary"] = _extract_manager_summary(lyzr_text, summary["executive_summary"])
        summary["key_decisions"] = _extract_manager_bullets(
            lyzr_text,
            r"(?i)(?:###?\s*(?:key\s+)?decisions?(?:\s+made)?[:\s]*\n)(.*?)(?=\n###?|\Z)",
            summary["key_decisions"],
        )
        summary["risks_and_blockers"] = _extract_manager_bullets(
            lyzr_text,
            r"(?i)(?:###?\s*(?:risks?(?:\s+and\s+blockers?)?|blockers?|unresolved\s+issues?)[:\s]*\n)(.*?)(?=\n###?|\Z)",
            summary["risks_and_blockers"],
        )
        action_items = _extract_manager_actions(lyzr_text, transcript_lines, action_items)
        return summary, action_items

    def query_semantic_memory(self, query: str, limit: int = 4, uid: str | None = None) -> dict[str, Any]:
        """
        Semantic Q&A over past audio transcripts stored in Qdrant.
        """
        results = self.memory.search_memory(query=query, limit=limit, uid=uid)

        if not results:
            answer = f"No direct conversational records found in Qdrant matching '{query}'."
        else:
            top_hit = results[0]
            answer = (
                f"Based on ambient memory from {top_hit['speaker']} at {top_hit['timestamp_str']}: "
                f"\"{top_hit['text']}\" (Vector Relevance Score: {top_hit['score']})."
            )

        return {
            "query": query,
            "answer": answer,
            "matches": results,
            "relevance_top": results[0]["score"] if results else 0.0
        }


def _extract_manager_summary(text: str, default_summary: str) -> str:
    import re
    match = re.search(r"(?i)(?:###?\s*(?:executive\s+)?summary[:\s]*\n)(.*?)(?=\n###?|\Z)", text, re.DOTALL)
    if match:
        extracted = match.group(1).strip()
        if len(extracted) > 20:
            return extracted
    return default_summary


def _extract_manager_bullets(text: str, pattern: str, default_bullets: list[str]) -> list[str]:
    import re
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return default_bullets
    lines = [
        re.sub(r"^[-*•\d\.\s]+", "", line).strip()
        for line in match.group(1).split("\n")
        if re.sub(r"^[-*•\d\.\s]+", "", line).strip()
    ]
    return lines or default_bullets


def _parse_single_action_line(clean_line: str, transcript_lines: list[dict[str, str]], item_id: str) -> dict[str, Any]:
    import re

    pri = "Medium"
    if re.search(r"\b(p0|critical|urgent|asap|blocker)\b", clean_line, re.I):
        pri = "Critical"
    elif re.search(r"\b(high|p1|important)\b", clean_line, re.I):
        pri = "High"
    elif re.search(r"\b(low|nice to have)\b", clean_line, re.I):
        pri = "Low"

    assignee_match = re.search(r"(?:owner|assignee|assigned to)[:\s]+([a-zA-Z\s]+?)(?:,|\.|\)|due|deadline|\Z)", clean_line, re.I)
    if assignee_match:
        assignee = assignee_match.group(1).strip()
    else:
        speaker_names = [line.get("speaker", "") for line in transcript_lines if line.get("speaker")]
        found = next((s for s in speaker_names if s.lower() in clean_line.lower()), None)
        assignee = found or "Team"

    due_match = re.search(r"(?:due(?:\s+date)?|deadline|by)[:\s]+([a-zA-Z0-9\s]+?)(?:,|\.|\)|\Z)", clean_line, re.I)
    due_date = due_match.group(1).strip() if due_match else "Upcoming Sprint"

    title_clean = re.sub(r"\[.*?\]", "", clean_line).strip()
    if len(title_clean) > 80:
        title_clean = title_clean[:80] + "..."

    return {
        "id": item_id,
        "title": title_clean,
        "assignee": assignee,
        "due_date": due_date,
        "priority": pri,
        "quote": clean_line,
        "timestamp": "Lyzr Action Extractor",
        "status": "OPEN",
    }


def _extract_manager_actions(
    text: str,
    transcript_lines: list[dict[str, str]],
    default_actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    import re
    match = re.search(r"(?i)(?:###?\s*action\s+items?(?:\s+and\s+deliverables)?[:\s]*\n)(.*?)(?=\n###?|\Z)", text, re.DOTALL)
    if not match:
        return default_actions

    raw_lines = [
        line.strip()
        for line in match.group(1).split("\n")
        if line.strip() and line.strip().startswith(("-", "*", "•", "1", "2", "3", "4", "5"))
    ]
    parsed = []
    for i, raw in enumerate(raw_lines):
        clean = re.sub(r"^[-*•\d\.\s]+", "", raw).strip()
        if len(clean) >= 6:
            parsed.append(_parse_single_action_line(clean, transcript_lines, f"act_lyzr_{i + 1}"))
    return parsed or default_actions
