"""Agent base."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from jarvis.core.config import JarvisConfig, AgentPreset
from jarvis.core.types import AgentResponse, Message, Role
from jarvis.engine.base import BaseEngine
from jarvis.engine.registry import get_engine
from jarvis.tools.registry import get_tools


class BaseAgent(ABC):
    name: str = "base"
    description: str = "Base agent"

    def __init__(self, config: JarvisConfig | None = None, engine: BaseEngine | None = None, preset: AgentPreset | None = None):
        self.config = config or JarvisConfig.load()
        self.engine = engine or get_engine(self.config)
        self.preset = preset or self.config.get_preset()
        self.tools = get_tools(self.preset.tools)

    def _system_message(self) -> Message:
        return Message(role=Role.SYSTEM, content=self.preset.system_prompt)

    @abstractmethod
    def run(self, prompt: str, context: str = "", **kwargs) -> AgentResponse:
        ...

    async def arun(self, prompt: str, context: str = "", **kwargs) -> AgentResponse:
        # default async via thread
        import asyncio

        return await asyncio.to_thread(self.run, prompt, context, **kwargs)

    def _build_messages(self, prompt: str, context: str = "") -> list[Message]:
        msgs: list[Message] = [self._system_message()]
        if context:
            msgs.append(Message(role=Role.USER, content=f"Context:\n{context}\n\nTask:\n{prompt}"))
        else:
            msgs.append(Message(role=Role.USER, content=prompt))
        return msgs
