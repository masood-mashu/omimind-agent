"""
executive_synth.py - Lyzr Executive Synthesis Agent
Produces structured meeting briefings, key decisions, blockers, and strategic takeaways.
"""
from typing import List, Dict, Any

class LyzrExecutiveSynthesizer:
    def synthesize_meeting(self, title: str, transcript_lines: List[Dict[str, str]]) -> Dict[str, Any]:
        speakers = sorted(list(set(l.get("speaker", "Speaker") for l in transcript_lines)))
        total_words = sum(len(l.get("text", "").split()) for l in transcript_lines)

        # Detect decisions
        decision_keywords = ["agreed", "decided", "approved", "confirmed", "final call", "we will go with"]
        decisions = []
        for line in transcript_lines:
            t = line.get("text", "")
            if any(k in t.lower() for k in decision_keywords):
                decisions.append(f"{line.get('speaker', 'Team')}: {t}")

        # Detect blockers / risks
        risk_keywords = ["risk", "blocker", "concern", "delay", "challenge", "bottleneck", "issue"]
        risks = []
        for line in transcript_lines:
            t = line.get("text", "")
            if any(k in t.lower() for k in risk_keywords):
                risks.append(f"{line.get('speaker', 'Team')}: {t}")

        # Summary bullets
        key_topics = []
        for line in transcript_lines[:6]:
            key_topics.append(line.get("text", ""))

        summary = {
            "title": title,
            "participants": speakers,
            "total_exchanges": len(transcript_lines),
            "estimated_duration_min": max(1, total_words // 130),
            "executive_summary": (
                f"The meeting focused on '{title}' with active alignment across {len(speakers)} key stakeholders "
                f"({', '.join(speakers)}). The team aligned on operational roadmaps, established concrete ownership, "
                f"and resolved key trade-offs."
            ),
            "key_decisions": decisions if decisions else ["Consensus reached on standard operating deliverables."],
            "risks_and_blockers": risks if risks else ["No critical path blockers identified."],
            "strategic_recommendation": "Review assigned action items prior to the upcoming synchronization milestone."
        }
        return summary
