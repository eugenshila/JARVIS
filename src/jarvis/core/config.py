"""Configuration management — local-first, TOML-based."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

import tomlkit

from jarvis.core.types import EngineConfig, EngineType


def get_home() -> Path:
    env_home = os.environ.get("JARVIS_HOME") or os.environ.get("OPENJARVIS_HOME")
    if env_home:
        return Path(env_home).expanduser()
    return Path.home() / ".jarvis"


@dataclass
class AgentPreset:
    name: str
    description: str
    system_prompt: str
    tools: list[str] = field(default_factory=list)
    engine: str = "default"


PRESETS: dict[str, AgentPreset] = {
    "chat-simple": AgentPreset(
        name="chat-simple",
        description="Lightweight conversation, no tools",
        system_prompt="You are JARVIS, a helpful personal AI that runs locally. Be concise, accurate, and private. Use only supplied context for personal facts.",
        tools=[],
    ),
    "morning-digest": AgentPreset(
        name="morning-digest",
        description="Spoken daily briefing from email, calendar, health, news",
        system_prompt="You are JARVIS morning digest. Build a concise briefing: top emails, today's calendar, health snapshot, news highlights. Keep under 300 words. Distinguish facts from inferences.",
        tools=["gmail", "calendar", "web_search", "memory_search"],
    ),
    "deep-research": AgentPreset(
        name="deep-research",
        description="Multi-hop research across indexed docs with citations",
        system_prompt="You are a deep research agent. Break queries into sub-questions, search web and local docs, synthesize with citations. Never invent sources. Mark uncertainty.",
        tools=["web_search", "memory_search", "file_read", "file_write"],
    ),
    "code-assistant": AgentPreset(
        name="code-assistant",
        description="Agent with code execution, file I/O, and shell access",
        system_prompt="You are JARVIS code assistant. Help with coding: read files, execute code safely, explain, refactor. Ask before destructive actions. Provide runnable examples.",
        tools=["file_read", "file_write", "shell", "code_exec"],
    ),
    "scheduled-monitor": AgentPreset(
        name="scheduled-monitor",
        description="Stateful agent on a schedule with memory",
        system_prompt="You are a monitoring agent. Track changes, remember state across runs, alert on important events. Be concise and actionable.",
        tools=["memory_search", "memory_write", "web_search", "file_read"],
    ),
}


@dataclass
class JarvisConfig:
    home: Path = field(default_factory=get_home)
    engine: EngineConfig = field(default_factory=EngineConfig)
    preset: str = "chat-simple"
    telemetry_enabled: bool = False
    data_dir: Path | None = None

    def __post_init__(self):
        if self.data_dir is None:
            self.data_dir = self.home / "data"
        # env overrides
        if os.environ.get("OPENAI_API_KEY"):
            self.engine.api_key = os.environ["OPENAI_API_KEY"]
        if os.environ.get("JARVIS_API_URL"):
            self.engine.api_url = os.environ["JARVIS_API_URL"]
        if os.environ.get("JARVIS_MODEL"):
            self.engine.model = os.environ["JARVIS_MODEL"]

    @property
    def config_path(self) -> Path:
        return self.home / "config.toml"

    @classmethod
    def load(cls, home: Path | None = None) -> JarvisConfig:
        cfg = cls(home=home or get_home())
        path = cfg.config_path
        if not path.exists():
            return cfg
        try:
            text = path.read_text(encoding="utf-8")
            data = tomllib.loads(text)
            eng = data.get("engine", {})
            if eng:
                cfg.engine = EngineConfig(
                    type=EngineType(eng.get("type", "openai")),
                    model=eng.get("model", cfg.engine.model),
                    api_url=eng.get("api_url", cfg.engine.api_url),
                    api_key=eng.get("api_key", cfg.engine.api_key),
                    temperature=eng.get("temperature", 0.7),
                    max_tokens=eng.get("max_tokens", 2048),
                )
            cfg.preset = data.get("preset", cfg.preset)
            cfg.telemetry_enabled = data.get("telemetry", {}).get("enabled", False)
        except Exception:
            pass
        return cfg

    def save(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        doc = tomlkit.document()
        doc["preset"] = self.preset
        eng = tomlkit.table()
        eng["type"] = self.engine.type.value
        eng["model"] = self.engine.model
        eng["api_url"] = self.engine.api_url
        eng["temperature"] = self.engine.temperature
        eng["max_tokens"] = self.engine.max_tokens
        if self.engine.api_key and len(self.engine.api_key) > 8:
            # don't write key to disk by default; keep env-based
            eng.add(tomlkit.comment("api_key is read from OPENAI_API_KEY env"))
        doc["engine"] = eng
        tel = tomlkit.table()
        tel["enabled"] = self.telemetry_enabled
        doc["telemetry"] = tel
        self.config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    def get_preset(self) -> AgentPreset:
        return PRESETS.get(self.preset, PRESETS["chat-simple"])
