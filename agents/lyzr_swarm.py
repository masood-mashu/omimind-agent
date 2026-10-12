"""Role-aware Lyzr execution for the observable meeting pipeline."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from agents.lyzr_client import LyzrClient, LyzrResult
from backend.config import settings


@dataclass(frozen=True)
class AgentDefinition:
    role: str
    agent_id: str | None
    label: str


class LyzrAgentRegistry:
    """The deployment owns the agent IDs; browsers never provide them."""

    def __init__(self):
        self._agents = {
            "memory_recall": AgentDefinition("memory_recall", settings.lyzr_memory_recall_agent_id, "Memory Recall"),
            "meeting_analyst": AgentDefinition("meeting_analyst", settings.lyzr_meeting_analyst_agent_id, "Meeting Analyst"),
            "action_extractor": AgentDefinition("action_extractor", settings.lyzr_action_extractor_agent_id, "Action Extractor"),
            "manager": AgentDefinition("manager", settings.lyzr_manager_agent_id, "Manager"),
            "followup_planner": AgentDefinition("followup_planner", settings.lyzr_followup_planner_agent_id, "Follow-up Planner"),
        }

    def get(self, role: str) -> AgentDefinition:
        return self._agents[role]

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return {role: {"label": item.label, "agent_id": item.agent_id, "configured": bool(item.agent_id)} for role, item in self._agents.items()}


@dataclass(frozen=True)
class AgentTrace:
    role: str
    agent_id: str | None
    status: str
    provider: str
    execution_source: str
    result: LyzrResult
    latency_ms: int
    started_at: float | None = None
    completed_at: float | None = None
    input_summary: str | None = None
    evidence_ids: list[str] | None = None
    run_id: str | None = None
    event_id: str | None = None


class LyzrSwarmRunner:
    def __init__(self, client: LyzrClient | None = None, registry: LyzrAgentRegistry | None = None):
        self.client = client or LyzrClient()
        self.registry = registry or LyzrAgentRegistry()

    async def _call(self, role: str, *, uid: str, question: str, context: list[dict[str, Any]]) -> AgentTrace:
        definition = self.registry.get(role)
        started_at = time.time()
        started = time.perf_counter()
        result = await self.client.areason(uid=uid, question=question, context=context, agent_id=definition.agent_id)
        latency = int((time.perf_counter() - started) * 1000)
        successful = result.provider == "lyzr_studio_cloud" and bool(result.text.strip())
        return AgentTrace(
            role=role,
            agent_id=definition.agent_id,
            status="completed" if successful else "failed",
            provider=result.provider,
            execution_source="lyzr_studio_cloud" if successful else "deterministic_fallback",
            result=result,
            latency_ms=latency,
            started_at=started_at,
            completed_at=time.time(),
            input_summary=question[:500],
            evidence_ids=[str(item.get("id")) for item in context if item.get("id")],
        )

    async def run(self, *, uid: str, title: str, transcript: list[dict[str, Any]], retrieved_context: list[dict[str, Any]]) -> list[AgentTrace]:
        traces: list[AgentTrace] = []
        async for trace in self.stream(uid=uid, title=title, transcript=transcript, retrieved_context=retrieved_context):
            traces.append(trace)
        return traces

    async def stream(self, *, uid: str, title: str, transcript: list[dict[str, Any]], retrieved_context: list[dict[str, Any]]):
        base = retrieved_context or transcript
        worker_questions = {
            "memory_recall": f"Recall the most relevant prior user memory for this meeting: {title}. Cite evidence.",
            "meeting_analyst": f"Analyze this meeting for summary, decisions, risks, and unresolved questions: {title}.",
            "action_extractor": f"Extract concrete action items, owners, and due dates from this meeting: {title}.",
        }
        worker_tasks = [asyncio.create_task(self._call(role, uid=uid, question=question, context=base)) for role, question in worker_questions.items()]
        workers: list[AgentTrace] = []
        for task in asyncio.as_completed(worker_tasks):
            trace = await task
            workers.append(trace)
            yield trace
        worker_context = base + [
            {"speaker": trace.role, "timestamp_str": "agent output", "text": trace.result.text}
            for trace in workers if trace.result.text
        ]
        manager = await self._call(
            "manager",
            uid=uid,
            question="Synthesize the worker outputs into grounded meeting intelligence with headings for Executive Summary, Key Decisions, Risks and Blockers, and Action Items.",
            context=worker_context,
        )
        yield manager
        planner = await self._call(
            "followup_planner",
            uid=uid,
            question="Turn the meeting intelligence into clear follow-up email, Jira, and calendar draft recommendations. Keep them as drafts for user review.",
            context=worker_context + [{"speaker": "manager", "timestamp_str": "agent output", "text": manager.result.text}],
        )
        yield planner
