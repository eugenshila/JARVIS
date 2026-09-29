"""Ollama local engine."""

from __future__ import annotations

import json
import os

from jarvis.core.types import AgentResponse, Message, EngineConfig
from jarvis.engine.base import BaseEngine


class OllamaEngine(BaseEngine):
    name = "ollama"

    #: How long Ollama should keep the model resident after a call. Reloading
    #: a 3B model costs several seconds; holding it costs only RAM we already
    #: spent.
    KEEP_ALIVE = os.environ.get("JARVIS_OLLAMA_KEEP_ALIVE", "30m")

    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self.base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        # model override
        if os.environ.get("JARVIS_MODEL"):
            self.config.model = os.environ["JARVIS_MODEL"]
        self._warmed: str | None = None

    def warmup(self, system_prompt: str | None = None, timeout: float = 60.0) -> bool:
        """Load the model and prime Ollama's KV prefix cache.

        Ollama caches the attention state of a prompt *prefix* between
        requests. If we warm up with the same system prompt real requests will
        use, those few hundred tokens are evaluated once, at startup, instead
        of on the first real question — which is the difference between the
        user waiting ~15s for the first reply and waiting ~1s.

        Pass the STATIC part of the system prompt only. Anything that changes
        per request (a timestamp, the current context) invalidates the prefix
        and makes the warmup pointless.

        Returns True if the model responded. Never raises: a failed warmup is
        a missed optimisation, not an error.
        """
        import urllib.error
        import urllib.request

        prompt = (system_prompt or "").strip()
        if self._warmed is not None and self._warmed == prompt:
            return True

        messages = []
        if prompt:
            messages.append({"role": "system", "content": prompt})
        messages.append({"role": "user", "content": "ok"})
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.KEEP_ALIVE,
            # One token: we want the prefix evaluated, not an answer.
            "options": {"num_predict": 1, "temperature": 0.0},
        }
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout):
                self._warmed = prompt
                return True
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def generate(self, messages: list[Message], **kwargs) -> AgentResponse:
        import urllib.request
        import urllib.error

        # Ollama chat API
        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "keep_alive": self.KEEP_ALIVE,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.load(resp)
                content = result.get("message", {}).get("content", "") or result.get("response", "")
                return AgentResponse(content=content, model=result.get("model", self.config.model))
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama not reachable at {self.base_url}. Is `ollama serve` running? {e}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}") from e

    async def agenerate(self, messages: list[Message], **kwargs) -> AgentResponse:
        try:
            import httpx
        except ImportError:
            import asyncio
            return await asyncio.to_thread(self.generate, messages, **kwargs)

        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()
            content = result.get("message", {}).get("content", "")
            return AgentResponse(content=content, model=result.get("model", self.config.model))

    def describe(self):
        return {
            "name": self.name,
            "base_url": self.base_url,
            "model": self.config.model,
            "warmed": self._warmed is not None,
        }
