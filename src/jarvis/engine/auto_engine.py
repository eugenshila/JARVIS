"""
Auto Engine — Hybrid Online/Offline that picks best engine automatically.

User wants: installed locally but when online run full stack online, when offline run basic one.

This engine:
- Checks network online/offline on each request (cached 30 sec)
- Checks what engines available (openai key, ollama, etc.)
- Picks best: online -> openai/ollama, offline -> mock/ollama offline
- Delegates to real engine (OpenAI, Ollama, Mock, etc.)
- For i5-6300U + 8GB: online openai best (no RAM), offline mock or tinyllama

Usage:
  jarvis ask "hello" --engine auto
  jarvis ask "hello" --engine auto --online-engine openai --offline-engine mock

Or set in config.toml:
  [auto]
  online_engine = "openai"  # or "ollama", "auto"
  offline_engine = "mock"   # or "ollama"
  cache_seconds = 30
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

from jarvis.core.types import EngineConfig, EngineType, Message, AgentResponse
from jarvis.engine.base import BaseEngine
from jarvis.core.network import check_online, check_engines, pick_best_engine, get_auto_status
from jarvis.engine.registry import get_engine


class AutoEngine(BaseEngine):
    """
    Auto engine that switches online/offline automatically.
    - Online: full stack (openai, ollama, vllm, etc.)
    - Offline: basic (mock or ollama offline)
    """

    def __init__(self, config: EngineConfig, online_engine: str = "auto", offline_engine: str = "mock", cache_seconds: int = 30):
        # Don't call super().__init__(config) because BaseEngine has no __init__ with args
        self.config = config
        self.name = "auto"
        self.online_engine_pref = online_engine
        self.offline_engine_pref = offline_engine
        self.cache_seconds = cache_seconds
        self._last_check = 0
        self._cached_status: Optional[dict] = None
        self._cached_engine_name: Optional[str] = None
        self._cached_engine_instance: Optional[BaseEngine] = None

    def _get_status(self, force: bool = False) -> dict:
        now = time.time()
        if not force and self._cached_status and (now - self._last_check) < self.cache_seconds:
            return self._cached_status

        status = get_auto_status()
        # Override prefs if passed explicitly
        if self.online_engine_pref != "auto":
            status["prefs"]["online_engine"] = self.online_engine_pref
        if self.offline_engine_pref != "mock":
            status["prefs"]["offline_engine"] = self.offline_engine_pref

        # Re-pick with overridden prefs
        from jarvis.core.network import NetworkStatus, EngineAvailability
        network = status["network"]
        engines = status["engines"]

        # Reconstruct objects for pick_best_engine
        net = type('obj', (object,), {
            'online': network['online'],
            'method': network['method'],
            'latency_ms': network['latency_ms'],
            'error': network['error']
        })()
        eng = type('obj', (object,), {
            'openai': engines['openai'],
            'ollama': engines['ollama'],
            'vllm': engines['vllm'],
            'mlx': engines['mlx'],
            'anthropic': engines['anthropic'],
            'tavily': engines['tavily'],
            'faiss': engines['faiss'],
            'details': engines['details']
        })()

        engine_name, reason = pick_best_engine(net, eng, self.online_engine_pref, self.offline_engine_pref)
        status["selected"]["engine"] = engine_name
        status["selected"]["reason"] = reason

        self._cached_status = status
        self._last_check = now
        return status

    def _get_engine(self) -> BaseEngine:
        status = self._get_status()
        engine_name = status["selected"]["engine"]

        # If cached engine matches, reuse
        if self._cached_engine_name == engine_name and self._cached_engine_instance:
            return self._cached_engine_instance

        # Create new engine instance
        # Use same config but override type
        from jarvis.core.config import JarvisConfig
        cfg = JarvisConfig.load()
        # Preserve model, api_url, etc.
        engine = get_engine(cfg, engine_type=engine_name)

        self._cached_engine_name = engine_name
        self._cached_engine_instance = engine
        return engine

    def get_status(self) -> dict:
        return self._get_status(force=True)

    def generate(self, messages: List[Message], **kwargs) -> AgentResponse:
        # For base compatibility, delegate to chat
        tools = kwargs.get("tools")
        return self.chat(messages, tools=tools, **kwargs)

    async def agenerate(self, messages: List[Message], **kwargs) -> AgentResponse:
        # Async version — same as sync for now
        return self.generate(messages, **kwargs)

    def chat(self, messages: List[Message], tools: Optional[List[dict]] = None, **kwargs) -> AgentResponse:
        engine = self._get_engine()
        status = self._get_status()

        # Add auto info to response if mock fallback
        try:
            # Engines have generate, not chat — try both
            if hasattr(engine, 'chat'):
                resp = engine.chat(messages, tools=tools, **kwargs)
            elif hasattr(engine, 'generate'):
                resp = engine.generate(messages, **kwargs)
            else:
                return AgentResponse(content=f"Engine {engine} has no chat/generate", finished=True)

            # If we are in auto mode, prepend mode info for first message or if offline
            if not status["network"]["online"] or status["selected"]["engine"] == "mock":
                # Only add note if offline or mock, to be transparent
                mode = status["selected"]["mode"]
                reason = status["selected"]["reason"]
                # Don't modify content too much, just add small footer if offline
                if not status["network"]["online"]:
                    resp.content = f"📴 **OFFLINE MODE — Basic** ({reason})\n\n{resp.content}\n\n---\n*Offline: mock + keyword memory + local calendar/email mock. Go online for full stack: OpenAI or Ollama tinyllama*"
                elif status["selected"]["engine"] == "mock" and status["network"]["online"]:
                    resp.content = f"🌐 **ONLINE BUT BASIC** ({reason})\n\n{resp.content}\n\n---\n*Online but no LLM key: mock LLM + online search. Set OPENAI_API_KEY for full stack online, Sir.*"

            return resp
        except Exception as e:
            # If selected engine fails, fallback to mock
            if status["selected"]["engine"] != "mock":
                try:
                    from jarvis.engine.openai import MockEngine
                    mock = MockEngine(model="mock")
                    resp = mock.chat(messages, tools=tools, **kwargs)
                    resp.content = f"⚠️ **{status['selected']['engine']} failed: {e} — Fallback to mock**\n\n{resp.content}"
                    return resp
                except Exception as e2:
                    return AgentResponse(content=f"Auto engine failed: {e}, fallback also failed: {e2}", finished=True)
            else:
                return AgentResponse(content=f"Auto engine (mock) failed: {e}", finished=True)

    def __repr__(self):
        status = self._get_status()
        return f"AutoEngine(online={status['network']['online']}, selected={status['selected']['engine']}, mode={status['selected']['mode']})"
