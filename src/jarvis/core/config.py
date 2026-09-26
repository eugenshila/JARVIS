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
    "business-os": AgentPreset(
        name="business-os",
        description="Business OS — Knows goals, priorities, workflows, rules, standards, persistent memory, OpenAI brain, SHILATECH COO",
        system_prompt="You are JARVIS Business OS — COO for Eugene at SHILATECH. You know goals, priorities, business, workflows, rules, standards from persistent memory. Use OpenAI gpt-4o-mini for best quality. Be proactive, enforce SHILATECH standards, align to north star, remember everything via vector memory.",
        tools=["memory_search", "memory_write", "file_read", "file_write", "shell", "web_search", "tavily_search", "ddgs_search", "business_profile", "business_goals", "business_priorities", "business_workflows", "business_rules", "business_memory", "task_breakdown", "day_planner", "focus", "quick_capture", "win_tracker", "calendar", "weather", "proactive_briefing", "network_status", "hybrid_mode"],
    ),
    "shilatech": AgentPreset(
        name="shilatech",
        description="SHILATECH Business OS — Same as business-os, premium branding",
        system_prompt="You are JARVIS SHILATECH Business OS — Personal AI COO for Eugene. SHILATECH • Malibu Point 10880. Knows goals, priorities, workflows, rules. OpenAI brain, persistent memory, modern circular HUD, voice auto-init.",
        tools=["memory_search", "memory_write", "business_profile", "business_goals", "business_priorities", "business_workflows", "business_rules", "business_memory", "web_search", "file_read", "file_write"],
    ),
}


@dataclass
class AutoConfig:
    online_engine: str = "auto"  # auto, openai, ollama, vllm, mlx, mock
    offline_engine: str = "mock"  # mock, ollama
    cache_seconds: int = 30
    enabled: bool = True


@dataclass
class JarvisConfig:
    home: Path = field(default_factory=get_home)
    engine: EngineConfig = field(default_factory=EngineConfig)
    auto: AutoConfig = field(default_factory=AutoConfig)
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
                try:
                    eng_type = EngineType(eng.get("type", "openai"))
                except ValueError:
                    eng_type_str = eng.get("type", "openai")
                    if eng_type_str == "auto":
                        eng_type = EngineType.AUTO
                    else:
                        eng_type = EngineType(eng_type_str) if eng_type_str in [e.value for e in EngineType] else EngineType.OPENAI
                cfg.engine = EngineConfig(
                    type=eng_type,
                    model=eng.get("model", cfg.engine.model),
                    api_url=eng.get("api_url", cfg.engine.api_url),
                    api_key=eng.get("api_key", cfg.engine.api_key),
                    temperature=eng.get("temperature", 0.7),
                    max_tokens=eng.get("max_tokens", 2048),
                )
            auto_cfg = data.get("auto", {})
            if auto_cfg:
                cfg.auto = AutoConfig(
                    online_engine=auto_cfg.get("online_engine", "auto"),
                    offline_engine=auto_cfg.get("offline_engine", "mock"),
                    cache_seconds=auto_cfg.get("cache_seconds", 30),
                    enabled=auto_cfg.get("enabled", True),
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
            eng.add(tomlkit.comment("api_key is read from OPENAI_API_KEY env"))
        doc["engine"] = eng
        auto_tbl = tomlkit.table()
        auto_tbl["online_engine"] = self.auto.online_engine
        auto_tbl["offline_engine"] = self.auto.offline_engine
        auto_tbl["cache_seconds"] = self.auto.cache_seconds
        auto_tbl["enabled"] = self.auto.enabled
        auto_tbl.add(tomlkit.comment("Hybrid mode: online=full stack (openai/ollama), offline=basic (mock/ollama)"))
        auto_tbl.add(tomlkit.comment("For i5-6300U 8GB: online=openai best, offline=mock or ollama tinyllama"))
        doc["auto"] = auto_tbl
        tel = tomlkit.table()
        tel["enabled"] = self.telemetry_enabled
        doc["telemetry"] = tel
        self.config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    def get_preset(self) -> AgentPreset:
        return PRESETS.get(self.preset, PRESETS["chat-simple"])
