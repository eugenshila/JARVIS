"""Skill abstraction — agentskills.io compatible."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Skill:
    name: str
    description: str
    prompt: str
    source: str = "local"
    tags: list[str] = field(default_factory=list)
    path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "tags": self.tags,
        }
