"""MLX engine — Apple Silicon native inference via mlx-lm.

Requires macOS 13+ on Apple Silicon.
Install: pip install -e .[inference-mlx]
Model: mlx-community/Llama-3.2-3B-Instruct-4bit, etc
"""

from __future__ import annotations

from jarvis.core.types import AgentResponse, Message, EngineConfig
from jarvis.engine.base import BaseEngine


class MLXEngine(BaseEngine):
    name = "mlx"

    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self._model = None
        self._tokenizer = None
        self._loaded = False

    def _ensure_model(self):
        if self._loaded:
            return
        try:
            from mlx_lm import load, generate  # type: ignore

            model_path = self.config.model
            # mlx-community models auto-download via HF
            self._model, self._tokenizer = load(model_path)
            self._generate_fn = generate
            self._loaded = True
        except ImportError as e:
            raise RuntimeError(
                "mlx-lm not installed. On macOS Apple Silicon:\n"
                "  pip install -e .[inference-mlx]\n"
                "Models: mlx-community/Llama-3.2-3B-Instruct-4bit"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to load MLX model {self.config.model}: {e}") from e

    def generate(self, messages: list[Message], **kwargs) -> AgentResponse:
        self._ensure_model()

        prompt = self._chat_to_prompt(messages)

        # MLX generation
        response = self._generate_fn(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=self.config.max_tokens,
            temp=self.config.temperature,
            verbose=False,
        )

        # response may contain prompt, strip if needed
        if response.startswith(prompt):
            response = response[len(prompt):].lstrip()

        return AgentResponse(
            content=response,
            model=self.config.model,
            usage={"prompt_tokens": len(prompt)//4, "completion_tokens": len(response)//4},
        )

    async def agenerate(self, messages: list[Message], **kwargs) -> AgentResponse:
        import asyncio
        return await asyncio.to_thread(self.generate, messages, **kwargs)

    def _chat_to_prompt(self, messages: list[Message]) -> str:
        # ChatML-ish
        out = []
        for m in messages:
            role = str(m.role)
            out.append(f"<|im_start|>{role}\n{m.content}<|im_end|>\n")
        out.append("<|im_start|>assistant\n")
        return "\n".join(out)

    def describe(self):
        return {"name": self.name, "model": self.config.model, "backend": "mlx", "loaded": self._loaded}
