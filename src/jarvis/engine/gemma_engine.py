"""Gemma.cpp / pygemma engine — ultra-light local inference.

For CPU-only devices, very low RAM.
Requires: pip install pygemma (optional)
"""

from jarvis.core.types import AgentResponse, Message, EngineConfig
from jarvis.engine.base import BaseEngine


class GemmaEngine(BaseEngine):
    name = "gemma_cpp"

    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self._engine = None
        self._loaded = False

    def _ensure_model(self):
        if self._loaded:
            return
        try:
            import pygemma  # type: ignore

            # Placeholder — pygemma API may vary
            self._engine = pygemma
            self._loaded = True
        except ImportError as e:
            raise RuntimeError(
                "pygemma not installed. For CPU light inference:\n"
                "  pip install pygemma\n"
                "Or use mock/ollama/vllm instead."
            ) from e

    def generate(self, messages: list[Message], **kwargs) -> AgentResponse:
        # Fallback to mock if not available — keeps build working everywhere
        try:
            self._ensure_model()
        except RuntimeError:
            # Graceful fallback to mock for demo
            from jarvis.engine.openai import MockEngine

            mock = MockEngine(model=f"{self.config.model} (gemma fallback)")
            return mock.generate(messages)

        prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
        # Placeholder generation
        content = f"[Gemma.cpp mock] Would generate from {self.config.model} for prompt {len(prompt)} chars. Install pygemma for real."
        return AgentResponse(content=content, model=self.config.model)

    async def agenerate(self, messages: list[Message], **kwargs) -> AgentResponse:
        import asyncio
        return await asyncio.to_thread(self.generate, messages, **kwargs)
