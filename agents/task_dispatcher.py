"""
task_dispatcher.py - Lyzr Autonomous Task Dispatcher
Converts extracted meeting items into actionable outputs: email drafts, Jira tickets, and follow-ups.
"""
from typing import List, Dict, Any

class LyzrTaskDispatcher:
    def generate_followup_email(self, summary: Dict[str, Any], action_items: List[Dict[str, Any]]) -> Dict[str, str]:
        subject = f"[Action Required] Follow-Up: {summary.get('title', 'Executive Meeting Summary')}"
        participants = ", ".join(summary.get("participants", ["Team"]))

        action_bullets = ""
        for item in action_items:
            action_bullets += f"- [{item['priority'].upper()}] {item['title']} -> Assignee: {item['assignee']} (Due: {item['due_date']})\n"

        body = f"""Hi Team,

Thank you for your time during our discussion on '{summary.get('title', 'Project Strategy')}'.

EXECUTIVE SUMMARY:
{summary.get('executive_summary')}

KEY DECISIONS:
""" + "\n".join([f"✓ {d}" for d in summary.get("key_decisions", [])]) + f"""

ACTION ITEMS & DELIVERABLES:
{action_bullets if action_bullets else 'No open action items pending.'}

RISKS & MONITORING:
""" + "\n".join([f"⚠️ {r}" for r in summary.get("risks_and_blockers", [])]) + f"""

Best regards,
OmiMind Autonomous Chief of Staff
(Powered by Lyzr & Qdrant)
"""
        return {
            "subject": subject,
            "to": participants,
            "body": body.strip()
        }

    def generate_jira_tickets(self, action_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tickets = []
        for item in action_items:
            tickets.append({
                "ticket_key": f"OMI-{item['id'].replace('act_', '')}",
                "summary": item["title"],
                "assignee": item["assignee"],
                "due_date": item["due_date"],
                "priority": item["priority"],
                "description": f"Extracted automatically from meeting context: \"{item['quote']}\"",
                "labels": ["OmiVoice", "LyzrAgent", "QdrantMemory"]
            })
        return tickets
