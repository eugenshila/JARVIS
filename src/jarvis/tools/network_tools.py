"""
Network + Hybrid Mode Tools — for online full stack / offline basic

Tools:
- network_status: check if online, what engines available, what will be used
- hybrid_mode: configure online/offline engines, enable/disable auto
- online_status: alias
"""

from __future__ import annotations

import os
from typing import Dict, Any

from jarvis.tools.base import BaseTool, ToolSpec
from jarvis.core.network import get_auto_status, check_online, check_engines, pick_best_engine
from jarvis.core.config import JarvisConfig


class NetworkStatusTool(BaseTool):
    spec = ToolSpec(
        name="network_status",
        description="Network + Hybrid Mode Status — checks if online/offline, what engines available (openai, ollama, vllm, etc.), what engine will be used auto. For i5-6300U 8GB: online openai best, offline mock/tinyllama.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "status, check, engines, pick", "default": "status"},
            },
            "required": [],
        },
    )

    def run(self, action: str = "status", **kwargs) -> str:
        if action == "check":
            net = check_online()
            if net.online:
                return f"🌐 **ONLINE** — {net.method} {net.latency_ms}ms — Full stack available, Sir.\n\nLatency: {net.latency_ms}ms via {net.method}"
            else:
                return f"📴 **OFFLINE** — {net.method} error: {net.error} — Basic mode, Sir.\n\nNo internet, using mock + local only. Go online for full stack."

        elif action == "engines":
            eng = check_engines()
            lines = ["**Engines Availability — Your Machine:**", ""]
            for key, detail in eng.details.items():
                ok = getattr(eng, key, False) if hasattr(eng, key) else False
                icon = "✅" if ok else "⚠️" if "Running" in str(detail) or "set" in str(detail).lower() else "❌"
                lines.append(f"{icon} {key}: {detail}")
            lines.extend(["", "**For your i5-6300U 8GB:**", "• Online best: openai (no RAM) or ollama tinyllama/phi3:mini", "• Offline best: mock (always works) or ollama tinyllama offline", "• Skip: vLLM needs NVIDIA GPU, MLX needs Mac"])
            return "\n".join(lines)

        else:
            status = get_auto_status()
            net = status["network"]
            eng = status["engines"]
            sel = status["selected"]
            prefs = status["prefs"]

            online_icon = "🌐 ONLINE" if net["online"] else "📴 OFFLINE"
            mode = sel["mode"]

            out = [
                f"**Hybrid Mode Status — {online_icon} — {mode}**",
                "",
                f"**Network:** {'Online' if net['online'] else 'Offline'} via {net['method']}" + (f" {net['latency_ms']}ms" if net['latency_ms'] else "") + (f" — Error: {net['error']}" if net['error'] else ""),
                "",
                f"**Selected Engine:** {sel['engine']} — {sel['reason']}",
                f"**Mode:** {mode}",
                "",
                f"**Prefs:** online_engine={prefs['online_engine']} offline_engine={prefs['offline_engine']} (from config.toml [auto])",
                "",
                "**Engines:**",
            ]
            for k in ["openai", "ollama", "vllm", "mlx", "anthropic", "tavily", "faiss"]:
                ok = eng.get(k, False)
                icon = "✅" if ok else "❌"
                detail = eng["details"].get(k, "")
                out.append(f"  {icon} {k}: {detail}")

            out.extend([
                "",
                "**What happens:**",
                "• Online + OPENAI_API_KEY → openai full stack (best for 8GB, no RAM)",
                "• Online + Ollama running → ollama full local (tinyllama/phi3:mini for 8GB)",
                "• Offline + Ollama running → ollama offline (still works offline!)",
                "• Offline no Ollama → mock basic (always works, keyword memory, local calendar/email mock)",
                "",
                "**For your i5-6300U 8GB:**",
                "• Online: Use openai — fastest, no RAM pressure, Sir",
                "• Offline: Use mock basic or ollama tinyllama 1.1B (~8-10 tokens/sec)",
                "• Avoid: 7B+ models on 8GB — will swap and freeze",
                "",
                f"**Current:** {sel['engine']} — {mode}",
                "",
                "**Configure:**",
                "• `jarvis config set auto.online_engine openai`",
                "• `jarvis config set auto.offline_engine mock`",
                "• Or edit ~/.jarvis/config.toml [auto] section",
                "• `jarvis ask --engine auto 'hello'` for auto mode",
            ])
            return "\n".join(out)


