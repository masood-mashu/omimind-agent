# HiDevs Track 1: Meeting & Lecture Intelligence

This document maps OmiMind to the official Track 1 requirements for the [Stop Prompting. Code Solo Agents Hackathon](https://app.hidevs.xyz/hackathons/stop-prompting-solo-agents-hackathon-2026).

## 1. Official requirements

The official page describes Track 1 as:

> Voice-to-insight with semantic retrieval and action-item extraction.

The hackathon page also requires every project to integrate:

- **Omi** for real-time voice capture or ambient input
- **Qdrant** for persistent vector memory and semantic retrieval
- **Lyzr** for multi-agent orchestration, reasoning, and task execution

The submission requirements currently shown on the official page are:

- Solo participation
- Public GitHub repository
- Setup instructions and an architecture diagram in the README
- Demo video of no more than five minutes
- Submission through HiDevs by **October 13, 2026 at 11:59 PM IST**

## 2. Current implementation mapping

| Requirement | Current implementation | Status |
|---|---|---|
| Voice-first input | Browser microphone transcript capture and Omi-compatible webhook routes | Implemented |
| Semantic retrieval | Qdrant collection `omi_ambient_memory`, 128-dimensional vectors, hybrid vector/lexical ranking | Implemented when Qdrant is configured; local fallback is available |
| Action-item extraction | Deterministic commitment, deadline, assignee, and priority rules in `agents/action_extractor.py` | Implemented |
| Meeting/lecture synthesis | Decision, risk, participant, and executive-summary generation in `agents/executive_synth.py` | Implemented |
| Contextual Q&A | `/api/query` local recall and protected `/ask` endpoint with optional Lyzr Studio synthesis | Implemented |
| Lyzr integration | Lyzr Studio is called by `/ask` when credentials are configured | Partial: the main five-stage demo pipeline is local Python, not a remote Lyzr workflow |
| Observable execution | SSE events for the five sequential processing stages | Implemented |
| Privacy controls | Protected webhook, Q&A, seed, and deletion routes; session/point deletion | Implemented; deployment must configure `API_SECRET_KEY` |

## 3. End-to-end product flow

```text
Omi or microphone transcript
              ↓
FastAPI validation and normalization
              ↓
Qdrant vector memory
              ↓
Local processing stages:
  memory indexing → action extraction → synthesis
  → task dispatch → calendar generation
              ↓
Dashboard, semantic recall, and user-controlled exports
```

See the detailed [execution flow](EXECUTION_FLOW.md) and the standalone [architecture](ARCHITECTURE.md), [data-flow](DATA_FLOW.md), and [sequence](SEQUENCE_DIAGRAM.md) diagrams.

## 4. Evidence currently available

- Public repository: [github.com/masood-mashu/omimind-agent](https://github.com/masood-mashu/omimind-agent)
- Live dashboard: [omimind-agent.vercel.app](https://omimind-agent.vercel.app/)
- Automated verification: 58 tests passing, 87.77% coverage, Ruff passing
- Local end-to-end dashboard flow verified
- Production preset flow and semantic recall verified
- README includes setup instructions and architecture documentation links

## 5. Submission checklist

Before submitting, verify the following items in the HiDevs form:

- [ ] Repository is public and contains the latest commit.
- [ ] `API_SECRET_KEY` and provider credentials are configured in the deployment environment.
- [ ] Omi webhook integration is demonstrated or clearly described with its protected routes.
- [ ] Qdrant persistence is demonstrated with a configured Qdrant URL and API key.
- [ ] Lyzr Studio usage is demonstrated through `/ask`, or the main orchestration is upgraded to a Lyzr-managed workflow.
- [ ] Demo video is no longer than five minutes and shows the complete voice → memory → reasoning → output loop.
- [ ] Submission is completed before October 13, 2026 at 11:59 PM IST.

## 6. Important positioning note

The repository should describe the five dashboard stages as a local modular processing pipeline and describe Lyzr as the optional external grounded-Q&A integration unless the implementation is changed to execute those stages through Lyzr. This distinction keeps the submission technically accurate while still demonstrating the required Omi, Qdrant, and Lyzr integration points.
