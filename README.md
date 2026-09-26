# 🎙️ OmiMind: Ambient Voice Memory & Autonomous Chief of Staff

[![CI Tests](https://github.com/masood-mashu/omimind-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/masood-mashu/omimind-agent/actions)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Omi Powered](https://img.shields.io/badge/Omi-Ambient%20Voice%20Capture-purple.svg)](https://omi.me)
[![Qdrant Cloud](https://img.shields.io/badge/Qdrant-Cloud%20Vector%20Memory-red.svg)](https://qdrant.tech)
[![Lyzr Multi-Agent](https://img.shields.io/badge/Lyzr-Multi--Agent%20Swarm-emerald.svg)](https://lyzr.ai)
[![Hackathon: Stop Prompting](https://img.shields.io/badge/HiDevs%20Hackathon-Track%201%3A%20Meeting%20Intelligence-orange.svg)](https://app.hidevs.xyz/hackathons/stop-prompting-solo-agents-hackathon-2026)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-omimind--agent.vercel.app-brightgreen.svg)](https://omimind-agent.vercel.app/)

> 🌐 **Live Demo:** [https://omimind-agent.vercel.app/](https://omimind-agent.vercel.app/)
> 📡 **Omi Webhook URL:** `POST https://omimind-agent.vercel.app/api/omi-webhook`

An autonomous, memory-backed chief of staff built for the **Omi AI Wearable**. OmiMind continuously ingests ambient meeting conversations, lectures, and voice memos — indexes every utterance into **Qdrant Cloud** for permanent semantic recall — and orchestrates a **Lyzr 4-Agent Swarm** that streams live execution events to the dashboard as it autonomously extracts commitments, synthesises executive dossiers, and dispatches Jira tickets and follow-up emails.

Built for **HiDevs × Lyzr × Qdrant × Omi Hackathon 2026 — Track 1: Meeting & Lecture Intelligence**.

---

## 🏛️ System Architecture

```mermaid
graph TD
    User([Omi Wearable / Browser Mic]) -->|Ambient Audio Stream| Omi[Omi Voice Webhook / WebSpeech Ingestion]
    Omi -->|Transcripts & Speaker Segments| Server[FastAPI v2.0 — backend/main.py]

    subgraph Qdrant Cloud Vector Memory Layer
        Server -->|128-Dim L2-Normalised Embeddings| Qdrant[(Qdrant Cloud: omi_ambient_memory\n19 Vectors · Cosine · Persistent)]
        Qdrant <-->|Hybrid 60% Cosine + 40% Lexical Search| MemAgent[Memory Agent — agents/memory_agent.py]
    end

    subgraph Lyzr 4-Agent Swarm — SSE Streaming Pipeline
        Server -->|SSE Event Stream| Stream[Live Agent Pipeline Dashboard]
        Stream --> A1[Agent 1: Qdrant Memory Indexer]
        Stream --> A2[Agent 2: Lyzr Action Extractor]
        Stream --> A3[Agent 3: Lyzr Executive Synthesizer]
        Stream --> A4[Agent 4: Lyzr Task Dispatcher]
    end

    subgraph Autonomous Deliverables
        A2 --> Actions[Action Items + Kanban]
        A3 --> Dossier[Executive Briefing + Decisions + Risks]
        A4 --> Email[Auto-Drafted Follow-Up Email]
        A4 --> Jira[Jira / GitHub API-Ready Tickets]
        MemAgent --> QnA[Live Semantic Q&A — 400ms Debounce]
    end
```

---

## ✨ What Makes This Different

| Feature | Detail |
|---|---|
| **Live SSE Agent Pipeline** | Watch all 4 Lyzr agents fire sequentially in real time — pulsing → ✓ per agent with count badges |
| **Qdrant Cloud Persistence** | Memory survives cold starts — 19 vectors pre-seeded, every new session adds permanently |
| **Real Omi Webhook** | `POST /api/omi-webhook` accepts native Omi `segments[]` payload or flat transcript |
| **Hybrid Semantic Search** | 60% cosine vector + 40% lexical stem overlap — dynamic scores per query (e.g. 72.7%, 53.8%) |
| **Live Search-as-you-type** | Query box fires on every keystroke with 400ms debounce — no button click needed |
| **Dynamic Executive Briefings** | Summary built from actual decisions/risks in the transcript, not boilerplate templates |
| **Calendar Deadline Detection** | Detects "by October 15th", "by end of week", "by next Friday" — not just day names |
| **3 Deployment Paths** | Local Python · Docker · Vercel serverless — all working |

---

## 🎯 The Three Core Pillars

### 1. 🎙️ Omi Wearable Ambient Voice Layer
- Native `POST /api/omi-webhook` endpoint accepts Omi's `{"segments": [{"speaker": "...", "text": "...", "start": 0.0}]}` payload directly from any Omi device.
- Also accepts flat transcript strings with auto speaker diarisation (regex `Name: text` detection).
- Browser microphone fallback via WebSpeech API for demo environments.
- 3 pre-set enterprise scenarios: Q4 Executive Budget Strategy, P0 SRE Outage Postmortem, Stanford CS229 Lecture.

### 2. ⚡ Qdrant Cloud Vector Memory Layer
- Every utterance ingested into `omi_ambient_memory` as a **128-dimensional L2-normalised dense vector** (stop-word filtered, subword 3-gram + bigram context).
- **Hybrid recall engine: 60% normalised cosine similarity + 40% lexical stem overlap** — produces per-query dynamic relevance scores with full speaker attribution.
- Hosted on **Qdrant Cloud** — persistent across all Vercel cold starts, pre-seeded with 19 demo vectors.
  > *"What temperature must vaccine containers maintain?"* → Leo (Firmware Architect): **72.7% match**
  > *"What did Samantha say about the FAA airspace waiver?"* → Samantha (Regulatory Compliance): **53.8% match**
- Live search-as-you-type: results update 400ms after every keystroke.

### 3. 🐝 Lyzr 4-Agent Swarm — Streamed via SSE
All 4 agents execute sequentially and stream their status live to the dashboard via **Server-Sent Events**:

| Agent | Role | Output |
|---|---|---|
| 🗄️ **MemoryAgent** | Indexes utterances into Qdrant Cloud | Vector count badge |
| 🎯 **ActionExtractor** | Detects commitments, assignees, deadlines (incl. calendar dates), urgency (P0/High) | Action items + Kanban |
| 🧠 **ExecutiveSynthesizer** | Builds dynamic briefing from actual transcript decisions and risks | Executive dossier |
| 📬 **TaskDispatcher** | Drafts follow-up email + Jira tickets (OMI-1…) labelled `OmiVoice`, `LyzrAgent`, `QdrantMemory` | Email + tickets |

---

## 🚀 Quickstart & Execution

### Option 1: Local Python Run
```bash
# 1. Clone repository
git clone https://github.com/masood-mashu/omimind-agent.git
cd omimind-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run automated tests
pytest tests/ -v

# 4. Start the application server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser to interact with the Live OmiMind Dashboard.

### Option 2: Docker Container (One-Command Run)
```bash
docker-compose up --build
```
Navigate to `http://localhost:8000`.

### Option 3: Vercel Cloud Serverless Deployment
```
1. Fork this repository → import on vercel.com/new
2. Add environment variables:
   QDRANT_URL     = https://your-cluster.cloud.qdrant.io
   QDRANT_API_KEY = your-api-key
3. Deploy → POST /api/seed to pre-populate demo data
```

### Omi Device Integration
Point your Omi app webhook to:
```
POST https://omimind-agent.vercel.app/api/omi-webhook
Content-Type: application/json

{
  "session_id": "optional-session-id",
  "segments": [
    {"speaker": "Alice", "text": "I will finalize the report by Friday.", "start": 12.5},
    {"speaker": "Bob",   "text": "Approved. Make it P0 priority.",          "start": 18.2}
  ]
}
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health + Qdrant Cloud stats |
| `GET` | `/api/meetings` | List all 3 pre-set demo meetings |
| `POST` | `/api/process-stream` | **SSE stream** — run full 4-agent pipeline on a preset meeting |
| `POST` | `/api/custom-voice-stream` | **SSE stream** — run full pipeline on custom transcript/voice |
| `POST` | `/api/omi-webhook` | Native Omi device webhook — accepts `segments[]` payload |
| `POST` | `/api/query` | Hybrid semantic memory search with relevance score |
| `POST` | `/api/seed` | Pre-seed all 3 demo meetings into Qdrant Cloud |
| `POST` | `/api/process` | Non-streaming fallback for preset meeting |

---

## 💼 Pre-Set Enterprise Scenarios

1. **Executive Q4 AI Infrastructure & Budget Review (`q4_strategy`)**
   — CFO Sarah, CTO David, VP Elena, Marcus align on $450k compute budget, Net-45 vendor terms, and database latency SLAs.

2. **P0 Incident Postmortem: Global Payment Gateway Outage (`sre_postmortem`)**
   — SRE Lead Alex and VP Vikram diagnose an expired TLS certificate, enforce automated renewal policies via Prometheus, and audit silenced webhook routes.

3. **Stanford CS229: FlashAttention & Scaling Laws (`cs_lecture`)**
   — Prof. Andrew explains SRAM tiling, O(N²) attention bottlenecks, and assigns Triton kernel Problem Set 4 deadline.

---

## 🧪 Automated Pytest Test Suite

```bash
$ pytest tests/ -v
tests/test_omimind.py::test_semantic_embedding_generator PASSED          [ 16%]
tests/test_omimind.py::test_qdrant_vector_memory PASSED                  [ 33%]
tests/test_omimind.py::test_lyzr_action_extractor PASSED                 [ 50%]
tests/test_omimind.py::test_executive_synthesizer PASSED                 [ 66%]
tests/test_omimind.py::test_task_dispatcher PASSED                       [ 83%]
tests/test_omimind.py::test_full_orchestration PASSED                    [100%]
============================== 6 passed in 2.32s ==============================
```

---

## 👥 Author & Hackathon Details
- **Author**: Mohammed Masood ([@masood-mashu](https://github.com/masood-mashu))
- **Hackathon**: [Stop Prompting. Code Solo Agents (2026)](https://app.hidevs.xyz/hackathons/stop-prompting-solo-agents-hackathon-2026)
- **Partners**: HiDevs, Lyzr AI, Qdrant, Omi
