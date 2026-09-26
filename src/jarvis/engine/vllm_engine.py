"""vLLM engine — high-throughput local inference.

Requires: pip install -e .[inference-vllm]
Model: e.g., meta-llama/Meta-Llama-3-8B-Instruct, mistralai/Mistral-7B-Instruct-v0.2
"""

from __future__ import annotations

from typing import Any

from jarvis.core.types import AgentResponse, Message, EngineConfig
from jarvis.engine.base import BaseEngine


class VLLMEngine(BaseEngine):
    name = "vllm"

    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self._engine = None
        self._tokenizer = None
        self._model_loaded = False

    def _ensure_model(self):
        if self._model_loaded:
            return
        try:
            from vllm import LLM, SamplingParams  # type: ignore

            # Lazy load — model name from config
            model_name = self.config.model
            # For quantized or small models, adjust
            self._engine = LLM(model=model_name, dtype="auto", trust_remote_code=True)
            self._SamplingParams = SamplingParams
            self._model_loaded = True
        except ImportError as e:
            raise RuntimeError(
                "vLLM not installed. Run: pip install -e .[inference-vllm]\n"
                "Also needs CUDA or CPU build. See https://docs.vllm.ai/"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to load vLLM model {self.config.model}: {e}") from e

    def generate(self, messages: list[Message], **kwargs) -> AgentResponse:
        self._ensure_model()

        # Convert chat to prompt
        prompt = self._chat_to_prompt(messages)

        sampling = self._SamplingParams(
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        outputs = self._engine.generate([prompt], sampling)
        text = outputs[0].outputs[0].text if outputs else ""

        # vLLM doesn't give token counts easily, estimate
        prompt_tokens = len(prompt) // 4
        comp_tokens = len(text) // 4

        return AgentResponse(
            content=text,
            model=self.config.model,
            usage={"prompt_tokens": prompt_tokens, "completion_tokens": comp_tokens, "total_tokens": prompt_tokens + comp_tokens},
        )

    async def agenerate(self, messages: list[Message], **kwargs) -> AgentResponse:
        import asyncio

        return await asyncio.to_thread(self.generate, messages, **kwargs)

    def _chat_to_prompt(self, messages: list[Message]) -> str:
        # Simple chat template — for Llama/Mistral style
        parts = []
        for m in messages:
            role = str(m.role)
            if role == "system":
                parts.append(f"<|system|>\n{m.content}\n")
            elif role == "user":
                parts.append(f"<|user|>\n{m.content}\n")
            elif role == "assistant":
                parts.append(f"<|assistant|>\n{m.content}\n")
        parts.append("<|assistant|>\n")
        return "\n".join(parts)

    def describe(self):
        return {"name": self.name, "model": self.config.model, "backend": "vllm", "loaded": self._model_loaded}
