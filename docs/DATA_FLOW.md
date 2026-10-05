# OmiMind Data Flow

This document details the data lifecycle from voice capture through vectorization, multi-agent reasoning, retrieval, and autonomous delivery.

```mermaid
flowchart TD
    Capture["🎙️ Omi Wearable / Microphone Audio"] --> Normalize["FastAPI Validation & Speaker Diarisation"]
    Normalize --> Session["Session ID + Speaker Attribution + Timestamps"]
    Session --> Embed["384-Dimensional FastEmbed Vectorization"]
    Embed --> Store[("Qdrant Cloud: `omi_ambient_memory`<br/>Persistent Vector Index")]

    Session --> Pipeline["Qdrant Retrieval → Lyzr Manager (SSE Stream)"]
    Pipeline --> Extract["Action Items & Kanban<br/>Assignees + Deadlines + Priority Tags"]
    Pipeline --> Brief["Executive Dossier<br/>Decisions + Technical Risks"]
    Pipeline --> Dispatch["Follow-Up Communications<br/>1-Click Gmail + Jira Tickets"]
    Pipeline --> Schedule["Calendar Events<br/>RFC 5545 .ics + Google Meet Links"]

    Store --> Search["Hybrid Semantic & Lexical Recall<br/>(60% Cosine + 40% Lexical Overlap)"]
    Search --> Answer["Grounded Answer with Speaker & Timestamp"]
    Answer --> Dashboard["Live Production Dashboard"]

    Extract --> Dashboard
    Brief --> Dashboard
    Dispatch --> Dashboard
    Schedule --> Dashboard

    Dashboard -->|1-Click Action| External["Gmail Compose / Calendar Sync / .ics Download"]

    Delete["Privacy-First `/api/forget` Endpoint"] -.->|GDPR Point or Session Purge| Store
    Ask["Official `/ask` Endpoint"] --> Search
    Ask --> Lyzr["Lyzr Studio Cloud Grounded Inference"]
    Lyzr --> OutputAnswer["Grounded Strategic Synthesis"]

    classDef input fill:#172554,stroke:#60a5fa,color:#dbeafe;
    classDef process fill:#064e3b,stroke:#34d399,color:#d1fae5;
    classDef sensitive fill:#7f1d1d,stroke:#f87171,color:#fee2e2;
    classDef output fill:#3f1d5b,stroke:#c084fc,color:#f3e8ff;
    class Capture,External input;
    class Normalize,Session,Embed,Pipeline,Extract,Brief,Dispatch,Schedule,Search,Answer,OutputAnswer process;
    class Store,Delete,Ask,Lyzr sensitive;
    class Dashboard output;
```

---

## Security & Privacy Lifecycle

- **Authentication:** Protected API endpoints are secured via `API_SECRET_KEY` header (`x-api-key` or `Bearer`).
- **Network Isolation:** CORS is strictly restricted to trusted origins via `ALLOWED_ORIGINS`.
- **Privacy-First Memory Purge:** Users retain full sovereignty over their ambient memory; `POST /api/forget` and `DELETE /api/memory` permanently delete vectors by session or point ID from Qdrant Cloud.
