# OmiMind End-to-End Sequence Diagram

This sequence details chronological interactions across the Omi wearable, FastAPI ingestion, Qdrant vector memory, Lyzr Manager reasoning (with live SSE updates), and deterministic user-controlled outputs.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Meeting Attendee
    participant Omi as Omi Wearable / Microphone
    participant UI as Live Web Dashboard
    participant API as FastAPI Application
    participant Orch as OmiMindOrchestrator
    participant Q as Qdrant Cloud (`omi_ambient_memory`)
    participant Studio as Lyzr Studio Cloud
    participant Ext as Google Meet / Gmail / Jira

    Note over User,Omi: Phase 1: Ambient Audio & Diarisation
    User->>Omi: Live conversation / Voice memo
    Omi->>API: POST /omi/conversation or /api/omi-webhook
    API-->>Omi: HTTP 200 OK (< 50ms fast-ack)

    Note over API,Q: Phase 2: Vector Memory & Lyzr Manager Reasoning
    UI->>API: POST /api/process-stream (or /api/custom-voice-stream)
    API-->>UI: SSE: MemoryAgent [RUNNING]
    API->>Orch: Index transcript utterances
    Orch->>Q: Upsert 384-dim FastEmbed embeddings + speaker metadata
    Q-->>Orch: Stored vector point IDs
    API-->>UI: SSE: MemoryAgent [DONE] (Indexed vector count)

    API-->>UI: SSE: ActionExtractor [RUNNING]
    API->>Orch: Extract commitments & deadlines
    Orch-->>API: Extracted tasks, assignees, deadlines, P0 priorities
    API-->>UI: SSE: ActionExtractor [DONE]

    API-->>UI: SSE: ExecutiveSynthesizer [RUNNING]
    API->>Orch: Synthesize strategic briefing
    Orch-->>API: Executive summary, confirmed decisions, risks
    API-->>UI: SSE: ExecutiveSynthesizer [DONE]

    API-->>UI: SSE: TaskDispatcher [RUNNING]
    API->>Orch: Format email & Jira tickets
    Orch-->>API: Follow-up email draft + Jira JSON (OMI-1..6)
    API-->>UI: SSE: TaskDispatcher [DONE]

    API-->>UI: SSE: CalendarScheduler [RUNNING]
    API->>Orch: Detect calendar intent
    Orch-->>API: Google Meet URLs + RFC 5545 .ics content
    API-->>UI: SSE: CalendarScheduler [DONE]

    API-->>UI: SSE: [COMPLETE] Full intelligence dossier
    UI-->>User: Render Executive Tabs, Kanban, & Calendar Sync

    Note over User,Studio: Phase 3: Semantic Q&A & Lyzr Studio Inference
    User->>UI: Type question: "What did Sarah say about the budget?"
    UI->>API: POST /api/query (or POST /ask)
    API->>Q: Hybrid search (60% cosine + 40% lexical)
    Q-->>API: Ranked matching utterances + speaker attribution
    opt Lyzr Studio Cloud Inference
        API->>Studio: POST /v3/inference/chat/ (Context + Question)
        Studio-->>API: Synthesized strategic answer
    end
    API-->>UI: Grounded answer with citation & similarity score
    UI-->>User: Display 99%+ relevance match and quote

    Note over User,Ext: Phase 4: Autonomous Deliverables Action
    User->>UI: Click "+ Google Meet" / "Send via Gmail" / "Download .ics"
    UI->>Ext: Launch calendar event / Open Gmail draft
```
