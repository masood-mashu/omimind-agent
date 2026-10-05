# OmiMind System Architecture

This document describes the runtime components, data flows, and architectural layers of OmiMind: Ambient Voice Memory & Autonomous Chief of Staff.

```mermaid
flowchart TD
    User["🎙️ Omi AI Wearable / Ambient Audio"] -->|Diarised Audio Streams| Omi["Omi Voice Webhook Ingestion Engine"]
    Omi -->|Speaker Segments & Transcripts| API["FastAPI Application Server<br/>(backend/main.py)"]

    subgraph QDRANT ["⚡ Qdrant Cloud Vector Memory Layer"]
        API -->|384-Dim FastEmbed Vectors| Qdrant[("Configured Qdrant: omi_ambient_memory<br/>Persistent Vector Index")]
        Qdrant <-->|Hybrid 60% Cosine + 40% Lexical| MemAgent["Memory Agent (agents/memory_agent.py)"]
    end

    subgraph LYZR ["🤖 Lyzr Manager + Specialists (Real-Time SSE Stream)"]
        API -->|SSE Event Stream /api/process-stream| Stream["Live Agent Monitor Dashboard"]
        Stream --> A1["🗄️ Qdrant Memory Indexer"]
        Stream --> A2["🔎 Qdrant Retrieval"]
        Stream --> A3["🤖 Lyzr Manager + Specialist Agents"]
        Stream --> A4["🧩 Deterministic Output Validators"]
        Stream --> A5["📦 User-controlled Draft Outputs"]
    end

    subgraph OUTPUTS ["📦 Autonomous Deliverables & Integrations"]
        A2 --> Actions["Action Items + Kanban Dashboard"]
        A3 --> Dossier["Executive Briefing + Decisions + Risks"]
        A4 --> Email["1-Click Gmail & SMTP Follow-Up Email"]
        A4 --> Jira["Jira / GitHub API-Ready Tickets (OMI-1..6)"]
        A5 --> Calendar["Calendar Sync (.ics) + Google Meet Links"]
        MemAgent --> QnA["400ms Debounced Semantic Q&A Recall"]
    API -->|Grounded reasoning and Q&A| Studio["Lyzr Studio Cloud<br/>Manager Agent"]
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
   - Normalizes audio transcripts with speaker diarisation and fast accepted-job acknowledgement.

2. **Qdrant Cloud Vector Memory Layer:**
   - Collection: `omi_ambient_memory`.
   - Embeds each spoken utterance with FastEmbed `BAAI/bge-small-en-v1.5` into 384-dimensional vectors.
   - Hybrid scoring: 60% cosine similarity + 40% lexical stem overlap for dynamic relevance scores.
   - Privacy-first knowledge control via `POST /api/forget` and `DELETE /api/memory`.

3. **Lyzr Multi-Agent Reasoning Layer:**
   - Qdrant retrieval feeds a real Lyzr Manager/specialist reasoning step, followed by deterministic validators and user-controlled drafts.
   - Streams live execution events via Server-Sent Events (SSE) to the frontend dashboard.
   - `/ask` and the primary Track 1 pipeline use the shared Lyzr client for grounded context synthesis when configured.

4. **Model Context Protocol (MCP) Server:**
   - Standard JSON-RPC 2.0 stdio server (`mcp_server.py`) exposing ambient memory tools to Claude Desktop, Cursor, and other MCP clients.
