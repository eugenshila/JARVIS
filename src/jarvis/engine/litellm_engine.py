"""LiteLLM engine — unified gateway to 100+ providers (OpenAI, Anthropic, Gemini, Bedrock, etc).

Requires: pip install -e .[inference-litellm]
Useful for cloud fallback when local insufficient.
"""

from __future__ import annotations

from jarvis.core.types import AgentResponse, Message, EngineConfig
from jarvis.engine.base import BaseEngine


class LiteLLMEngine(BaseEngine):
    name = "litellm"

    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()

    def generate(self, messages: list[Message], **kwargs) -> AgentResponse:
        try:
            import litellm  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "litellm not installed. Run: pip install -e .[inference-litellm]\n"
                "Then set e.g., ANTHROPIC_API_KEY, GOOGLE_API_KEY, etc."
            ) from e

        # Convert to litellm format
        litellm_messages = [{"role": str(m.role), "content": m.content} for m in messages]

        try:
            resp = litellm.completion(
                model=self.config.model,
                messages=litellm_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            content = resp.choices[0].message.content or ""
            usage = getattr(resp, "usage", {}) or {}
            if hasattr(usage, "model_dump"):
                usage = usage.model_dump()
            elif not isinstance(usage, dict):
                usage = {"prompt_tokens": 0, "completion_tokens": 0}
            return AgentResponse(content=content, model=resp.model, usage=usage)
        except Exception as e:
            raise RuntimeError(f"LiteLLM error with model {self.config.model}: {e}") from e

    async def agenerate(self, messages: list[Message], **kwargs) -> AgentResponse:
        try:
            import litellm  # type: ignore

            litellm_messages = [{"role": str(m.role), "content": m.content} for m in messages]
            resp = await litellm.acompletion(
                model=self.config.model,
                messages=litellm_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            content = resp.choices[0].message.content or ""
            usage = getattr(resp, "usage", {}) or {}
            return AgentResponse(content=content, model=resp.model, usage=usage if isinstance(usage, dict) else {})
        except ImportError:
            import asyncio
            return await asyncio.to_thread(self.generate, messages, **kwargs)
        except Exception as e:
            raise RuntimeError(f"LiteLLM async error: {e}") from e

    def describe(self):
        return {"name": self.name, "model": self.config.model, "backend": "litellm"}
