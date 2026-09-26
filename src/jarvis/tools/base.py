"""Tool abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema
    requires_approval: bool = False


class BaseTool(ABC):
    spec: ToolSpec

    @abstractmethod
    def run(self, **kwargs) -> str:
        ...

    async def arun(self, **kwargs) -> str:
        return self.run(**kwargs)

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.spec.name,
                "description": self.spec.description,
                "parameters": self.spec.parameters,
            },
        }
