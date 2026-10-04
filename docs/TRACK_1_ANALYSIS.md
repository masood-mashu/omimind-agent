# 🎙️ HiDevs Hackathon: Track 1 (Meeting & Lecture Intelligence) Deep-Dive

This document provides a comprehensive analysis of **Track 1: Meeting & Lecture Intelligence** for the HiDevs Hackathon (AI House × HiDevs × Lyzr × Qdrant × Omi), detailing the problem statement, mandatory architecture, and how **OmiMind** addresses every single requirement and evaluation rubric.

---

## 1. Track Overview & Core Mandate

> **Track Definition (Official Guide)**:  
> *"Voice-to-insight engines with semantic retrieval, automated action-item extraction and Q&A over past meetings."*

### The Problem in Meeting & Lecture Intelligence
In fast-paced organizations and academic environments:
- **Ephemeral Spoken Conversations**: Verbal decisions, commitments, and deadlines vanish the moment the conversation ends.
- **Action Item Drift**: Tasks agreed upon in meetings lack explicit owners or deadlines, leading to project delays.
- **Search Impossibility**: Searching through audio recordings is slow and friction-heavy.
- **Manual Note-Taking Friction**: Manual notes distract participants from active listening.

---

## 2. The 3 Mandatory Tech Pillars & How OmiMind Delivers

The hackathon requires connecting all three technologies in a **single connected loop**:

```
[ 🎙️ Omi: Ambient Voice Ingestion ]
                 ⬇️
[ ⚡ Qdrant: Semantic Retrieval & Memory ]
                 ⬇️
[ 🐝 Lyzr: Multi-Agent Reasoning Swarm ]
```

| Technology | Role Required | OmiMind Implementation |
|---|---|---|
| **Omi** | Real-time ambient audio capture | Native webhook endpoints (`/omi/conversation` & `/omi/realtime`) ingesting transcript segments, speaker diarisation, and timestamps. |
| **Qdrant** | Persistent vector memory & semantic retrieval | AWS Qdrant Cloud cluster (`omi_ambient_memory`) running 128-dim dense normalized vectors with hybrid 60% cosine + 40% lexical stem search. |
| **Lyzr** | Multi-agent reasoning swarm | 5 specialized agents (MemoryAgent, ActionExtractor, ExecutiveSynthesizer, TaskDispatcher, CalendarScheduler) + Lyzr Studio Cloud inference (`6ac2646b...`). |

---

## 3. How OmiMind Solves the Core Requirements

### 1. Automated Action-Item Extraction (`ActionExtractor`)
- Extracts owners via Named Entity Recognition (NER).
- Detects explicit deadlines (e.g., *"Tuesday at 2 PM"*, *"before Friday"*).
- Assigns priority ratings (`P0 / Critical`, `High`, `Medium`).
- Renders an interactive Kanban board with status toggles.

### 2. Grounded Q&A Over Past Meetings (`MemoryAgent` + `/ask`)
- **Instant Search-as-You-Type (`/api/query`)**: 400ms debounced vector recall showing verbatim quotes, speaker attribution, and cosine relevance scores (e.g. `81% Match (0.8058)`).
- **Conversational Synthesis (`/ask`)**: Lyzr Studio Cloud Agent synthesizes grounded answers using the retrieved Qdrant context snippets.

### 3. Executive Dossier & Strategic Synthesis (`ExecutiveSynthesizer`)
- Categorizes **Confirmed Decisions** vs. **Identified Blockers & Risks**.
- Tracks participant engagement and meeting intent.

### 4. Closing the Loop (`TaskDispatcher` & `CalendarScheduler`)
- **1-Click Send via Gmail**: Pre-fills Gmail web compose with drafted email, subject, and recipient.
- **Jira Engineering Tickets**: Auto-formats tickets (`OMI-1`, `OMI-2`) ready for copy/import.
- **RFC 5545 Calendar Invites**: Extracts meeting times and generates Google Meet links + downloadable `.ics` files.
- **Model Context Protocol (MCP)**: Native `mcp_server.py` exposing OmiMind tools to Claude Desktop, Cursor, and Antigravity.

---

## 4. Evaluation Rubric & Competitive Advantage

| Criterion | Hackathon Weight | OmiMind Execution |
|---|---|---|
| **Working Software** | High (60%+ score) | Live on Vercel ([omimind-agent.vercel.app](https://omimind-agent.vercel.app/)) with 105+ active cloud vectors. |
| **Observable Agent Workflows** | Explicit Bonus | Real-time Server-Sent Events (SSE) stream animating all 5 agents on the live dashboard. |
| **Agent Specialization** | Explicit Bonus | 5 dedicated modular agents coordinated by central orchestrator. |
| **Testing & Reliability** | Code Quality Gate | 55 automated unit/integration tests with a 100% green pass rate (`pytest tests/ -v`). |
| **Real Device Verification** | Authenticity | Tested and verified with real spoken voice from the Omi mobile app. |
