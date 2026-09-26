"""OpenAI-compatible engine."""

from __future__ import annotations

import json
import os
from typing import Any

from jarvis.core.types import AgentResponse, Message, EngineConfig
from jarvis.engine.base import BaseEngine


class OpenAICompatibleEngine(BaseEngine):
    name = "openai"

    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        if not self.config.api_key:
            self.config.api_key = os.environ.get("OPENAI_API_KEY", "")
        if os.environ.get("JARVIS_API_URL"):
            self.config.api_url = os.environ["JARVIS_API_URL"]
        if os.environ.get("JARVIS_MODEL"):
            self.config.model = os.environ["JARVIS_MODEL"]

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, messages: list[Message]) -> dict[str, Any]:
        return {
            "model": self.config.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

    def chat(self, messages: list[Message], tools=None, **kwargs) -> AgentResponse:
        # Compatibility: chat calls generate
        return self.generate(messages, **kwargs)

    def generate(self, messages: list[Message], **kwargs) -> AgentResponse:
        import urllib.request
        import urllib.error

        if not self.config.api_key:
            raise ValueError("OPENAI_API_KEY not set. Set env var or use --mock for offline demo.")

        if not self.config.api_url.startswith("https://") and not self.config.api_url.startswith("http://"):
            raise ValueError("API URL must be http(s)")

        data = json.dumps(self._payload(messages)).encode("utf-8")
        req = urllib.request.Request(self.config.api_url, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                result = json.load(resp)
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:500]
            raise RuntimeError(f"API HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Cannot connect to {self.config.api_url}: {e.reason}") from e

        try:
            choice = result["choices"][0]
            content = choice["message"]["content"] or ""
            usage = result.get("usage", {})
            return AgentResponse(content=content, usage=usage, model=result.get("model", self.config.model))
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected API response: {result}") from e

    async def agenerate(self, messages: list[Message], **kwargs) -> AgentResponse:
        try:
            import httpx
        except ImportError:
            # fallback to sync in thread
            import asyncio
            return await asyncio.to_thread(self.generate, messages, **kwargs)

        if not self.config.api_key:
            raise ValueError("OPENAI_API_KEY not set.")

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self.config.api_url,
                json=self._payload(messages),
                headers=self._headers(),
            )
            resp.raise_for_status()
            result = resp.json()
            choice = result["choices"][0]
            content = choice["message"]["content"] or ""
            usage = result.get("usage", {})
            return AgentResponse(content=content, usage=usage, model=result.get("model", self.config.model))


class MockEngine(BaseEngine):
    """Offline mock engine for demos without API key."""

    name = "mock"

    def __init__(self, model: str = "mock-1"):
        self.model = model

    def generate(self, messages: list[Message], **kwargs) -> AgentResponse:
        # Simple heuristic mock
        last_user = next((m.content for m in reversed(messages) if str(m.role) == "user"), "")
        if "brief" in last_user.lower() or "meeting" in last_user.lower():
            content = (
                "**Mock Brief (offline mode)**\n\n"
                f"- Purpose: Summarize context ({len(last_user)} chars)\n"
                "- Attendees: Not specified (in mock mode, paste details)\n"
                "- Desired outcome: Demo of local-first stack\n"
                "- Bring: Laptop, notes, API key for real generation\n"
                "- Questions: What is the goal? What does success look like? Risks?\n"
                "- Risk: Mock mode doesn't call cloud; set OPENAI_API_KEY for real output.\n\n"
                f"Context preview: {last_user[:200]}..."
            )
        elif "code" in last_user.lower():
            content = (
                "```python\n# Mock code assistant (offline)\n"
                "def hello():\n    print('Hello from JARVIS mock engine')\n    print('Set OPENAI_API_KEY or run ollama for real inference')\n```"
            )
        else:
            content = (
                f"[MOCK ENGINE] You said: {last_user[:500]}\n\n"
                "I'm running in offline mock mode. To enable real AI:\n"
                "1. Set OPENAI_API_KEY env var\n"
                "2. Or run `ollama serve` and use --engine ollama\n"
                "3. Or install a local model via `jarvis model pull`\n\n"
                "This demonstrates the local-first architecture without cloud calls."
            )
        return AgentResponse(content=content, model=self.model, usage={"prompt_tokens": len(last_user)//4, "completion_tokens": len(content)//4})

    async def agenerate(self, messages: list[Message], **kwargs) -> AgentResponse:
        return self.generate(messages, **kwargs)
