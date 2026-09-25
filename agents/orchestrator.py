"""
orchestrator.py - Central Coordinator for OmiMind Multi-Agent Swarm
Coordinates Qdrant vector memory indexing, Lyzr agent synthesis, and natural language recall.
"""
from typing import List, Dict, Any, Optional
from agents.memory_agent import QdrantMemoryAgent
from agents.action_extractor import LyzrActionExtractor
from agents.executive_synth import LyzrExecutiveSynthesizer
from agents.task_dispatcher import LyzrTaskDispatcher

class OmiMindOrchestrator:
    def __init__(self, storage_path: str = "./qdrant_storage"):
        self.memory = QdrantMemoryAgent(storage_path=storage_path)
        self.extractor = LyzrActionExtractor()
        self.synthesizer = LyzrExecutiveSynthesizer()
        self.dispatcher = LyzrTaskDispatcher()

    def process_session(self, session_id: str, title: str, transcript_lines: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Ingests a complete meeting/lecture session:
        1. Embeds each line into Qdrant vector memory with metadata payloads.
        2. Extracts commitments and action items.
        3. Generates executive synthesis.
        4. Dispatches follow-up emails and Jira tickets.
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
                urgency=line.get("urgency", "normal")
            )
            indexed_points.append(p_id)

        # Agent 1: Action items
        action_items = self.extractor.extract_from_transcript(transcript_lines)

        # Agent 2: Executive synthesis
        summary = self.synthesizer.synthesize_meeting(title, transcript_lines)

        # Agent 3: Task dispatching
        email_draft = self.dispatcher.generate_followup_email(summary, action_items)
        jira_tickets = self.dispatcher.generate_jira_tickets(action_items)

        return {
            "session_id": session_id,
            "title": title,
            "indexed_vectors_count": len(indexed_points),
            "summary": summary,
            "action_items": action_items,
            "email_draft": email_draft,
            "jira_tickets": jira_tickets
        }

    def query_semantic_memory(self, query: str, limit: int = 4) -> Dict[str, Any]:
        """
        Semantic Q&A over past audio transcripts stored in Qdrant.
        """
        results = self.memory.search_memory(query=query, limit=limit)
        
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
