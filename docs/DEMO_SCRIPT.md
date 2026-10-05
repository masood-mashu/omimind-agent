# 🎬 Five-Minute Hackathon Demo Script (Turnkey Video Guide)

**Hackathon:** [Stop Prompting. Code Solo Agents (2026)](https://app.hidevs.xyz/hackathons/stop-prompting-solo-agents-hackathon-2026)  
**Track:** Track 1: Meeting & Lecture Intelligence  
**Target Video Duration:** Under 5 minutes (Strict requirement)  
**Live Target:** [https://omimind-agent.vercel.app/](https://omimind-agent.vercel.app/)  

---

## ⏱️ Minute-by-Minute Recording Walkthrough

```mermaid
gantt
    title 5-Minute Video Recording Timeline
    dateFormat mm:ss
    axisFormat %M:%S
    section Intro
    Problem & Omi Ambient Concept      :00:00, 00:30
    section Architecture
    Omi, Qdrant & Lyzr Connected Loop  :00:30, 01:15
    section Live Swarm
    Ingest Feed & Watch Live SSE Swarm :01:15, 02:15
    Deliverables: Kanban, Calendar, Email :02:15, 03:00
    section Memory & MCP
    Semantic Q&A with Evidence        :03:00, 03:45
    Live Mic Capture & MCP Server Tools:03:45, 04:30
    section Conclusion
    Recap & Track 1 Impact             :04:30, 05:00
```

---

### 🎙️ 0:00 – 0:30 | The Problem & The Omi Ambient Concept

- **Screen:** Show the live application at [omimind-agent.vercel.app](https://omimind-agent.vercel.app/).
- **Spoken Talking Track:**
  > *"Hi everyone, this is Mohammed Masood, and this is OmiMind — an ambient voice memory and autonomous Chief of Staff built for the Stop Prompting, Solo Agents Hackathon, competing in Track 1: Meeting & Lecture Intelligence.*  
  > *Traditional meeting assistants force intrusive bots into your calls or transcribe audio into useless walls of text. OmiMind listens through Omi or a microphone, stores meeting evidence in Qdrant, and sends retrieved context to a Lyzr Manager for grounded meeting intelligence. Deterministic components then prepare user-controlled follow-up outputs."*

---

### 🏛️ 0:30 – 1:15 | Architecture & Connected Loop

- **Screen:** Point out the top header badge (`Qdrant Vectors: Active`) and briefly reference the Mermaid architecture diagram in the README.
- **Spoken Talking Track:**
  > *"Our system connects three foundational pillars into one seamless loop:*  
  > *1. **Omi Voice Ingestion:** The webhook validates the payload, queues processing, and acknowledges quickly.*
  > *2. **Qdrant Vector Memory:** Utterances are embedded with `BAAI/bge-small-en-v1.5` into 384-dimensional vectors with speaker, user, and timestamp attribution.*
  > *3. **Lyzr Reasoning:** Qdrant retrieves relevant evidence and a real Lyzr Manager reasons over that context; deterministic validators prepare safe follow-up drafts."*

---

### ⚡ 1:15 – 2:15 | Live Swarm Execution (Observable SSE)

- **Screen:** In the left sidebar, click the preset **Q4 AI Strategy & Budget** (`#btn-q4_strategy`), then click **Ingest & Run Lyzr Swarm** (`#btn-process`).
- **Action:** Watch the observable Qdrant retrieval and Lyzr Manager stages expand in the live monitor.
- **Spoken Talking Track:**
  > *"Let's see it in action. I'll select our 'Q4 AI Strategy & Budget' meeting and click 'Ingest & Run Lyzr Swarm'.*  
  > *Notice the live SSE monitor on the left. Rather than a black-box spinner, we can watch each specialized Lyzr agent work in real time:*  
  > *- First, the **MemoryAgent** indexes all 8 utterances into Qdrant Cloud.*  
  > *- Next, the **ActionExtractor** detects verbal commitments and deadlines.*  
  > *- Then, the **ExecutiveSynthesizer** distills key decisions and risks.*  
  > *- The **TaskDispatcher** drafts follow-up emails and Atlassian Jira tickets.*  
  > *- Finally, the **CalendarScheduler** identifies follow-up meeting intent.*  
  > *The pipeline completes in seconds; the exact provider and output counts are shown by the live response."*

---

### 📦 2:15 – 3:00 | Inspecting the Deliverables

- **Screen:** Click through the five tabs in the right intelligence dossier.
- **Tab 1: Executive Synthesis:**
  > *"In Executive Synthesis, we see confirmed decisions: CFO Sarah's Zero-Trust token redaction policy, CTO David's 128-node reserved cluster approval, and identified latency risks."*
- **Tab 2: Action Items & Kanban:**
  > *"In Action Items, our agent autonomously extracted 6 prioritized tasks with assignees and exact deadlines, categorized by P0, High, and Medium urgency."*
- **Tab 3: 📅 Calendar Sync:**
  > *"In Calendar Sync, the agent detected commitments to meet and generated two follow-up sync sessions, complete with a direct **+ Google Meet** launch button and an RFC 5545 **.ics** download for Apple or Outlook calendar import."*
- **Tab 4 & 5: Email & Jira:**
  > *"In Follow-Up Email, an executive recap is pre-addressed to all attendees with a 1-click **Send via Gmail** button. In Jira Tickets, structured tickets `OMI-1` through `OMI-6` are ready with labels `OmiVoice`, `LyzrAgent`, and `QdrantMemory`."*

---

### 🔍 3:00 – 3:45 | Qdrant Semantic Memory Recall & Q&A

- **Screen:** Scroll to the **Qdrant Semantic Memory Recall** box (`#query-input`).
- **Action:** Type: `"What did Sarah say about the budget?"` and press Enter.
- **Spoken Talking Track:**
  > *"Now let's test our persistent vector memory in Qdrant Cloud.*  
  > *I'll ask: 'What did Sarah say about the budget?'*  
  > *Qdrant returns the highest-ranked transcript evidence with speaker and timestamp attribution. The displayed score is the actual score from this run, not a fixed accuracy claim.*
  > *The answer is grounded by passing retrieved evidence to Lyzr; if the provider is unavailable, the interface reports that explicitly."*

---

### 🎙️ 3:45 – 4:30 | Live Mic Voice Memo & MCP Tools

- **Screen:** Show the **Live Omi Voice Capture** panel with the canvas audio waveform visualizer.
- **Action:** Either speak into the microphone or paste a custom sentence: *"I will deploy the rate-limiting middleware to staging tomorrow morning and let's review on Thursday at 11 AM."* Click **Vectorize**.
- **Spoken Talking Track:**
  > *"OmiMind also accepts live spoken voice or custom memos. When I click Vectorize, the connected Qdrant and Lyzr stages process the input, then deterministic components prepare any calendar draft for approval.*
  > *Furthermore, for external developer agents like Claude Desktop, Cursor, or Antigravity, OmiMind includes a native Model Context Protocol (MCP) server running over JSON-RPC stdio, exposing our vector memory as native tools."*

---

### 🏁 4:30 – 5:00 | Conclusion & Impact

- **Screen:** Return to the top of the dashboard or the GitHub repository.
- **Spoken Talking Track:**
  > *"To summarize: OmiMind is a Track 1 meeting and lecture intelligence system. It integrates Omi voice ingestion, persistent Qdrant memory, and a Lyzr Manager reasoning step in one observable, closed-loop system.*
  > *The connected stages transform spoken meetings from ephemeral conversations into actionable, persistent intelligence while keeping external actions user-controlled.*
  > *Thank you to HiDevs, Lyzr, Qdrant, and Omi for hosting this hackathon!"*
