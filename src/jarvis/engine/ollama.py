"""Ollama local engine."""

from __future__ import annotations

import json
import os

from jarvis.core.types import AgentResponse, Message, EngineConfig
from jarvis.engine.base import BaseEngine


class OllamaEngine(BaseEngine):
    name = "ollama"

    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self.base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        # model override
        if os.environ.get("JARVIS_MODEL"):
            self.config.model = os.environ["JARVIS_MODEL"]

    def generate(self, messages: list[Message], **kwargs) -> AgentResponse:
        import urllib.request
        import urllib.error

        # Ollama chat API
        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
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
        return {"name": self.name, "base_url": self.base_url, "model": self.config.model}