class HybridModeTool(BaseTool):
    spec = ToolSpec(
        name="hybrid_mode",
        description="Hybrid Mode Config — configure online full stack vs offline basic. Set online_engine (auto/openai/ollama/vllm/mock) and offline_engine (mock/ollama). For i5-6300U 8GB: online openai, offline mock.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "status, set, enable, disable", "default": "status"},
                "online_engine": {"type": "string", "description": "Engine when online: auto, openai, ollama, vllm, mlx, mock", "default": "auto"},
                "offline_engine": {"type": "string", "description": "Engine when offline: mock, ollama", "default": "mock"},
            },
            "required": [],
        },
    )

    def run(self, action: str = "status", online_engine: str = "auto", offline_engine: str = "mock", **kwargs) -> str:
        cfg = JarvisConfig.load()

        if action == "status":
            status = get_auto_status()
            return f"""**Hybrid Mode Config:**

**Current Prefs (from ~/.jarvis/config.toml [auto]):**
  online_engine = {status['prefs']['online_engine']} (auto = best available: openai > ollama > vllm > mlx > mock)
  offline_engine = {status['prefs']['offline_engine']} (mock = always works, ollama = local offline if running)
  cache_seconds = {cfg.auto.cache_seconds}
  enabled = {cfg.auto.enabled}

**Current Selection:**
  Network: {'🌐 Online' if status['network']['online'] else '📴 Offline'} via {status['network']['method']}
  Engine: {status['selected']['engine']} — {status['selected']['mode']}
  Reason: {status['selected']['reason']}

**For your i5-6300U 8GB:**
  • Online: openai (best, no RAM, fast) or ollama tinyllama/phi3:mini (local but slower)
  • Offline: mock (basic, always works) or ollama tinyllama offline (still works offline!)

**Set:**
  hybrid_mode set online_engine openai offline_engine mock
  hybrid_mode set online_engine ollama offline_engine ollama
  hybrid_mode enable / disable

**Use:**
  jarvis ask --engine auto 'Good morning Eugene'
  # Auto picks online/offline engine each request, cached 30 sec
"""

        elif action == "set":
            cfg.auto.online_engine = online_engine
            cfg.auto.offline_engine = offline_engine
            cfg.save()
            status = get_auto_status()
            return f"""✅ **Hybrid Mode Set:**

  online_engine = {online_engine}
  offline_engine = {offline_engine}

Saved to ~/.jarvis/config.toml [auto]

**Now:**
  Network: {'🌐 Online' if status['network']['online'] else '📴 Offline'}
  Selected: {status['selected']['engine']} — {status['selected']['mode']}
  Reason: {status['selected']['reason']}

Test: jarvis ask --engine auto 'Good morning Eugene'
"""

        elif action == "enable":
            cfg.auto.enabled = True
            cfg.save()
            return f"✅ **Hybrid Mode ENABLED** — Auto online/offline switching ON, Sir.\n\nOnline: full stack ({cfg.auto.online_engine}), Offline: basic ({cfg.auto.offline_engine})\n\nConfig: ~/.jarvis/config.toml [auto] enabled=true"

        elif action == "disable":
            cfg.auto.enabled = False
            cfg.save()
            return f"⚠️ **Hybrid Mode DISABLED** — Auto switching OFF, Sir.\n\nNow uses fixed engine from [engine] type={cfg.engine.type.value}\n\nEnable: hybrid_mode enable"

        else:
            return self.run(action="status")
