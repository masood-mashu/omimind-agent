"""Small, typed client for the Lyzr Studio inference API.

The client deliberately returns an explicit provider status. A local
deterministic result is allowed for development and tests, but callers must
not present that result as Lyzr reasoning.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("omimind.lyzr")


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
        connect_timeout: float = 10.0,
        max_retries: int = 2,
    ):
        self.api_key = api_key or os.environ.get("LYZR_API_KEY")
        self.agent_id = agent_id or os.environ.get("LYZR_MANAGER_AGENT_ID") or os.environ.get("LYZR_AGENT_ID")
        self.url = url or os.environ.get(
            "LYZR_INFERENCE_URL",
            "https://agent-prod.studio.lyzr.ai/v3/inference/chat/",
        )
        self.timeout = timeout if timeout is not None else float(os.environ.get("LYZR_TIMEOUT_SECONDS", "45"))
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.agent_id)

    def _sanitize_error(self, exc: Exception) -> str:
        """Classifies error safely and guarantees no secrets are leaked in error strings."""
        if isinstance(exc, httpx.TimeoutException):
            classified = f"Lyzr inference timed out (timeout={self.timeout}s)"
        elif isinstance(exc, httpx.NetworkError):
            classified = "Failed to establish network connection to Lyzr Studio"
        elif isinstance(exc, httpx.HTTPStatusError):
            classified = f"Lyzr Studio returned error HTTP {exc.response.status_code}"
        else:
            classified = str(exc) or exc.__class__.__name__

        if self.api_key and self.api_key in classified:
            classified = classified.replace(self.api_key, "[REDACTED]")
        return classified

    def _build_payload(self, uid: str, question: str, context: list[dict[str, Any]]) -> dict[str, Any]:
        context_text = "\n".join(
            f"- [{item.get('speaker', 'Speaker')} @ {item.get('timestamp_str', 'unknown')}] "
            f"{item.get('text', '')}"
            for item in context
        ) or "none"

        # Consistent user identity: Use authenticated uid directly to preserve tenant isolation
        effective_user_id = uid if uid else (os.environ.get("LYZR_USER_ID") or "default_user")

        return {
            "user_id": effective_user_id,
            "agent_id": self.agent_id,
            "session_id": f"{self.agent_id}-{effective_user_id}",
            "message": (
                "CONTEXT:\n"
                f"{context_text}\n\n"
                f"QUESTION: {question}\n"
                "Answer only from the supplied context and identify the evidence used."
            ),
        }

    async def areason(self, *, uid: str, question: str, context: list[dict[str, Any]]) -> LyzrResult:
        """
        Asynchronous non-blocking Lyzr inference with connection/read timeouts,
        bounded retries, and honest provider classification.
        """
        if not self.configured:
            return LyzrResult(
                text="",
                provider="unconfigured",
                agent_id=self.agent_id,
                error="LYZR_API_KEY and a Manager/agent ID are required for Lyzr reasoning",
            )

        payload = self._build_payload(uid, question, context)
        headers = {"Content-Type": "application/json", "x-api-key": self.api_key}
        timeout_cfg = httpx.Timeout(timeout=self.timeout, connect=self.connect_timeout, read=self.timeout)

        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    response = await client.post(self.url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    text = data.get("response", "")
                    if not isinstance(text, str) or not text.strip():
                        raise ValueError("Lyzr returned an empty response")
                    return LyzrResult(
                        text=text.strip(),
                        provider="lyzr_studio_cloud",
                        agent_id=self.agent_id,
                    )
            except httpx.HTTPStatusError as exc:
                last_error = self._sanitize_error(exc)
                if exc.response.status_code < 500:
                    # Client errors (4xx) should not be retried
                    break
                if attempt < self.max_retries:
                    await asyncio.sleep(0.3 * (attempt + 1))
            except Exception as exc:
                last_error = self._sanitize_error(exc)
                if attempt < self.max_retries:
                    await asyncio.sleep(0.3 * (attempt + 1))

        return LyzrResult(
            text="",
            provider="lyzr_error",
            agent_id=self.agent_id,
            error=last_error,
        )

    def reason(self, *, uid: str, question: str, context: list[dict[str, Any]]) -> LyzrResult:
        """
        Synchronous inference with bounded retries and timeout enforcement.
        Does not block the async event loop if called in worker thread.
        """
        if not self.configured:
            return LyzrResult(
                text="",
                provider="unconfigured",
                agent_id=self.agent_id,
                error="LYZR_API_KEY and a Manager/agent ID are required for Lyzr reasoning",
            )

        payload = self._build_payload(uid, question, context)
        headers = {"Content-Type": "application/json", "x-api-key": self.api_key}
        timeout_cfg = httpx.Timeout(timeout=self.timeout, connect=self.connect_timeout, read=self.timeout)

        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.post(self.url, headers=headers, json=payload, timeout=timeout_cfg)
                response.raise_for_status()
                data = response.json()
                text = data.get("response", "")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("Lyzr returned an empty response")
                return LyzrResult(
                    text=text.strip(),
                    provider="lyzr_studio_cloud",
                    agent_id=self.agent_id,
                )
            except httpx.HTTPStatusError as exc:
                last_error = self._sanitize_error(exc)
                if exc.response.status_code < 500:
                    break
                if attempt < self.max_retries:
                    time.sleep(0.3 * (attempt + 1))
            except Exception as exc:
                last_error = self._sanitize_error(exc)
                if attempt < self.max_retries:
                    time.sleep(0.3 * (attempt + 1))

        return LyzrResult(
            text="",
            provider="lyzr_error",
            agent_id=self.agent_id,
            error=last_error,
        )
