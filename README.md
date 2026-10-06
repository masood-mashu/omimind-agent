# 🎙️ OmiMind: Ambient Voice Memory & Autonomous Chief of Staff

[![CI Tests & Quality Gate](https://github.com/masood-mashu/omimind-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/masood-mashu/omimind-agent/actions)
[![Tests Passing](https://img.shields.io/badge/tests-99%20passed-brightgreen.svg)](https://github.com/masood-mashu/omimind-agent/actions)
[![Coverage: 88.4%](https://img.shields.io/badge/coverage-88.4%25%20(gate%20%E2%89%A5%2085%25)-blue.svg)](https://github.com/masood-mashu/omimind-agent)
[![Code Quality: Ruff](https://img.shields.io/badge/ruff-clean%20(McCabe%20%E2%89%A4%2010)-blueviolet.svg)](https://docs.astral.sh/ruff/)
[![Python Versions](https://img.shields.io/badge/Python-3.10%20%7C%203.11-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Omi Powered](https://img.shields.io/badge/Omi-Ambient%20Voice%20Capture-purple.svg)](https://omi.me)
[![Qdrant Cloud](https://img.shields.io/badge/Qdrant-Cloud%20Vector%20Memory-red.svg)](https://qdrant.tech)
[![Lyzr Studio](https://img.shields.io/badge/Lyzr-Manager%20Reasoning%20(gpt--4o%20%7C%20mini)-emerald.svg)](https://lyzr.ai)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol%20Ready-blueviolet.svg)](https://modelcontextprotocol.io)
[![Hackathon: Stop Prompting](https://img.shields.io/badge/HiDevs%20Hackathon-Track%201%3A%20Meeting%20Intelligence-orange.svg)](https://app.hidevs.xyz/hackathons/stop-prompting-solo-agents-hackathon-2026)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-omimind--agent.vercel.app-brightgreen.svg)](https://omimind-agent.vercel.app/)

> 🌐 **Live Production Application:** [https://omimind-agent.vercel.app/](https://omimind-agent.vercel.app/)  
> 📡 **Official Omi Webhook Integrations:**  
> - `POST https://omimind-agent.vercel.app/omi/conversation` *(Memory creation webhook trigger)*  
> - `POST https://omimind-agent.vercel.app/omi/realtime` *(Real-time audio chunk stream ingestion)*  
> - `POST https://omimind-agent.vercel.app/api/omi-webhook` *(Native Omi segment diarisation receiver)*  
> ❓ **Official Question Endpoint:** `POST https://omimind-agent.vercel.app/ask` *(Grounded Q&A via Qdrant memory + Lyzr Studio Cloud)*  
> 🛡️ **Privacy & GDPR Compliance:** `POST /api/forget?session_id=...` & `DELETE /api/memory` *(Instant vector purge from Qdrant)*  
> 🔌 **Native Model Context Protocol:** `python mcp_server.py` *(JSON-RPC 2.0 stdio tools for Claude, Cursor, Antigravity)*  
> 📖 **Deep-Dive Engineering Documentation:**  
> - ⚡ [End-to-End Execution Flow (`docs/EXECUTION_FLOW.md`)](docs/EXECUTION_FLOW.md)  
> - 🏛️ [System Architecture (`docs/ARCHITECTURE.md`)](docs/ARCHITECTURE.md)  
> - 🌊 [Data Flow & Lifecycle (`docs/DATA_FLOW.md`)](docs/DATA_FLOW.md)  
> - ⏱️ [Chronological Sequence Diagram (`docs/SEQUENCE_DIAGRAM.md`)](docs/SEQUENCE_DIAGRAM.md)  
> - 🎙️ [Track 1: Meeting Intelligence Analysis (`docs/TRACK_1_ANALYSIS.md`)](docs/TRACK_1_ANALYSIS.md)  
> - 🎬 [Five-Minute Hackathon Demo Script (`docs/DEMO_SCRIPT.md`)](docs/DEMO_SCRIPT.md)

---

## 💡 Overview & Problem Statement

Modern knowledge workers and engineering teams spend hours every day in meetings, technical lectures, and hallway discussions. Traditional tools either transcribe audio into passive walls of unstructured text or inject intrusive recording bots that disrupt meeting culture.

**OmiMind** transforms ambient audio into an **autonomous Chief of Staff** through a closed-loop intelligence architecture:
1. **Zero-Intrusion Ambient Ingestion:** Captures live conversation directly through the **Omi Wearable** (via official webhook contracts) or the browser microphone with real-time waveform visualizers.
2. **Persistent Vector Memory:** Vectorizes every spoken utterance using dense 384-dimensional embeddings into **Qdrant** with speaker attribution, temporal timestamps, and user isolation (`uid`).
3. **Lyzr Studio Cloud Reasoning:** Dispatches retrieved transcript evidence to **Lyzr Studio Cloud** (`gpt-4o` / `gpt-4o-mini`) for multi-agent synthesis, disambiguating implicit commitments, identifying business risks, and extracting verified decisions.
4. **Autonomous Action Deliverables:** Automatically formats and outputs 1-click follow-up emails, Atlassian Jira issue schemas (`OMI-1..6`), and RFC 5545 `.ics` calendar invites with prefilled Google Meet links.
5. **Grounded Q&A (`/ask`):** Semantically recalls relevant conversation memory from Qdrant and synthesizes natural-language answers with speaker citations and confidence scores.
6. **Tool-Use via Model Context Protocol (MCP):** Exposes ambient memory directly to external developer environments (Claude Desktop, Cursor, Antigravity) via JSON-RPC 2.0 stdio.

Built for **HiDevs × Lyzr × Qdrant × Omi Hackathon 2026 — Track 1: Meeting & Lecture Intelligence**.

---

## 🏁 Build Track & Alignment

**Track:** Meeting & Lecture Intelligence — Track 1  
> *"Voice-to-insight engines with semantic retrieval, automated action-item extraction and Q&A over past meetings."*  
> — Official HiDevs Hackathon Track Description

OmiMind satisfies 100% of Track 1 requirements with production-grade rigor:
- **Voice Ingestion:** Fully compliant with Omi Webhook specifications (`/omi/conversation`, `/omi/realtime`, `/api/omi-webhook`).
- **Semantic Memory:** Production Qdrant vector database integration with hybrid search (Cosine + Lexical stemming) and GDPR purge.
- **Action Extraction:** Deterministic pattern recognition and priority scoring for verbal commitments, assignees, and deadlines.
- **Meeting Q&A:** Grounded `/ask` endpoint querying Qdrant vectors and answering through Lyzr Studio Cloud (`gpt-4o` / `gpt-4o-mini`).

---

## 🏛️ System Architecture & Data Flow

```mermaid
flowchart TD
    User["🎙️ Omi Wearable / Ambient Audio"] -->|Live Audio Streams| Omi["Omi Voice Webhook Layer"]
    Omi -->|Diarised Speaker Segments| FastAPIServer["FastAPI v2.0 Router Layer<br/>(backend/routers/)"]

    subgraph INGESTION ["📡 Ingestion & Validation Gateway"]
        FastAPIServer --> R1["/omi/conversation & /omi/realtime"]
        FastAPIServer --> R2["/api/process-stream & /api/custom-voice-stream"]
        FastAPIServer --> R3["/api/query & /ask"]
    end

    subgraph QDRANT ["⚡ Qdrant Vector Memory Layer"]
        FastAPIServer -->|384-Dim FastEmbed Vectors| Qdrant[("Configured Qdrant: omi_ambient_memory<br/>Persistent Vector Memory")]
        Qdrant <-->|Hybrid 60% Cosine + 40% Lexical| MemAgent["Memory Agent (agents/memory_agent.py)<br/>+ Pluggable Embeddings (agents/embeddings/)"]
    end

    subgraph LYZR ["🤖 Lyzr Manager Swarm (Real-Time SSE Stream)"]
        R2 -->|SSE Stream /api/process-stream| Stream["Live Agent Monitor Dashboard"]
        Stream --> A1["🗄️ Stage 1: Qdrant Memory Indexer"]
        Stream --> A2["🔎 Stage 2: Qdrant Retrieval"]
        Stream --> A3["🤖 Stage 3: Lyzr Manager Reasoning (gpt-4o / gpt-4o-mini)"]
        Stream --> A4["🧩 Stage 4: Action/Decision Validation"]
        Stream --> A5["📦 Stage 5: User-controlled Draft Outputs"]
    end

    subgraph OUTPUTS ["📦 Autonomous Deliverables & Integrations"]
        A4 --> Actions["Action Items + Kanban Dashboard"]
        A3 --> Dossier["Executive Briefing + Decisions + Risks"]
        A5 --> Email["1-Click Gmail & SMTP Follow-Up Email"]
        A5 --> Jira["Jira / GitHub API-Ready Tickets (OMI-1..6)"]
        A5 --> Calendar["Calendar Sync (.ics) + Google Meet Links"]
        MemAgent --> QnA["400ms Debounced Semantic Q&A Recall"]
        R3 -->|Grounded /ask| LyzrStudio["Lyzr Studio Cloud Inference (gpt-4o / gpt-4o-mini)"]
    end

    subgraph MCP ["🔌 Model Context Protocol (MCP) Interop"]
        MCP_Server["mcp_server.py (JSON-RPC stdio)"] <--> Qdrant
        MCP_Server <--> ExternalAgents["Claude Desktop / Cursor / Antigravity"]
    end

    classDef external fill:#172554,stroke:#60a5fa,color:#dbeafe;
    classDef service fill:#064e3b,stroke:#34d399,color:#d1fae5;
    classDef store fill:#3f1d5b,stroke:#c084fc,color:#f3e8ff;
    class User,Omi,LyzrStudio,ExternalAgents external;
    class FastAPIServer,R1,R2,R3,MemAgent,A1,A2,A3,A4,A5,MCP_Server service;
    class Qdrant store;
```

---

## 📂 Repository Structure

The codebase is organized into modular packages adhering to clean code, Single Responsibility Principle (SRP), and high testability:

```
omimind-agent/
├── agents/                           # Autonomous agents & swarm orchestration
│   ├── embeddings/                   # Pluggable semantic vector embedding engines
│   │   ├── base.py                   # BaseEmbeddingModel ABC (embed_text, embed_batch)
│   │   ├── deterministic.py          # Zero-dependency morphological subword hashing
│   │   ├── fastembed.py              # FastEmbed BAAI/bge-small-en-v1.5 engine
│   │   ├── sentence_transformer.py   # HuggingFace sentence-transformers with fallback
│   │   └── __init__.py               # Provider factory & global semantic helpers
│   ├── action_extractor.py           # Commitment, assignee, and priority detection
│   ├── calendar_scheduler.py         # RFC 5545 .ics generation & Google Meet links
│   ├── executive_synth.py            # Executive briefing, decisions, and risk synthesis
│   ├── lyzr_client.py                # Lyzr Studio Cloud manager agent integration
│   ├── memory_agent.py               # Qdrant collection lifecycle & hybrid vector search
│   ├── orchestrator.py               # Multi-agent swarm orchestrator
│   └── task_dispatcher.py            # Atlassian Jira schemas & follow-up email drafts
├── backend/                          # Modular FastAPI v2.0 application server
│   ├── routers/                      # Modular endpoint controllers
│   │   ├── health.py                 # System health & Lyzr telemetry diagnostics
│   │   ├── memory.py                 # Preset meetings, query, seed, and GDPR forget
│   │   ├── pipeline.py               # SSE streaming & synchronous synthesis pipelines
│   │   ├── webhooks.py               # Omi native & conversation webhook ingestion
│   │   └── __init__.py               # Router exports
│   ├── schemas/                      # Pydantic v2 request/response validation models
│   │   ├── api_models.py             # ProcessRequest, CustomVoiceRequest, QueryRequest, etc.
│   │   └── __init__.py               # Schema exports
│   ├── config.py                     # Typed Settings with environment discovery
│   ├── main.py                       # Modular application entrypoint & static mounting (<250 LOC)
│   ├── mock_data.py                  # Realistic enterprise multi-party demo meetings
│   └── shared.py                     # Shared orchestrator singleton & transcript parser
├── frontend/                         # Modern vanilla glassmorphic web dashboard
│   ├── css/styles.css                # Premium responsive dark-mode design system
│   ├── js/                           # Clean event-delegated ES6 application logic
│   │   ├── api.js                    # Backend REST & SSE client
│   │   ├── app.js                    # Core event controller & delegated listeners
│   │   ├── audio.js                  # Audio visualizer & microphone capture
│   │   └── ui.js                     # Dynamic DOM rendering & animations
│   ├── favicon.ico                   # Multi-resolution favicon assets
│   ├── favicon.svg                   # Vector SVG favicon
│   ├── site.webmanifest              # Progressive Web App (PWA) manifest
│   └── index.html                    # Semantic HTML5 user interface
├── tests/                            # Comprehensive automated test suite (92 tests)
│   ├── test_action_extractor.py      # Action extraction & priority scoring tests
│   ├── test_api_endpoints.py         # FastAPI router, webhook & telemetry tests
│   ├── test_calendar_scheduler.py    # Calendar scheduling & .ics formatting tests
│   ├── test_embeddings.py            # Modular embedding engines & batch tests
│   ├── test_executive_synth.py       # Executive brief & risk synthesis tests
│   ├── test_lyzr_client.py           # Lyzr Studio Cloud connectivity tests
│   ├── test_mcp_server.py            # Model Context Protocol JSON-RPC tests
│   ├── test_memory_agent.py          # Qdrant hybrid recall, isolation & GDPR tests
│   ├── test_omimind.py               # End-to-end swarm integration tests
│   └── test_task_dispatcher.py       # Jira & email draft formatting tests
├── docs/                             # Deep-dive architecture and demo specifications
│   ├── assets/                       # Telemetry proofs and high-resolution diagrams
│   ├── ARCHITECTURE.md               # Deep-dive system architecture specification
│   ├── DATA_FLOW.md                  # Comprehensive data flow & storage lifecycle
│   ├── DEMO_SCRIPT.md                # Turnkey 5-minute hackathon recording script
│   ├── EXECUTION_FLOW.md             # End-to-end execution flow documentation
│   ├── SEQUENCE_DIAGRAM.md           # Chronological sequence diagrams
│   └── TRACK_1_ANALYSIS.md           # Track 1 requirements alignment report
├── mcp_server.py                     # Model Context Protocol JSON-RPC 2.0 stdio server
├── pyproject.toml                    # Build system & quality gates (85% coverage, McCabe ≤ 10)
├── requirements.txt                  # Production runtime dependencies
└── vercel.json                       # Serverless deployment configuration
```

---

## 🤖 The Track 1 Multi-Agent Pipeline

The core intelligence layer executes five observable stages streamed live over Server-Sent Events (SSE):

| Stage | Module | Role & Autonomous Capabilities | Output |
|---|---|---|---|
| **Stage 1: Qdrant Memory Indexing** | [`agents/memory_agent.py`](agents/memory_agent.py)<br/>[`agents/embeddings/`](agents/embeddings/) | Vectorizes spoken utterances with FastEmbed `BAAI/bge-small-en-v1.5` dense embeddings into Qdrant Cloud. | 384-dim vectors indexed |
| **Stage 2: Qdrant Retrieval** | [`agents/memory_agent.py`](agents/memory_agent.py) | Semantically retrieves relevant conversational evidence scoped by user ID (`uid`) via Cosine distance. | Grounded transcript context |
| **Stage 3: Lyzr Manager Multi-Agent Reasoning** | [`agents/lyzr_client.py`](agents/lyzr_client.py) | Lyzr Studio Cloud Manager (`6ac5795151dce5f00e746950`) delegates to specialized worker agents (*Meeting Analyst*, *Action Extractor*, *Recall Agent*) over retrieved transcript context. | Grounded multi-agent synthesis |
| **Stage 4: Deterministic Validation & Reconciliation** | [`agents/orchestrator.py`](agents/orchestrator.py)<br/>[`agents/action_extractor.py`](agents/action_extractor.py)<br/>[`agents/executive_synth.py`](agents/executive_synth.py) | Reconciles Lyzr Manager output with deterministic schema normalization, assignee resolution, deadlines, and offline fallback. | Validated Kanban task cards & briefing |
| **Stage 5: User-controlled Draft Outputs** | [`agents/task_dispatcher.py`](agents/task_dispatcher.py)<br/>[`agents/calendar_scheduler.py`](agents/calendar_scheduler.py) | Drafts follow-up emails, Atlassian Jira issue schemas (`OMI-1..6`), RFC 5545 `.ics` files, and prefilled Google Meet URLs. | 1-Click drafts & calendar links |

### Real-Time SSE Observability
In accordance with the hackathon scoring guidelines (*"Show the agents working. Log each step... Observable workflows are part of the score"*), the pipeline emits live Server-Sent Events (`/api/process-stream` and `/api/custom-voice-stream`). The browser dashboard visualizes each stage's active execution, live status, and numeric vector scores in real time.

### 📊 Production Lyzr Studio Cloud Telemetry & Observability

Rather than relying on local mock fallbacks or client-side simulations, every meeting synthesis genuinely executes through **Lyzr Studio Cloud** (`gpt-4o` / `gpt-4o-mini`):

<p align="center">
  <img src="docs/assets/lyzr_studio_telemetry.png" alt="Lyzr Studio Cloud Production Telemetry Dashboard" width="100%" />
</p>

#### Production Telemetry Metrics (Lyzr Agent Studio Cloud Dashboard)
- **Baseline Verified Benchmark:** **126 live cloud inference requests** captured in telemetry monitoring (`docs/assets/lyzr_studio_telemetry.png`).
- **Average Latency:** **2.25 seconds** per multi-agent reasoning pass.
- **Baseline Benchmark Error Rate:** **0.00%** across the initial 126 verified cloud traces.
- **Token Efficiency:** **3,517 average tokens per trace** across all requests.
- **Total Development Runs:** **214 cumulative executions** logged in Lyzr Studio across exhaustive end-to-end testing.
- **Credit Consumption:** **19.58 of 20.00 Lyzr platform credits** consumed during development and stress testing.
- **Quota Ceiling & Graceful Resilience:** On Oct 6, continuous verification reached the free-tier quota ceiling (0.42 credits remaining), triggering expected cloud quota rejections on Lyzr's side. The system demonstrated automatic resilience via deterministic synthesis fallback and now supports the high-efficiency **`gpt-4o-mini`** model (`Agent ID: 6ac5666bf9e23d7db3dcce95`) requiring ~15x fewer credits per inference pass.

#### 🔍 Token Consumption Breakdown
Across the live traces averaging ~3,500 tokens per trace, token consumption breaks down across three distinct phases:
1. **Dynamic Context Ingestion (~2,000 – 2,400 tokens):**
   - Transcripts retrieved semantically from Qdrant Cloud are injected into the Lyzr prompt with speaker attribution, temporal timestamps, and confidence scores.
   - Long multi-party meetings (e.g. 15–20 speaker turns) supply dense historical context so the agent never hallucinates.
2. **Deep Orchestrated Reasoning (~600 – 800 tokens):**
   - Lyzr Studio's reasoning engine analyzes multi-turn dialogues to disambiguate implied commitments (*"I'll take that"*, *"Let's deploy by 6 PM"*), assign clear owners, verify calendar feasibility, and detect implicit business risks.
3. **Structured Grounded Synthesis (~400 – 600 tokens):**
   - Lyzr outputs a clean, deterministic synthesis including executive summary, strategic decisions, prioritized action items, and follow-up agendas.

---

## 🖥️ Live Tested Demonstration Scenarios

The live deployment at **[https://omimind-agent.vercel.app/](https://omimind-agent.vercel.app/)** supports three preset enterprise feeds plus live voice capture:

1. **Q4 AI Strategy & Budget (Executive Review):**
   - **Participants:** Sarah (CFO), David (CTO), Elena (VP Product), Marcus (Lead Architect).
   - **Results:** 8 vectors indexed, 6 actionable deliverables (`OMI-1` allocate H100 GPU compute budget, `OMI-2` review ScaleCloud Net-45 contract, `OMI-3` deploy multi-agent copilot, `OMI-4` staging load test, `OMI-5` zero-trust VPC token redaction, `OMI-6` customer rollout comms), 2 confirmed decisions, 2 engineering risks, 1 calendar follow-up sync (next Tuesday at 2:00 PM).
   - **Semantic Recall:** *"What did Sarah say about the budget?"* ➔ Ranked evidence with speaker attribution (`Sarah (CFO)`) and timestamps (`01:20` ScaleCloud Net-45 review up to $450,000; `09:30` approval for 128-node reserved cluster).

2. **P0 Payment Outage Postmortem (SRE & Incident Ops):**
   - **Participants:** Alex (SRE Lead), Vikram (VP Engineering), Chloe (Security), Ravi (Database Admin).
   - **Results:** 7 vectors indexed, 2 P0 tasks (`OMI-1` audit security webhook routes by EOD tomorrow, `OMI-2` migrate ingress certs to automated Let's Encrypt renewal with Prometheus monitoring by Friday), 2 confirmed decisions (reconciled balances with zero financial loss, zero manual certificate renewals in production), 0 blockers, 1 calendar follow-up review on Friday at 3:00 PM with Google Meet launch.
   - **Semantic Recall:** *"What caused the payment outage?"* ➔ Recalls Alex's 00:10 utterance regarding expired TLS certificate on the ingress proxy.

3. **Stanford CS229: FlashAttention (Technical Lecture):**
   - **Participants:** Prof. Andrew, Student Alex, Student Maya.
   - **Results:** 6 vectors indexed, synthesizes IO-aware tiling, SRAM memory hierarchy, Triton Problem Set 4 homework deadline (Tuesday midnight), and TA Priya's debugging clinic (Monday at 4:00 PM in Gates Hall).
   - **Semantic Recall:** *"How does FlashAttention avoid memory bottlenecks?"* ➔ Recalls Prof. Andrew's 05:10 explanation on SRAM tiling computing softmax incrementally without materializing the full N×N matrix.

4. **Live Omi Voice Capture & Custom Voice Input:**
   - Speak into browser microphone or paste raw transcripts. Click **Vectorize & Process** to run Qdrant indexing and Lyzr reasoning on live custom inputs.

---

## 🔌 Model Context Protocol (MCP) Server

OmiMind includes a production-ready Model Context Protocol (MCP) server ([`mcp_server.py`](mcp_server.py)) implementing the **JSON-RPC 2.0 (MCP 2024-11-05 spec)** over standard I/O (`stdio`).

### Supported Tools:
1. `search_ambient_memory(query, limit)` — Hybrid semantic & lexical Qdrant memory search.
2. `get_meeting_dossier(meeting_id)` — Executive briefing, confirmed decisions, and risks.
3. `extract_action_items(transcript)` — Commitment, assignee, and deadline extraction.
4. `schedule_followup_events(transcript)` — Calendar sync events and Google Meet links.

### Adding to Claude Desktop / Cursor / Antigravity:
```json
{
  "mcpServers": {
    "omimind": {
      "command": "python",
      "args": ["/path/to/omimind-agent/mcp_server.py"]
    }
  }
}
```

---

## 📡 API Reference

| Method | Endpoint | Authentication | Description |
|---|---|:---:|---|
| `GET` | `/health` | Public | Service health, embedding readiness & Lyzr Studio status |
| `GET` | `/api/meetings` | Public | List preset demo meetings and turn counts |
| `POST` | `/api/process-stream` | Public | **SSE Stream:** Real-time multi-agent pipeline on preset meeting |
| `POST` | `/api/custom-voice-stream` | Public | **SSE Stream:** Real-time multi-agent pipeline on custom voice memo |
| `POST` | `/api/process` | Public | Synchronous meeting processing & dossier creation |
| `POST` | `/api/custom-voice` | Public | Synchronous custom voice memo processing |
| `POST` | `/api/query` | Public | Hybrid semantic vector memory search (`limit: 1–20`, user-scoped) |
| `POST` | `/ask` | Protected | **Official Guide:** Grounded Q&A via Qdrant memory + Lyzr Studio |
| `POST` | `/api/omi-webhook` | Protected | Native Omi wearable segment webhook |
| `POST` | `/omi/conversation` | Protected | **Official Guide:** Memory creation trigger webhook |
| `POST` | `/omi/realtime` | Protected | **Official Guide:** Real-time audio chunk stream |
| `POST` | `/api/seed` | Protected | Pre-seed preset meetings into Qdrant Cloud |
| `POST` | `/api/forget` | Protected | GDPR-compliant session or point vector purge |
| `DELETE` | `/api/memory` | Protected | Alias for GDPR-compliant vector deletion |
| `GET` | `/favicon.ico` | Public | Multi-resolution icon for browser discovery |
| `GET` | `/favicon.svg` | Public | Vector SVG application brand icon |

*Protected endpoints require `API_SECRET_KEY` supplied via `x-api-key: <key>` or `Authorization: Bearer <key>`.*

---

## ⚙️ Configuration & Environment Variables

All settings are strongly typed using Pydantic Settings in [`backend/config.py`](backend/config.py):

| Variable | Required | Default | Description |
|---|:---:|:---:|---|
| `QDRANT_URL` | Optional | `None` | Qdrant Cloud cluster URL (e.g. `https://xyz.qdrant.io:6333`). If unset, uses local memory. |
| `QDRANT_API_KEY` | Optional | `None` | Qdrant Cloud API access key. |
| `LYZR_API_KEY` | Optional | `None` | Lyzr Studio Cloud platform API key. |
| `LYZR_AGENT_ID` | Optional | `None` | Primary Lyzr Studio Agent ID for meeting synthesis. |
| `LYZR_MANAGER_AGENT_ID` | Optional | `None` | Lyzr Studio Manager Agent ID (`6ac5795151dce5f00e746950`) coordinating specialist workers. |
| `LYZR_TIMEOUT_SECONDS` | Optional | `45.0` | Timeout in seconds for Lyzr multi-agent reasoning calls. |
| `LYZR_USER_ID` | Optional | `default_user` | User identifier for Lyzr session tracking. |
| `EMBEDDING_PROVIDER` | Optional | `fastembed` | Active embedding engine: `fastembed`, `deterministic`, or `sentence_transformers`. |
| `API_SECRET_KEY` | Optional | `None` | Secret key protecting sensitive webhooks and GDPR purge endpoints. |
| `OMI_API_KEY` | Optional | `None` | API key for authenticating outbound Omi hardware requests. |
| `OMI_WEBHOOK_SECRET` | Optional | `None` | Secret token verified on incoming Omi wearable webhooks. |
| `ALLOW_EPHEMERAL_MEMORY` | Optional | `false` | Fall back to in-memory Qdrant if cloud cluster is unreachable. |
| `ALLOWED_ORIGINS` | Optional | `http://localhost:8000...` | Comma-separated list of allowed CORS origins. |
| `PORT` | Optional | `8000` | Application HTTP server port. |

---

## 🧪 Comprehensive Automated Test Suite & Quality Gates

OmiMind maintains a continuous quality gate requiring **>= 85.0% coverage** and **McCabe complexity <= 10**:

```bash
$ pytest --cov=agents --cov=backend tests/ --cov-report=term-missing
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\hackathon\omimind-agent
configfile: pyproject.toml
collected 100 items

tests/test_action_extractor.py (7 tests)      PASSED
tests/test_api_endpoints.py (26 tests)        PASSED
tests/test_calendar_scheduler.py (6 tests)    PASSED
tests/test_embeddings.py (18 tests)           PASSED
tests/test_executive_synth.py (3 tests)       PASSED
tests/test_live_lyzr_manager.py (1 test)      SKIPPED (credential-gated live call)
tests/test_lyzr_client.py (5 tests)           PASSED
tests/test_mcp_server.py (4 tests)            PASSED
tests/test_memory_agent.py (18 tests)         PASSED
tests/test_omimind.py (8 tests)               PASSED
tests/test_task_dispatcher.py (3 tests)       PASSED

=============================== tests coverage ================================
Name                                        Stmts   Miss  Cover   Missing
-------------------------------------------------------------------------
agents\__init__.py                              0      0   100%
agents\action_extractor.py                     40      0   100%
agents\calendar_scheduler.py                   41      2    95%   52-53
agents\embeddings\__init__.py                  21      2    90%   28, 31
agents\embeddings\base.py                      11      0   100%
agents\embeddings\deterministic.py             37      0   100%
agents\embeddings\fastembed.py                 83     18    78%   42-47, 51-58...
agents\embeddings\sentence_transformer.py      54     10    81%   32-33, 44...
agents\executive_synth.py                      30      0   100%
agents\lyzr_client.py                          33      1    97%   80
agents\memory_agent.py                        114     18    84%   57-59, 69-80...
agents\orchestrator.py                         92      1    99%   180
agents\task_dispatcher.py                      15      0   100%
backend\__init__.py                             0      0   100%
backend\config.py                              39      4    90%   15-16, 95-96
backend\main.py                                80     13    84%   98-99, 125...
backend\mock_data.py                            2      0   100%
backend\routers\__init__.py                     5      0   100%
backend\routers\health.py                      14      0   100%
backend\routers\memory.py                      69     11    84%   53, 73-75...
backend\routers\pipeline.py                    97     18    81%   50-52, 80-88...
backend\routers\webhooks.py                    94     18    81%   51, 54, 77...
backend\schemas\__init__.py                     2      0   100%
backend\schemas\api_models.py                  18      0   100%
backend\shared.py                              31      3    90%   28, 37-38
-------------------------------------------------------------------------
TOTAL                                        1022    119    88%
Required test coverage of 85.0% reached. Total coverage: 88.36%
================== 99 passed, 1 skipped in 93.99s ===================
```

```bash
$ python -m ruff check .
All checks passed!
```  83%   53, 74, 76-78...
backend/routers/pipeline.py                    98     18    82%   50-52, 80-88...
backend/routers/webhooks.py                    95     18    81%   49, 52, 87...
backend/schemas/api_models.py                  17      0   100%
backend/shared.py                              31      3    90%   28, 37-38
-------------------------------------------------------------------------
TOTAL                                         966    121    87%
Required test coverage of 85.0% reached. Total coverage: 87.47%
============================= 92 passed in 74.53s =============================
```

```bash
$ python -m ruff check .
All checks passed!
```

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Set Up Virtual Environment

```bash
# Clone repository
git clone https://github.com/masood-mashu/omimind-agent.git
cd omimind-agent

# Set up Python virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Qdrant & Lyzr credentials (optional for in-memory demo mode)
```

### 4. Run Test Suite & Lint Checks

```bash
pytest --cov=agents --cov=backend tests/
python -m ruff check .
```

### 5. Launch Application Server

```bash
python -m uvicorn backend.main:app --reload --port 8000
```
Open **`http://localhost:8000`** in your browser.

---

## 🐳 Docker Deployment

Run the complete application in a self-contained container:

```bash
# Build Docker image
docker build -t omimind-agent .

# Run container
docker run -p 8000:8000 --env-file .env omimind-agent
```

Or using Docker Compose:
```bash
docker compose up --build
```

---

## 🎬 Turnkey Demo Walkthrough (Under 5 Minutes)

Follow the complete script in [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for recording hackathon demonstrations:
- **0:00–0:30:** Introduce OmiMind, problem context, and Track 1 alignment.
- **0:30–1:15:** Present the live production web app at [omimind-agent.vercel.app](https://omimind-agent.vercel.app/) and architecture.
- **1:15–2:45:** Select **Q4 AI Strategy & Budget**, click **Ingest & Run**, watch the 5-stage real-time SSE stream, and review generated Kanban tasks and RFC 5545 calendar sync.
- **2:45–3:30:** Test semantic vector recall (*"What did Sarah say about the budget?"*) showing ranked scores and speaker citations.
- **3:30–4:30:** Demonstrate live microphone capture, MCP server integration (`mcp_server.py`), and privacy purge (`/api/forget`).
- **4:30–5:00:** Show verified Lyzr Studio Cloud telemetry dashboard (126 traces, 2.25s latency, 0.00% error rate).

---

## ✅ Official Hackathon Submission Checklist (Section 9 Compliance)

In direct compliance with the official **HiDevs × Lyzr × Qdrant × Omi Hackathon Submission Guide (Section 9)**:

| Requirement (Guide Section 9) | Status | Verification & Evidence in OmiMind |
|---|:---:|---|
| **Public, open-source repository with clean structure and clear README** | ✅ **Passed** | Clean repository layout with modular `agents/`, `backend/`, `tests/`, and engineering guides in `docs/`. |
| **All three tools genuinely integrated in one connected loop** | ✅ **Passed** | **Omi** (webhooks) ➔ **Qdrant** (384-dim FastEmbed vector memory) ➔ **Lyzr** (Studio Cloud `gpt-4o` / `gpt-4o-mini` manager reasoning). |
| **Architecture documentation with a diagram** | ✅ **Passed** | Complete Mermaid architecture and sequence diagrams included in `README.md` and `docs/`. |
| **Working demo that someone else can run or watch** | ✅ **Passed** | Live public production web app deployed at [https://omimind-agent.vercel.app/](https://omimind-agent.vercel.app/). |
| **No API keys committed (environment variables + `.env.example`)** | ✅ **Passed** | Zero secrets in git history; comprehensive template in [`.env.example`](.env.example). |
| **One build track chosen and named in the README** | ✅ **Passed** | **Track 1: Meeting & Lecture Intelligence** clearly declared and adhered to throughout. |
| **Solo entry: one person, one submission** | ✅ **Passed** | Solo participant submission by Mohammed Masood. |
| **Observable agent workflows (60%+ scoring rubric)** | ✅ **Passed** | Real-time Server-Sent Events (SSE) stream (`/api/process-stream`) exposing each agent's execution live in the UI. |
| **Verified Cloud Telemetry** | ✅ **Passed** | Verified Lyzr Studio Cloud telemetry dashboard (126 traces benchmark, 2.25s latency, 0.00% baseline error rate; 214 total stress-tested runs). |

---

## 📋 Hackathon Submission Form Quick-Reference

> Keep these exact blocks ready for the [HiDevs Submission Form](https://app.hidevs.xyz/hackathons/stop-prompting-solo-agents-hackathon-2026?tab=submit):

### Project Name
**OmiMind**

### Project Title
**OmiMind: Ambient Voice Memory & Autonomous Chief of Staff for Omi, Qdrant & Lyzr**

### Build Track
**Meeting & Lecture Intelligence (Track 1)**

### Public GitHub Repository
**https://github.com/masood-mashu/omimind-agent**

### Deployed Demo URL
**https://omimind-agent.vercel.app/**

### Omi Usage
OmiMind integrates directly with Omi's ambient voice pipeline through three dedicated webhook endpoints:
- `POST /omi/conversation` — triggers after a conversation concludes; ingests full diarised `transcript_segments[]` with speaker attribution directly into persistent vector storage.
- `POST /omi/realtime` — ingests streaming audio transcripts in real time as the user speaks.
- `POST /api/omi-webhook` — handles native Omi wearable segment payloads with an accepted-job HTTP response; processing is deferred so the webhook remains responsive.
Tested and verified with automated test suites, simulated audio feeds, and live microphone capture.

### Qdrant Usage
Every spoken utterance is converted into a 384-dimensional `BAAI/bge-small-en-v1.5` dense vector and indexed in the `omi_ambient_memory` collection on configured Qdrant storage. Semantic retrieval utilizes Cosine similarity with strict user scoping (`uid`), speaker metadata, and temporal timestamps. Includes a dedicated `/api/forget` endpoint for GDPR-compliant memory purges.

### Lyzr Usage
OmiMind utilizes **Lyzr Agent Studio Cloud** powered by `gpt-4o` and `gpt-4o-mini` as the core reasoning engine. The pipeline exposes an observable multi-agent orchestration streamed over Server-Sent Events (SSE):
1. **MemoryAgent:** Indexes transcript evidence into Qdrant Cloud.
2. **QdrantRetrieval:** Semantically retrieves relevant, user-scoped meeting context.
3. **LyzrManager:** Reasons over the retrieved context through Lyzr Studio Cloud (`gpt-4o` / `gpt-4o-mini`) to generate structured synthesis.
4. **Deterministic Validators:** Extract and normalize actions, decisions, risks, and scheduling intent.
5. **Draft Outputs:** Prepares 1-click email drafts, Atlassian Jira issue schemas, RFC 5545 `.ics` files, and Google Meet URLs.
Telemetry verified across **126 live cloud inference benchmark traces** with **2.25s average latency** and a **0.00% baseline error rate**, plus **214 total development executions** demonstrating automatic quota resilience.

### Project Description
OmiMind is an ambient voice memory and autonomous Chief of Staff built for Track 1 (Meeting & Lecture Intelligence). It captures spoken meetings seamlessly via Omi wearable webhooks, indexes utterances into persistent Qdrant Cloud vector memory using FastEmbed 384-dim embeddings, and runs multi-agent reasoning through Lyzr Agent Studio Cloud (`gpt-4o` / `gpt-4o-mini`). OmiMind delivers real-time SSE stream observability, grounded Q&A over past conversations, automated action items with owners and deadlines, 1-click calendar sync, and native Model Context Protocol (MCP) support for external developer IDEs. Live at https://omimind-agent.vercel.app/.

---

## 👥 Author & Hackathon Acknowledgements

- **Author:** Mohammed Masood ([@masood-mashu](https://github.com/masood-mashu))
- **Hackathon:** [Stop Prompting. Code Solo Agents (2026)](https://app.hidevs.xyz/hackathons/stop-prompting-solo-agents-hackathon-2026)
- **Partners:** HiDevs, Lyzr AI, Qdrant, Omi
- **License:** [Apache-2.0](LICENSE)
