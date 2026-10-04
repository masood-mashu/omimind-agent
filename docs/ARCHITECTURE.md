# OmiMind System Architecture

This document describes the runtime components, data flows, and architectural layers of OmiMind: Ambient Voice Memory & Autonomous Chief of Staff.

```mermaid
flowchart TD
    User["🎙️ Omi AI Wearable / Ambient Audio"] -->|Diarised Audio Streams| Omi["Omi Voice Webhook Ingestion Engine"]
    Omi -->|Speaker Segments & Transcripts| API["FastAPI Application Server<br/>(backend/main.py)"]

    subgraph QDRANT ["⚡ Qdrant Cloud Vector Memory Layer"]
        API -->|128-Dim Normalized Vectors| Qdrant[("Qdrant Cloud: omi_ambient_memory<br/>Persistent Vector Index")]
        Qdrant <-->|Hybrid 60% Cosine + 40% Lexical| MemAgent["Memory Agent (agents/memory_agent.py)"]
    end

    subgraph LYZR ["🐝 Lyzr 5-Agent Swarm (Real-Time SSE Stream)"]
        API -->|SSE Event Stream /api/process-stream| Stream["Live Agent Monitor Dashboard"]
        Stream --> A1["🗄️ Agent 1: Qdrant Memory Indexer"]
        Stream --> A2["🎯 Agent 2: Lyzr Action Extractor"]
        Stream --> A3["🧠 Agent 3: Lyzr Executive Synthesizer"]
        Stream --> A4["📬 Agent 4: Lyzr Task Dispatcher"]
        Stream --> A5["📅 Agent 5: Lyzr Calendar Scheduler"]
    end

    subgraph OUTPUTS ["📦 Autonomous Deliverables & Integrations"]
        A2 --> Actions["Action Items + Kanban Dashboard"]
        A3 --> Dossier["Executive Briefing + Decisions + Risks"]
        A4 --> Email["1-Click Gmail & SMTP Follow-Up Email"]
        A4 --> Jira["Jira / GitHub API-Ready Tickets (OMI-1..6)"]
        A5 --> Calendar["Calendar Sync (.ics) + Google Meet Links"]
        MemAgent --> QnA["400ms Debounced Semantic Q&A Recall"]
        API -->|Grounded /ask Endpoint| Studio["Lyzr Studio Cloud Inference<br/>agent-prod.studio.lyzr.ai"]
    end

    subgraph MCP ["🔌 Model Context Protocol (MCP) Interop"]
        MCP_Server["mcp_server.py (JSON-RPC stdio)"] <--> Qdrant
        MCP_Server <--> ExternalAgents["Claude Desktop / Cursor / Antigravity"]
    end

    classDef external fill:#172554,stroke:#60a5fa,color:#dbeafe;
    classDef service fill:#064e3b,stroke:#34d399,color:#d1fae5;
    classDef store fill:#3f1d5b,stroke:#c084fc,color:#f3e8ff;
    class User,Omi,Studio,ExternalAgents external;
    class API,MemAgent,A1,A2,A3,A4,A5,MCP_Server service;
    class Qdrant store;
```

---

## Component Roles & Responsibilities

1. **Omi Voice Ingestion Layer:**
   - Exposes official webhook contracts (`POST /omi/conversation`, `POST /omi/realtime`, `POST /api/omi-webhook`).
   - Normalizes audio transcripts with speaker diarisation and sub-50ms acknowledgement.

2. **Qdrant Cloud Vector Memory Layer:**
   - Collection: `omi_ambient_memory`.
   - Embeds each spoken utterance into 128-dimensional L2-normalized dense vectors.
   - Hybrid scoring: 60% cosine similarity + 40% lexical stem overlap for dynamic relevance scores.
   - Privacy-first knowledge control via `POST /api/forget` and `DELETE /api/memory`.

3. **Lyzr Multi-Agent Reasoning Layer:**
   - 5 specialized agents execute in sequence, orchestrated by `OmiMindOrchestrator`.
   - Streams live execution events via Server-Sent Events (SSE) to the frontend dashboard.
   - `/ask` endpoint connects directly to Lyzr Studio Cloud (`https://agent-prod.studio.lyzr.ai/v3/inference/chat/`) for grounded context synthesis.

4. **Model Context Protocol (MCP) Server:**
   - Standard JSON-RPC 2.0 stdio server (`mcp_server.py`) exposing ambient memory tools to Claude Desktop, Cursor, and other MCP clients.
