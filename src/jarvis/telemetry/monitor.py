"""Telemetry — energy, latency, cost tracking (lightweight)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from jarvis.core.config import get_home


@dataclass
class TelemetryRecord:
    timestamp: float
    agent: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    energy_joules: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TelemetryStore:
    def __init__(self, home: Path | None = None):
        self.home = home or get_home()
        self.dir = self.home / "telemetry"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file = self.dir / "telemetry.jsonl"

    def log(self, record: TelemetryRecord):
        with self.file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def recent(self, limit: int = 50) -> list[TelemetryRecord]:
        if not self.file.exists():
            return []
        lines = self.file.read_text(encoding="utf-8").splitlines()[-limit:]
        out = []
        for line in lines:
            try:
                data = json.loads(line)
                out.append(TelemetryRecord(**data))
            except Exception:
                continue
        return out


class TelemetrySession:
    def __init__(self, agent: str, model: str):
        self.agent = agent
        self.model = model
        self.start = time.time()
        self.store = TelemetryStore()

    def end(self, usage: dict[str, int] | None = None, metadata: dict | None = None):
        latency = int((time.time() - self.start) * 1000)
        usage = usage or {}
        rec = TelemetryRecord(
            timestamp=self.start,
            agent=self.agent,
            model=self.model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency,
            metadata=metadata or {},
        )
        self.store.log(rec)
        return rec
