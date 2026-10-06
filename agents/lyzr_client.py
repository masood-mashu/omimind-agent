"""Small, typed client for the Lyzr Studio inference API.

The client deliberately returns an explicit provider status.  A local
deterministic result is allowed for development and tests, but callers must
not present that result as Lyzr reasoning.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LyzrResult:
    text: str
    provider: str
    agent_id: str | None = None
    error: str | None = None


class LyzrClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        agent_id: str | None = None,
        url: str | None = None,
        timeout: float | None = None,
    ):
        self.api_key = api_key or os.environ.get("LYZR_API_KEY")
        self.agent_id = agent_id or os.environ.get("LYZR_MANAGER_AGENT_ID") or os.environ.get("LYZR_AGENT_ID")
        self.url = url or os.environ.get(
            "LYZR_INFERENCE_URL",
            "https://agent-prod.studio.lyzr.ai/v3/inference/chat/",
        )
        self.timeout = timeout if timeout is not None else float(os.environ.get("LYZR_TIMEOUT_SECONDS", "45"))

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.agent_id)

    def reason(self, *, uid: str, question: str, context: list[dict[str, Any]]) -> LyzrResult:
        if not self.configured:
            return LyzrResult(
                text="",
                provider="unconfigured",
                agent_id=self.agent_id,
                error="LYZR_API_KEY and a Manager/agent ID are required for Lyzr reasoning",
            )

        try:
            import httpx

            context_text = "\n".join(
                f"- [{item.get('speaker', 'Speaker')} @ {item.get('timestamp_str', 'unknown')}] "
                f"{item.get('text', '')}"
                for item in context
            ) or "none"
            response = httpx.post(
                self.url,
                headers={"Content-Type": "application/json", "x-api-key": self.api_key},
                json={
                    "user_id": os.environ.get("LYZR_USER_ID", uid),
                    "agent_id": self.agent_id,
                    "session_id": f"{self.agent_id}-{uid}",
                    "message": (
                        "CONTEXT:\n"
                        f"{context_text}\n\n"
                        f"QUESTION: {question}\n"
                        "Answer only from the supplied context and identify the evidence used."
                    ),
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            text = response.json().get("response", "")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Lyzr returned an empty response")
            return LyzrResult(text=text.strip(), provider="lyzr_studio_cloud", agent_id=self.agent_id)
        except Exception as exc:  # network/provider errors are surfaced as metadata
            return LyzrResult(
                text="",
                provider="lyzr_error",
                agent_id=self.agent_id,
                error=str(exc),
            )
