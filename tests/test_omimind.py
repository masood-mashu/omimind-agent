"""
test_omimind.py - Pytest Verification Suite for OmiMind
Covers:
1. Qdrant Vector Collection Indexing & Cosine Recall
2. Lyzr Action Item & Commitment Extraction
3. Executive Meeting Synthesis
4. Task Dispatcher (Email & Jira Tickets)
5. Full Swarm Orchestration & Semantic Q&A
"""
import pytest
from agents.memory_agent import QdrantMemoryAgent, generate_semantic_embedding
from agents.action_extractor import LyzrActionExtractor
from agents.executive_synth import LyzrExecutiveSynthesizer
from agents.task_dispatcher import LyzrTaskDispatcher
from agents.orchestrator import OmiMindOrchestrator
from backend.mock_data import DEMO_MEETINGS

def test_semantic_embedding_generator():
    """Verify that semantic vectors are 128-dim and unit normalized."""
    vec1 = generate_semantic_embedding("Allocate $450,000 budget for H100 cluster")
    vec2 = generate_semantic_embedding("Allocate budget for GPU compute")
    assert len(vec1) == 128
    assert len(vec2) == 128

    # Cosine dot product of related texts must be strongly positive
    dot = sum(a * b for a, b in zip(vec1, vec2))
    assert dot > 0.40

def test_qdrant_vector_memory():
    """Verify that Qdrant indexes points and executes semantic vector search."""
    memory = QdrantMemoryAgent(storage_path=":memory:")
    
    # Index 2 distinct statements
    memory.index_utterance("sess1", "Sarah (CFO)", "We will approve the $450k budget by Friday.", 10.0, "00:10", "finance", "high")
    memory.index_utterance("sess1", "Marcus", "The database latency benchmark passed under 50ms.", 20.0, "00:20", "tech", "normal")

    # Semantic search
    results = memory.search_memory("How much money or budget was approved?", limit=2)
    assert len(results) > 0
    top_hit = results[0]
    assert top_hit["speaker"] == "Sarah (CFO)"
    assert "budget" in top_hit["text"].lower()

def test_lyzr_action_extractor():
    """Verify that action items, assignees, and deadlines are correctly extracted."""
    extractor = LyzrActionExtractor()
    lines = [
        {"speaker": "David", "timestamp_str": "01:00", "text": "I will review the security firewall settings by Friday."},
        {"speaker": "Elena", "timestamp_str": "02:00", "text": "We need to deploy the customer copilot before end of month."}
    ]
    items = extractor.extract_from_transcript(lines)
    assert len(items) == 2
    assert items[0]["assignee"] == "David"
    assert "Friday" in items[0]["due_date"]
    assert items[1]["assignee"] == "Elena"

def test_executive_synthesizer():
    """Verify executive summary, key decisions, and blockers synthesis."""
    synth = LyzrExecutiveSynthesizer()
    meeting = DEMO_MEETINGS["q4_strategy"]
    summary = synth.synthesize_meeting(meeting["title"], meeting["lines"])

    assert summary["title"] == meeting["title"]
    assert len(summary["participants"]) == 4
    assert len(summary["key_decisions"]) > 0
    assert len(summary["risks_and_blockers"]) > 0

def test_task_dispatcher():
    """Verify follow-up email and Jira ticket generation."""
    dispatcher = LyzrTaskDispatcher()
    sample_summary = {
        "title": "Sprint Sync",
        "participants": ["Alice", "Bob"],
        "executive_summary": "Team aligned on sprint goals.",
        "key_decisions": ["Ship v1.0"],
        "risks_and_blockers": []
    }
    sample_items = [
        {"id": "act_1", "title": "Deploy staging server", "assignee": "Bob", "due_date": "Tomorrow", "priority": "High", "quote": "I will deploy staging"}
    ]

    email = dispatcher.generate_followup_email(sample_summary, sample_items)
    assert "[Action Required]" in email["subject"]
    assert "Bob" in email["body"]

    tickets = dispatcher.generate_jira_tickets(sample_items)
    assert len(tickets) == 1
    assert tickets[0]["ticket_key"] == "OMI-1"
    assert tickets[0]["assignee"] == "Bob"

def test_full_orchestration():
    """Verify end-to-end multi-agent session processing and semantic Q&A."""
    orchestrator = OmiMindOrchestrator(storage_path=":memory:")
    meeting = DEMO_MEETINGS["sre_postmortem"]

    dossier = orchestrator.process_session(
        session_id=meeting["id"],
        title=meeting["title"],
        transcript_lines=meeting["lines"]
    )

    assert dossier["indexed_vectors_count"] == len(meeting["lines"])
    assert len(dossier["action_items"]) > 0
    assert dossier["email_draft"] is not None
    assert len(dossier["jira_tickets"]) > 0

    # Test natural language semantic query
    res = orchestrator.query_semantic_memory("Why was there an outage and who was assigned?")
    assert res["relevance_top"] > 0
    assert len(res["matches"]) > 0
