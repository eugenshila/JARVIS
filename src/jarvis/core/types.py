"""Core type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: Role | str
    content: str
    name: str | None = None
    tool_call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": str(self.role), "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class AgentResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    model: str = ""
    finished: bool = True


class EngineType(str, Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"
    LOCAL = "local"
    ANTHROPIC = "anthropic"
    MOCK = "mock"
    VLLM = "vllm"
    MLX = "mlx"
    LITELLM = "litellm"
    GEMMA_CPP = "gemma_cpp"


@dataclass
class EngineConfig:
    type: EngineType = EngineType.OPENAI
    model: str = "gpt-4o-mini"
    api_url: str = "https://api.openai.com/v1/chat/completions"
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class MemoryEntry:
    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
