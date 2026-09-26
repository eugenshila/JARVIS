"""Engine abstraction — base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Iterator

from jarvis.core.types import AgentResponse, Message


class BaseEngine(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, messages: list[Message], **kwargs) -> AgentResponse:
        ...

    @abstractmethod
    async def agenerate(self, messages: list[Message], **kwargs) -> AgentResponse:
        ...

    def stream(self, messages: list[Message], **kwargs) -> Iterator[str]:
        resp = self.generate(messages, **kwargs)
        yield resp.content

    async def astream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        resp = await self.agenerate(messages, **kwargs)
        yield resp.content

    def can_serve(self, model: str) -> bool:
        return True

    def describe(self) -> dict:
        return {"name": self.name}
