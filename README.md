# 🎙️ OMIMIND: Ambient Voice Memory & Meeting Assistant Demo

[![CI Tests & Quality Gate](https://github.com/masood-mashu/omimind-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/masood-mashu/omimind-agent/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Track 1](https://img.shields.io/badge/Track%201-Meeting%20%26%20Lecture%20Intelligence-purple.svg)](https://app.hidevs.xyz/hackathons/stop-prompting-solo-agents-hackathon-2026)
[![Qdrant Cloud](https://img.shields.io/badge/Qdrant-Cloud%20Vector%20Memory-red.svg)](https://qdrant.tech/)
[![Lyzr Studio](https://img.shields.io/badge/Lyzr-Agent%20Studio%20Swarm-blueviolet.svg)](https://www.lyzr.ai/)
[![Stitch UI](https://img.shields.io/badge/Google%20Stitch-Obsidian%20Telemetry%20Design-cyan.svg)](https://stitch.withgoogle.com/)

> **HiDevs × Lyzr × Qdrant × Omi Hackathon Entry**  
> **Track 1:** Meeting & Lecture Intelligence  
> **Live Web Application:** [https://omimind-agent.vercel.app/](https://omimind-agent.vercel.app/)  
> **Author:** Mohammed Masood ([@masood-mashu](https://github.com/masood-mashu))

---

## 💡 What is OMIMIND?

In fast-paced engineering teams, boardrooms, and academic lectures, critical decisions, action items, and technical agreements are spoken aloud and immediately lost. Manual note-taking distracts from active participation, and traditional recording tools generate static transcripts that sit unread.

**OMIMIND** bridges the gap between spoken conversation and autonomous execution. By uniting **Omi Wearable voice capture**, **Qdrant Cloud vector memory**, and **Lyzr Agent Studio swarms**, OMIMIND functions as an ambient, privacy-first **Chief of Staff**:

1. **Ambient Ingestion & Direct Input:** Captures ambient speech continuously from Omi device webhooks or in-browser microphone, with dedicated direct typing inputs and 1-click test templates for zero-friction evaluation.
2. **Instant Vectorization:** Indexes each utterance as a 384-dimensional dense vector into configured Qdrant storage using the embedding provider selected for the deployment.
3. **Multi-Agent Reasoning:** Coordinates Lyzr Studio Cloud swarms (`gpt-4o` / `gpt-4o-mini`) to synthesize executive briefings and ground queries against past conversations.
4. **Deterministic Validation & Action Dispatch:** Extracts concrete commitments, priority tags, assignees, and deadlines, formatting them into user-controlled follow-up emails, Jira ticket backlogs, and 1-click Google Calendar invites.
5. **Observable Real-Time Streaming:** Streams agent execution stages live over Server-Sent Events (SSE) to an accessible, responsive dashboard.
6. **Demo Interface:** A meeting workflow with clearly labeled illustrative wearable telemetry. No live device metrics are shown unless an authenticated device supplies them.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Ingress ["1. Ingress & Security Layer"]
        Omi["🎙️ Omi Wearable / Browser Mic"]
        AuthGate["🛡️ FastAPI Ingress & Security<br/>(backend/auth.py)"]
        Omi -->|Webhooks / Audio Stream| AuthGate
        AuthGate -.->|Replay & Signature Check<br/>Constant-Time Auth| Validated["Validated Utterances"]
    end

    subgraph MemoryLayer ["2. Ambient Vector Memory Layer"]
        Validated --> MemoryAgent["🧠 MemoryAgent<br/>(agents/memory_agent.py)"]
        MemoryAgent -->|Dense 384d Embeddings| Embeddings["⚡ Configured Embedding Provider<br/>(FastEmbed or deterministic)"]
        Embeddings --> Qdrant[("🗄️ Qdrant<br/>(omi_ambient_memory)")]
    end

    subgraph ReasoningLayer ["3. Multi-Agent Reasoning Layer"]
        Qdrant -->|User-Scoped Context| Orchestrator["⚙️ OrchestratorCoordinator<br/>(agents/orchestrator.py)"]
        Orchestrator --> Synth["📊 ExecutiveSynthesizer<br/>(Decisions, Risks & Summary)"]
        Orchestrator --> LyzrSwarm["🤖 Lyzr Studio Swarm<br/>(Manager + Recall + Analyst)"]
        LyzrSwarm -.->|Offline / Fallback| LocalEngine["Deterministic Local Engine<br/>(Transparent Attribution)"]
    end

    subgraph DispatchLayer ["4. Task & Calendar Dispatcher"]
        Synth & LyzrSwarm & LocalEngine --> Dispatcher["📋 TaskDispatcher & Scheduler<br/>(agents/task_dispatcher.py)"]
        Dispatcher --> EmailDraft["✉️ Markdown Email Draft"]
        Dispatcher --> JiraTickets["🎯 Structured Jira Backlog"]
        Dispatcher --> CalendarURL["📅 1-Click Google Calendar URLs"]
    end

    subgraph PresentationLayer ["5. Observable Dashboard"]
        Orchestrator -->|Live SSE Stream<br/>/api/process-stream| UI["🖥️ Vanilla ES Modules UI<br/>(Real-Time Agent Radar & Cards)"]
        EmailDraft & JiraTickets & CalendarURL --> UI
    end
```

---

## ⚡ The Four-Stage Agent Execution Pipeline

| Stage | Agent / Module | Responsibility | Output Produced |
| :---: | :--- | :--- | :--- |
| **1** | **MemoryAgent** | Generates 384-dimensional embeddings and indexes transcript segments in Qdrant under the authenticated workspace owner. | Vectors committed to Qdrant collection with hybrid lexical tokens. |
| **2** | **ExecutiveSynthesizer** | Analyzes conversational dynamics, extracting key decisions, discussion topics, and operational blockers. | Executive briefing and structured decision records. |
| **3** | **Lyzr Reasoning Swarm** | Gathers historical cross-meeting context from Qdrant and prompts the Lyzr Manager Agent asynchronously with bounded retries and timeout protection. | Context-grounded synthesis; honest fallback attribution if offline. |
| **4** | **TaskDispatcher & Scheduler** | Formats action items into ready-to-file Jira tickets, drafts follow-up emails, and generates 1-click Google Calendar URLs for detected dates. | Complete meeting dossier ready for user review and 1-click execution. |

---

## 🔒 Multi-User Workspace Security

OMIMIND is a public multi-user application. Each person creates a Supabase Auth account and receives an isolated workspace:

- **Verified identity:** FastAPI derives the owner from the verified Supabase JWT `sub` claim. Caller-supplied `uid` values never select a tenant.
- **Row-level isolation:** Supabase RLS protects meetings, runs, agent events, action items, Omi connections, and webhook records. Qdrant searches and deletes always include the authenticated owner filter.
- **Header-Only Authentication:** Sensitive endpoints require `Authorization: Bearer <token>` or `X-API-Key: <token>`. Credentials in query parameters (`?api_key=`, `?token=`) are rejected with `HTTP 401`.
- **Constant-Time Verification:** All secret comparisons utilize `hmac.compare_digest` to prevent timing attacks.
- **Omi Webhook Protection:** Dedicated tokenized connection routes authenticate with a high-entropy per-connection token in the path. The legacy signed webhook routes require configured credentials and a fresh timestamp within five minutes, with signatures covering the timestamp and raw request body.
- **Shared Durable Idempotency:** Supabase Postgres serializes event claims across app instances, detects changed payloads for reused event IDs, and retains completed IDs for 72 hours.
- **Strict Input Validation & Abuse Resistance:** Request payloads are capped at 1MB (`HTTP 413`), transcripts at 50,000 characters, queries at 1,000 characters, and segment batches at 500 items, rejecting malformed types or invalid timestamps (`HTTP 422`).
- **Ownership Enforcement on Purge:** Both `/api/forget` and `DELETE /api/memory` verify point and session ownership, returning `HTTP 403 Forbidden` if a caller attempts to delete another user's data.
- **XSS-Safe Frontend:** All dynamic participant lists and transcript strings are sanitized before rendering into the DOM.

---

## 🌐 API Reference

### Public Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health, version, embedding readiness, and Qdrant cluster statistics |
| `GET` | `/` | Application dashboard shell |
| `GET` | `/favicon.ico` | Browser application icon |

### Protected Application Endpoints
*Require `Authorization: Bearer <Supabase access token>` header.*

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/meetings` | List available pre-set demo meeting scenarios |
| `GET` | `/api/meetings/{id}` | Retrieve meeting lines, metadata, and cached dossier |
| `GET` | `/api/memories` | List recent user-scoped memories from Qdrant |
| `GET` | `/api/actions` | List all extracted action items for the authenticated user |
| `POST` | `/api/query` | Hybrid semantic vector search scoped to authenticated UID |
| `POST` | `/api/ask` | Grounded conversational Q&A over retrieved memory context |
| `POST` | `/ask` | Official Hackathon Q&A endpoint |
| `POST` | `/api/process` | Process a meeting session synchronously |
| `POST` | `/api/process-stream` | Real-time SSE streaming pipeline for live UI animations |
| `POST` | `/api/custom-voice` | Ingest and process custom transcript text synchronously |
| `POST` | `/api/custom-voice-stream` | Ingest and process custom transcript text over SSE |
| `POST` | `/api/seed` | Pre-seed demo meetings into Qdrant under authenticated UID |
| `POST` | `/api/forget` | Delete memories by `session_id` with ownership enforcement |
| `DELETE` | `/api/memory` | Delete a specific memory point by `point_id` with ownership enforcement |
| `GET` | `/api/runs/{run_id}/events` | Inspect the authenticated user's persisted agent trace |
| `POST` | `/api/omi/connections/pair/start` | Start a short-lived Omi pairing code |
| `POST` | `/api/omi/connections/pair/complete` | Link a verified Omi identity to the workspace |
| `GET` | `/api/omi/connections` | List the user's Omi connections |
| `POST` | `/api/omi/connections/{id}/rotate` | Rotate one connection webhook token |
| `DELETE` | `/api/omi/connections/{id}` | Revoke one Omi connection |
| `POST` | `/omi/pairing/proof/{connection_token}` | Signed one-time Omi callback for mobile pairing |
| `DELETE` | `/api/account` | Delete the account's Postgres, Qdrant, run, and Omi data |

### Dedicated Omi Webhook Endpoints
*Connection-token routes authenticate with the per-connection token in the URL. The legacy signed routes require `X-Omi-Timestamp` (or `X-Timestamp`) within five minutes and `X-Omi-Signature` over the timestamp and raw body.*

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/omi/conversation/{connection_token}` | Completed Omi conversation for a paired connection |
| `POST` | `/omi/realtime/{connection_token}` | Real-time streaming segment webhook for a paired connection |

---

## 🤖 Model Context Protocol (MCP) Server

OMIMIND includes a native **Model Context Protocol (MCP)** server ([mcp_server.py](mcp_server.py)) operating over standard input/output (stdio JSON-RPC 2.0). It requires `OMIMIND_MCP_UID` to be set to one Supabase Auth user ID and filters memory to that workspace. Set that variable before starting the server:

```bash
python mcp_server.py
```

### Claude Desktop / Cursor Configuration

Add this configuration to your `claude_desktop_config.json` or Cursor MCP settings:

```json
{
  "mcpServers": {
    "omimind": {
      "command": "python",
      "args": ["<path-to-repository>/mcp_server.py"],
      "env": {
        "OMIMIND_MCP_UID": "your-supabase-auth-user-id",
        "QDRANT_URL": "https://your-cluster.qdrant.io:6333",
        "QDRANT_API_KEY": "your-qdrant-api-key"
      }
    }
  }
}
```

### Exposed MCP Tools
- `search_ambient_memory`: Hybrid semantic vector search across ambient meeting memories.
- `get_meeting_dossier`: Retrieves executive summaries, decisions, risks, and calendar links for a session.
- `extract_action_items`: Runs multi-agent commitment extraction on raw transcript text.
- `schedule_followup_events`: Detects proposed follow-up meetings and outputs Google Calendar and iCal links.

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- **Python**: `>= 3.10` (tested on 3.10 and 3.11)
- **Qdrant**: Local instance or [Qdrant Cloud](https://cloud.qdrant.io/) (free cluster supported)
- **Lyzr API Key**: (Optional — local deterministic synthesis works seamlessly without it)

### 2. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/masood-mashu/omimind-agent.git
cd omimind-agent

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Upgrade pip & install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Secrets

```bash
# Copy example configuration
cp .env.example .env          # macOS / Linux
# copy .env.example .env      # Windows PowerShell
```

Configure your `.env` file:
```dotenv
ENVIRONMENT=development
DEPLOYMENT_MODE=multi_user
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-supabase-publishable-key
SUPABASE_SERVICE_ROLE_KEY=server-only-service-role-key
DATABASE_URL=postgresql://user:password@host:5432/postgres?sslmode=require
OMI_WEBHOOK_SECRET=your-omi-webhook-secret

# Qdrant Configuration
QDRANT_URL=https://your-cluster-id.us-east4-0.gcp.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key
COLLECTION_NAME=omi_ambient_memory

# Lyzr Configuration (server-side only)
LYZR_API_KEY=your-lyzr-api-key
LYZR_MANAGER_AGENT_ID=your-manager-agent-id
LYZR_MEMORY_RECALL_AGENT_ID=your-memory-recall-agent-id
LYZR_MEETING_ANALYST_AGENT_ID=your-meeting-analyst-agent-id
LYZR_ACTION_EXTRACTOR_AGENT_ID=your-action-extractor-agent-id
LYZR_FOLLOWUP_PLANNER_AGENT_ID=your-followup-planner-agent-id
```

> Production startup fails unless Supabase Auth, Postgres, Qdrant, Lyzr, and Omi webhook configuration is present. Webhook event storage never uses `/tmp`.

Apply every file in `supabase/migrations/` to the configured Supabase project before starting production. The service validates the durable webhook and workspace schema at startup and refuses to run against an incomplete database.

### 4. Run the Application

```bash
# Start server with auto-reload
python -m uvicorn app:app --reload --port 8000

# Or run directly via Python entrypoint
python app.py
```
Open your browser at **`http://localhost:8000`** (or access the live cloud deployment at **`https://omimind-agent.vercel.app/`**).

---

## 🐳 Docker Deployment

Run OMIMIND inside a containerized environment:

```bash
# Build Docker image
docker build -t omimind-agent .

# Run container with environment configuration
docker run -p 8000:8000 --env-file .env omimind-agent
```

Or run via Docker Compose:
```bash
docker compose up --build
```

---

## 🧪 Testing & Quality Gates

OMIMIND includes automated checks for semantic recall, processing pipelines, input bounds, multi-user isolation, and webhook security:

```bash
# Run Ruff lint & formatting checks
python -m ruff check .

# Run the full pytest suite with the CI coverage gate (>=80%)
pytest --cov=agents --cov=backend tests/ --cov-report=term-missing --cov-fail-under=80
```

See the [multi-user release test matrix](docs/RELEASE_TEST_MATRIX.md) for the automated and staging-only checks required before release.

---

## 📂 Repository Layout

```text
omimind-agent/
├── agents/
│   ├── embeddings/          # FastEmbed (384d), deterministic, & transformer embeddings
│   ├── action_extractor.py  # Commitment, assignee, priority & deadline extraction
│   ├── calendar_scheduler.py# Temporal extraction & 1-click Google Calendar URLs
│   ├── executive_synth.py   # Executive briefings, key decisions & risk analysis
│   ├── lyzr_client.py       # Async non-blocking Lyzr Studio client with retries
│   ├── memory_agent.py      # Non-destructive Qdrant vector memory lifecycle, search & purges
│   ├── orchestrator.py      # Central multi-agent pipeline coordinator
│   └── task_dispatcher.py   # Markdown email drafts & structured Jira backlog items
├── backend/
│   ├── auth.py              # Constant-time auth, shared demo sessions, and webhook verification
│   ├── config.py            # Typed settings with fail-fast production startup checks
│   ├── main.py              # FastAPI application, payload limits & error handlers
│   ├── mock_data.py         # Structured pre-set demo meeting scenarios
│   ├── routers/             # Modular REST routers (auth, health, memory, pipeline, webhooks)
│   ├── schemas/api_models.py# Strict Pydantic schemas with input bounds & validation
│   ├── shared.py            # Shared singleton instances and cache
│   ├── webhook_inbox.py     # Inbox factory and local SQLite adapter
│   └── stores/              # Shared Postgres production webhook inbox adapter
├── frontend/                # Vanilla ES Modules UI (responsive, zero external build tools)
│   ├── css/styles.css       # Design tokens, accessibility focus-visible, animations
│   ├── js/                  # SPA router, authenticated API client, Web Audio capture & views
│   └── index.html           # Main application shell with authentication modal & PWA manifest
├── tests/                   # Automated unit and integration tests
├── docs/                    # Architecture, data flow, execution, and sequence diagrams
│   └── stitch_designs/      # Google Stitch generated UI designs & Obsidian Telemetry HTML
├── .github/workflows/ci.yml # Automated GitHub Actions CI (Python 3.10 & 3.11)
├── mcp_server.py            # Model Context Protocol (MCP) stdio JSON-RPC server
├── Dockerfile               # Production container image
├── docker-compose.yml       # Container orchestration
├── requirements.txt         # Pinned Python dependencies
└── pyproject.toml           # Packaging metadata and pytest/ruff configuration
```

---

## 🏆 Hackathon Submission Form Quick-Reference

> Keep these exact blocks ready for the [HiDevs Submission Form](https://app.hidevs.xyz/hackathons/stop-prompting-solo-agents-hackathon-2026?tab=submit):

### Project Name
**OMIMIND**

### Project Title
**OMIMIND: Ambient Voice Memory & Autonomous Chief of Staff for Omi, Qdrant & Lyzr**

### Build Track
**Meeting & Lecture Intelligence (Track 1)**

### Public GitHub Repository
**https://github.com/masood-mashu/omimind-agent**

### Deployed Demo URL
**https://omimind-agent.vercel.app/**

### Quick Judge Path
1. Open the deployed demo and sign in with the confirmed judge account below.
2. Open **Meetings** and choose **Seed Demo Data** to add the sample meetings to the judge workspace.
3. Open a seeded meeting and run the processing flow, then use **Ask** to query the indexed meeting context.
4. Open **Activity** to inspect the run trace and **Memory** to remove a session's memories.

**Judge login:** `judge-omimind-2026-10-13@example.com`

**Password:** `u0ieOHEfspZHh086Xa4nlaPvFWMusxR6`

This is a dedicated demo workspace. Do not store personal or sensitive information in it. New self-registered accounts still require email confirmation. Add the final demo-video URL to the submission form before submitting; a video URL is not available in this repository.

For a local lightweight evaluation, set `ENVIRONMENT=development`, `ALLOW_EPHEMERAL_MEMORY=true`, and `EMBEDDING_PROVIDER=deterministic` to use in-memory Qdrant and deterministic embeddings. This path does not need Qdrant Cloud or FastEmbed, but hosted Supabase Auth and Lyzr are still needed to demonstrate their live integrations. For the full multi-user deployment, configure all variables above and apply the Supabase migrations.

### Omi Usage
OMIMIND accepts Omi conversation and realtime transcript payloads through paired connection-token webhook endpoints:
- `POST /omi/conversation/{connection_token}` — triggers after a paired conversation concludes; ingests diarised `transcript_segments[]` with speaker attribution directly into persistent vector storage.
- `POST /omi/realtime/{connection_token}` — ingests streaming audio transcripts in real time as the paired user speaks.
These paired routes authenticate with the high-entropy connection token in the URL path and do not require custom signature headers. A separate legacy `POST /api/omi-webhook` route uses configured webhook credentials and timestamp/signature headers. Automated tests cover simulated webhook payloads; real Omi hardware delivery has not been verified as part of this repository update.

### Qdrant Usage
Every spoken utterance is converted into a 384-dimensional dense vector and indexed in the `omi_ambient_memory` collection on configured Qdrant storage. The default provider is FastEmbed with `BAAI/bge-small-en-v1.5`; set `EMBEDDING_PROVIDER=deterministic` only for tests or lightweight local evaluation. Vercel downloads the model into its temporary cache on cold start unless a cache is bundled. Searches and deletes include an owner filter for the authenticated workspace. Existing collections are protected from destructive deletion on dimension mismatch. The `/api/forget` endpoint lets each user remove their own stored memories.

When changing an existing deployment from another embedding provider, re-embed its stored points before relying on semantic ranking. `python scripts/reembed_qdrant.py` preflights the configured collection without changing it; add `--apply` to update only vectors while preserving point IDs and payloads. The script keeps prior vectors in memory and attempts rollback if the update or verification fails.

### Lyzr Usage
OMIMIND utilizes **Lyzr Agent Studio Cloud** with the configured Manager Agent as the core reasoning engine. The pipeline exposes an observable multi-agent orchestration streamed over Server-Sent Events (SSE):
1. **MemoryAgent:** Indexes transcript evidence into Qdrant Cloud.
2. **QdrantRetrieval:** Semantically retrieves relevant, user-scoped meeting context.
3. **LyzrManager:** Reasons over the retrieved context through the configured Lyzr Studio Manager Agent (delegation configured within Lyzr Studio) to generate structured synthesis.
4. **Deterministic Validators:** Extract and normalize actions, decisions, risks, and scheduling intent.
5. **Draft Outputs:** Prepares user-controlled email drafts, Atlassian Jira issue payload drafts, RFC 5545 `.ics` files, and Google Calendar draft URLs.
The client connects to the configured Lyzr Manager Agent with bounded timeouts and retries. Missing configuration or failed inference can produce deterministic fallback results; run traces identify the source. The current production Lyzr call returned HTTP 402 during verification, so restore the Lyzr account's ability to run agents before recording or claiming a live Lyzr demo. Verify `/health` and the run trace in the deployed environment before claiming a demo used `lyzr_studio_cloud`.

### Project Description
OMIMIND is an ambient voice memory and autonomous Chief of Staff built for Track 1 (Meeting & Lecture Intelligence). It accepts Omi wearable webhook transcripts, indexes utterances into owner-scoped 384-dimensional Qdrant memory, and can run reasoning through a configured Lyzr Agent Studio Manager. It includes SSE stream observability, grounded Q&A over past conversations, automated action items with owners and deadlines, user-controlled calendar drafts, and native Model Context Protocol (MCP) support for external developer IDEs. The deployed demo is at https://omimind-agent.vercel.app/.

---

## 👥 Author & Acknowledgements

- **Author:** Mohammed Masood ([@masood-mashu](https://github.com/masood-mashu))
- **Hackathon:** [Stop Prompting. Code Solo Agents (2026)](https://app.hidevs.xyz/hackathons/stop-prompting-solo-agents-hackathon-2026)
- **Partners:** HiDevs, Lyzr AI, Qdrant, Omi
- **License:** [Apache-2.0](LICENSE)
