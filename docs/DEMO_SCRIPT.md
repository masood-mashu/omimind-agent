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
    Semantic Q&A (99%+ Vector Match)   :03:00, 03:45
    Live Mic Capture & MCP Server Tools:03:45, 04:30
    section Conclusion
    Recap & Track 1 Impact             :04:30, 05:00
```

---

### 🎙️ 0:00 – 0:30 | The Problem & The Omi Ambient Concept

- **Screen:** Show the live application at [omimind-agent.vercel.app](https://omimind-agent.vercel.app/).
- **Spoken Talking Track:**
  > *"Hi everyone, this is Mohammed Masood, and this is OmiMind — an ambient voice memory and autonomous Chief of Staff built for the Stop Prompting, Solo Agents Hackathon, competing in Track 1: Meeting & Lecture Intelligence.*  
  > *Traditional meeting assistants force intrusive bots into your calls or transcribe audio into useless walls of text. OmiMind is completely ambient: it listens through the Omi AI Wearable or your microphone, stores every utterance as a dense vector in Qdrant Cloud, and unleashes a Lyzr 5-Agent Swarm that autonomously produces executive dossiers, Kanban action items, Jira tickets, and calendar invitations without prompting."*

---

### 🏛️ 0:30 – 1:15 | Architecture & Connected Loop

- **Screen:** Point out the top header badge (`Qdrant Vectors: Active`) and briefly reference the Mermaid architecture diagram in the README.
- **Spoken Talking Track:**
  > *"Our system connects three foundational pillars into one seamless loop:*  
  > *1. **Omi Voice Ingestion:** Via dedicated webhooks (`/omi/conversation`, `/omi/realtime`, and `/api/omi-webhook`), we accept audio chunks and full conversation transcripts with sub-50ms acknowledgement.*  
  > *2. **Qdrant Cloud Vector Memory:** Utterances are embedded as 128-dimensional dense vectors with speaker and timestamp attribution, queried via a 60% cosine + 40% lexical hybrid search.*  
  > *3. **Lyzr Multi-Agent Swarm:** Five specialized agents coordinate to process transcripts in real time, streaming their progress live to our dashboard via Server-Sent Events, plus grounded Q&A inference through Lyzr Studio Cloud."*

---

### ⚡ 1:15 – 2:15 | Live Swarm Execution (Observable SSE)

- **Screen:** In the left sidebar, click the preset **Q4 AI Strategy & Budget** (`#btn-q4_strategy`), then click **Ingest & Run Lyzr Swarm** (`#btn-process`).
- **Action:** Watch the **Lyzr 5-Agent Swarm Live Monitor** panel expand and observe the real-time execution transitions.
- **Spoken Talking Track:**
  > *"Let's see it in action. I'll select our 'Q4 AI Strategy & Budget' meeting and click 'Ingest & Run Lyzr Swarm'.*  
  > *Notice the live SSE monitor on the left. Rather than a black-box spinner, we can watch each specialized Lyzr agent work in real time:*  
  > *- First, the **MemoryAgent** indexes all 8 utterances into Qdrant Cloud.*  
  > *- Next, the **ActionExtractor** detects verbal commitments and deadlines.*  
  > *- Then, the **ExecutiveSynthesizer** distills key decisions and risks.*  
  > *- The **TaskDispatcher** drafts follow-up emails and Atlassian Jira tickets.*  
  > *- Finally, the **CalendarScheduler** identifies follow-up meeting intent.*  
  > *In under 4 seconds, all 5 agents complete!"*

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
  > *Instantly, Qdrant returns a **99.47% Vector Relevance Match** with exact speaker attribution: Sarah at 00:15 stating 'Budget is under review'.*  
  > *Because our retrieval combines 60% cosine vector similarity and 40% lexical stem overlap, it pinpoints the exact moment in the conversation with zero hallucinations."*

---

### 🎙️ 3:45 – 4:30 | Live Mic Voice Memo & MCP Tools

- **Screen:** Show the **Live Omi Voice Capture** panel with the canvas audio waveform visualizer.
- **Action:** Either speak into the microphone or paste a custom sentence: *"I will deploy the rate-limiting middleware to staging tomorrow morning and let's review on Thursday at 11 AM."* Click **Vectorize**.
- **Spoken Talking Track:**
  > *"OmiMind also accepts live spoken voice or custom memos. When I click Vectorize, the same 5-agent swarm processes my voice input, updates Qdrant, and schedules a Thursday 11 AM calendar event.*  
  > *Furthermore, for external developer agents like Claude Desktop, Cursor, or Antigravity, OmiMind includes a native Model Context Protocol (MCP) server running over JSON-RPC stdio, exposing our vector memory as native tools."*

---

### 🏁 4:30 – 5:00 | Conclusion & Impact

- **Screen:** Return to the top of the dashboard or the GitHub repository.
- **Spoken Talking Track:**
  > *"To summarize: OmiMind is a fully open-source, production-grade autonomous Chief of Staff. It integrates Omi voice ingestion, Qdrant Cloud vector memory, and a 5-agent Lyzr swarm in one observable, closed-loop system.*  
  > *Backed by 58 automated tests with 87.77% coverage and deployed live on Vercel, OmiMind transforms spoken meetings from ephemeral conversations into actionable, permanent intelligence.*  
  > *Thank you to HiDevs, Lyzr, Qdrant, and Omi for hosting this hackathon!"*
