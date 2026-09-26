"""
Network + Hybrid Mode Tools — for online full stack / offline basic
SHILATECH branding, interactive decision when online.

Tools:
- network_status: check if online, what engines available, what will be used
- hybrid_mode: configure online/offline engines, enable/disable auto, interactive decision
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
        description="Network + Hybrid Mode Status — SHILATECH — checks if online/offline, what engines available (openai, ollama, vllm, etc.), what engine will be used auto. For i5-6300U 8GB: online openai best, offline mock/tinyllama. Interactive decision when online.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "status, check, engines, pick, interactive", "default": "status"},
            },
            "required": [],
        },
    )

    def run(self, action: str = "status", **kwargs) -> str:
        if action == "check":
            net = check_online()
            if net.online:
                return f"🌐 **ONLINE — SHILATECH** — {net.method} {net.latency_ms}ms — Full stack available, Sir.\n\nLatency: {net.latency_ms}ms via {net.method}\n\nYou can still decide: Full Stack Online vs Basic Offline Local — hybrid_mode interactive"
            else:
                return f"📴 **OFFLINE — SHILATECH** — {net.method} error: {net.error} — Basic mode, Sir.\n\nNo internet, using mock + local only. Go online for full stack. Same circular interface, only badge changes."

        elif action == "engines":
            eng = check_engines()
            lines = ["**Engines Availability — Your Machine — SHILATECH:**", ""]
            for key, detail in eng.details.items():
                ok = getattr(eng, key, False) if hasattr(eng, key) else False
                icon = "✅" if ok else "⚠️" if "Running" in str(detail) or "set" in str(detail).lower() else "❌"
                lines.append(f"{icon} {key}: {detail}")
            lines.extend(["", "**For your i5-6300U 8GB — SHILATECH:**", "• Online best: openai (no RAM) or ollama tinyllama/phi3:mini", "• Offline best: mock (always works) or ollama tinyllama offline", "• Skip: vLLM needs NVIDIA GPU, MLX needs Mac", "", "**Interactive:** When online, JARVIS stays interactive like offline — you decide Full vs Basic from HUD or CLI --interactive"])
            return "\n".join(lines)

        elif action == "interactive":
            from jarvis.tools.registry import get_tool
            hybrid = get_tool("hybrid_mode")
            if hybrid:
                return hybrid.run(action="interactive")
            return "Hybrid tool not available"

        else:
            status = get_auto_status()
            net = status["network"]
            eng = status["engines"]
            sel = status["selected"]
            prefs = status["prefs"]

            online_icon = "🌐 ONLINE" if net["online"] else "📴 OFFLINE"
            mode = sel["mode"]

            out = [
                f"**Hybrid Mode Status — SHILATECH — {online_icon} — {mode}**",
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
                "• Online + OPENAI_API_KEY → openai full stack (best for 8GB, no RAM) — SHILATECH",
                "• Online + Ollama running → ollama full local (tinyllama/phi3:mini for 8GB)",
                "• Offline + Ollama running → ollama offline (still works offline!)",
                "• Offline no Ollama → mock basic (always works, keyword memory, local calendar/email mock)",
                "",
                "**Interactive When Online — You Decide, Sir:**",
                "When online, JARVIS stays interactive like offline — you make decision from there:",
                "  1. Full Stack Online — openai/ollama, sends prompt to cloud if openai, full search, best quality",
                "  2. Basic Offline Local — mock/ollama local, nothing leaves device, private, SHILATECH secure",
                "  Same circular interface for both, only badge changes, Sir.",
                "",
                "**For your i5-6300U 8GB — SHILATECH:**",
                "• Online: Use openai — fastest, no RAM pressure, Sir",
                "• Offline: Use mock basic or ollama tinyllama 1.1B (~8-10 tokens/sec)",
                "• Avoid: 7B+ models on 8GB — will swap and freeze",
                "",
                f"**Current:** {sel['engine']} — {mode}",
                "",
                "**Interactive Decision:**",
                "• hybrid_mode interactive — shows decision prompt when online",
                "• hybrid_mode decide choice 1 — use full stack online now",
                "• hybrid_mode decide choice 2 — use basic offline local even though online",
                "• jarvis ask --engine auto --interactive — prompts you to pick 1 or 2 when online",
                "• In HUD: top bar ONLINE badge clickable to decide Full vs Basic",
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
        description="Hybrid Mode Config — SHILATECH — configure online full stack vs offline basic. Set online_engine (auto/openai/ollama/vllm/mock) and offline_engine (mock/ollama). Interactive when online so you can decide Full vs Basic. For i5-6300U 8GB: online openai, offline mock.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "status, set, enable, disable, interactive, decide", "default": "status"},
                "online_engine": {"type": "string", "description": "Engine when online: auto, openai, ollama, vllm, mock", "default": "auto"},
                "offline_engine": {"type": "string", "description": "Engine when offline: mock, ollama", "default": "mock"},
                "choice": {"type": "string", "description": "Interactive choice: 1=full stack online, 2=basic offline local", "default": ""},
            },
            "required": [],
        },
    )

    def run(self, action: str = "status", online_engine: str = "auto", offline_engine: str = "mock", choice: str = "", **kwargs) -> str:
        cfg = JarvisConfig.load()

        if action == "status":
            status = get_auto_status()
            return f"""**Hybrid Mode Config — SHILATECH:**

**Current Prefs (from ~/.jarvis/config.toml [auto]):**
  online_engine = {status['prefs']['online_engine']} (auto = best available: openai > ollama > vllm > mlx > mock)
  offline_engine = {status['prefs']['offline_engine']} (mock = always works, ollama = local offline if running)
  cache_seconds = {cfg.auto.cache_seconds}
  enabled = {cfg.auto.enabled}

**Current Selection:**
  Network: {'🌐 Online' if status['network']['online'] else '📴 Offline'} via {status['network']['method']}
  Engine: {status['selected']['engine']} — {status['selected']['mode']}
  Reason: {status['selected']['reason']}

**For your i5-6300U 8GB — SHILATECH:**
  • Online: openai (best, no RAM, fast) or ollama tinyllama/phi3:mini (local but slower)
  • Offline: mock (basic, always works) or ollama tinyllama offline (still works offline!)

**Interactive Decision When Online — You Decide, Sir:**
  When online, JARVIS stays interactive like offline — you make decision from there:
  1. Full Stack Online — openai/ollama, sends prompt to cloud if openai, full search, best quality
  2. Basic Offline Local — mock/ollama local, nothing leaves device, private, SHILATECH secure
  Same circular interface for both, only badge changes.

  hybrid_mode interactive — shows decision prompt
  hybrid_mode decide choice 1 — use full stack online now
  hybrid_mode decide choice 2 — use basic offline local even though online

**Set:**
  hybrid_mode set online_engine openai offline_engine mock
  hybrid_mode set online_engine ollama offline_engine ollama
  hybrid_mode enable / disable

**Use:**
  jarvis ask --engine auto 'Good morning Eugene' --interactive
  # Auto detects online, shows interactive decision, you pick 1 or 2
"""

        elif action == "interactive" or (action == "decide" and not choice):
            status = get_auto_status()
            net = status["network"]
            sel = status["selected"]

            if not net["online"]:
                return f"""📴 **OFFLINE — Basic Mode Only, Sir — SHILATECH**

Network: Offline via {net['method']} — Error: {net.get('error','no internet')}
Selected: {sel['engine']} — {sel['mode']}
Reason: {sel['reason']}

Offline, only basic available:
  • mock — always works, keyword memory, local calendar/email mock, 100% private
  • ollama — if running, local LLM offline (tinyllama 1.1B ~8-10 tokens/sec for 8GB)

No decision needed offline — basic only, Sir. Go online for full stack choice.
Same circular interface, only badge shows OFFLINE BASIC.

Test: jarvis ask --engine auto 'Good morning Eugene' (will use {sel['engine']} offline)
"""

            return f"""🌐 **ONLINE — Interactive Decision — SHILATECH — Full Stack vs Basic, Sir**

Network: Online via {net['method']} {net.get('latency_ms','')}ms
Current Auto Pick: {sel['engine']} — {sel['mode']}
Reason: {sel['reason']}

**You are online, Sir. JARVIS stays interactive like offline — you decide from here:**

**Option 1 — Full Stack Online (Recommended when online):**
  Engine: {status['prefs']['online_engine']} → auto picks best: openai > ollama > vllm > mlx
  What happens:
    • If OPENAI_API_KEY set → openai — prompt sent to https://api.openai.com HTTPS encrypted, best quality, no RAM pressure for your 8GB — SHILATECH
    • If Ollama running → ollama — LLM stays local even online (tinyllama/phi3:mini for 8GB), only search queries go online
    • Full search: Tavily if key set else DDGS free
    • Full memory: FAISS if installed else keyword
    • Best quality, needs internet
  Security: Only prompt you type sent to OpenAI API if openai, else LLM local private. Your files/memory/faces/voice stay local unless you use those tools. Same circular interface.

**Option 2 — Basic Offline Local (Even though online, stay private):**
  Engine: {status['prefs']['offline_engine']} → {status['prefs']['offline_engine']}
  What happens:
    • mock — always works, keyword memory, local calendar.json/email.json mock, 100% private, nothing leaves device
    • ollama — if running, local LLM offline (tinyllama 1.1B ~8-10 tokens/sec), still local even though online
    • Search: mock only (no online search) or DDGS if you want
    • Most private, works even if you pull Ethernet after
  Security: Nothing leaves device, 100% local, SHILATECH private. Same circular interface, only badge shows OFFLINE BASIC.

**For your i5-6300U 8GB — SHILATECH advice:**
  • Online with good WiFi: Option 1 openai — fastest, no RAM, best quality, Sir
  • Online but want privacy: Option 1 ollama — LLM local, only search online
  • Online but low battery / want offline test: Option 2 mock/ollama — basic, local only

**Decide now, Sir:**
  hybrid_mode decide choice 1 — Use Full Stack Online now (openai/ollama)
  hybrid_mode decide choice 2 — Use Basic Offline Local even though online (mock/ollama local)

**Or in CLI:**
  jarvis ask --engine auto --online-engine openai --offline-engine mock --interactive
  # Will prompt you to pick 1 or 2 when online

**Or in HUD:**
  Top bar shows ONLINE badge — click it to decide Full Stack vs Basic
  Circular HUD bottom shows decision buttons when online — same interface, you decide

Current: {sel['engine']} — {sel['mode']} — You can still decide, Sir.
"""

        elif action == "decide":
            status = get_auto_status()
            net = status["network"]

            if not net["online"]:
                return f"📴 Offline — only basic available, Sir — SHILATECH. No decision needed. Using {status['selected']['engine']} — {status['selected']['mode']} — Same circular interface."

            choice = str(choice).strip()

            if choice == "1" or choice.lower() in ["full", "online", "full stack", "openai", "ollama"]:
                cfg.auto.online_engine = online_engine if online_engine != "auto" else "auto"
                cfg.save()
                new_status = get_auto_status()
                from jarvis.core.network import check_engines
                eng = check_engines()
                # Force online engine
                engine_name = new_status["selected"]["engine"]
                reason = new_status["selected"]["reason"]

                return f"""✅ **Decision: Full Stack Online — Option 1 — SHILATECH, Sir**

You chose: Full Stack Online even though you could stay basic. JARVIS stays interactive like offline — you decided from here.

**Now Using:**
  Engine: {engine_name}
  Reason: {reason}
  Mode: FULL STACK ONLINE
  Network: 🌐 Online via {net['method']} {net.get('latency_ms','')}ms
  Interface: Same circular HUD like screenshot — only badge shows ONLINE FULL STACK

**What happens now:**
  • Prompt you type will be sent to {engine_name} — {'OpenAI API HTTPS encrypted if openai, else LLM local private if ollama' if engine_name in ['openai','ollama'] else 'mock local'}
  • Full search: Tavily if key set else DDGS free
  • Full memory: FAISS if installed
  • Best quality for your 8GB: {'openai no RAM' if engine_name=='openai' else 'tinyllama/phi3:mini local'}

**Security — SHILATECH:** Only prompt sent to {engine_name} if cloud, files/memory/faces/voice stay local unless you use those tools, Sir. Same interface.

**Test:**
  jarvis ask --engine {engine_name} 'Good morning Eugene'
  or
  jarvis ask --engine auto --online-engine {online_engine} 'Good morning Eugene'

You can switch anytime: hybrid_mode decide choice 2 for basic local even online, Sir.
"""

            elif choice == "2" or choice.lower() in ["basic", "offline", "local", "mock", "private"]:
                cfg.auto.offline_engine = offline_engine
                cfg.save()
                from jarvis.core.network import check_engines
                eng = check_engines()
                engine_name = offline_engine
                if offline_engine == "auto":
                    engine_name = "mock"
                if engine_name == "ollama" and not eng.ollama:
                    engine_name = "mock"

                return f"""✅ **Decision: Basic Offline Local — Option 2 — SHILATECH, Sir — Even Though Online, Stay Private — Interactive**

You chose: Basic Offline Local even though online — private, local only. JARVIS stays interactive like offline — you decided from here.

**Now Using (Even Though Online):**
  Engine: {engine_name}
  Mode: BASIC OFFLINE LOCAL (forced even though online)
  Network: 🌐 Online via {net['method']} but you chose local only
  Reason: You decided to stay private, Sir — nothing leaves device
  Interface: Same circular HUD like screenshot — only badge shows OFFLINE BASIC even though online

**What happens now:**
  • Engine: {engine_name} — {'mock always works, keyword memory, local calendar/email mock' if engine_name=='mock' else 'ollama tinyllama local 1.1B ~8-10 tokens/sec, LLM stays on device even online'}
  • Search: mock only (no online search) — 100% private
  • Memory: keyword local
  • Most private, SHILATECH secure, Sir — same interface

**Security:** Nothing leaves device, 100% local, private by default, Sir.

**Test:**
  jarvis ask --engine {engine_name} 'Good morning Eugene'
  or
  jarvis ask --engine auto --offline-engine {offline_engine} --online-engine {online_engine} 'Good morning Eugene' then choose 2

You can switch anytime: hybrid_mode decide choice 1 for full stack online, Sir.
"""

            else:
                return f"Invalid choice '{choice}', Sir — SHILATECH. Choose 1 for Full Stack Online or 2 for Basic Offline Local.\n\n{self.run(action='interactive')}"

        elif action == "set":
            cfg.auto.online_engine = online_engine
            cfg.auto.offline_engine = offline_engine
            cfg.save()
            status = get_auto_status()
            return f"""✅ **Hybrid Mode Set — SHILATECH:**

  online_engine = {online_engine}
  offline_engine = {offline_engine}

Saved to ~/.jarvis/config.toml [auto]

**Now:**
  Network: {'🌐 Online' if status['network']['online'] else '📴 Offline'}
  Selected: {status['selected']['engine']} — {status['selected']['mode']}
  Reason: {status['selected']['reason']}

**Interactive:** When online, JARVIS stays interactive like offline — you decide Full Stack vs Basic from HUD or CLI --interactive — same circular interface

Test: jarvis ask --engine auto 'Good morning Eugene' --interactive
"""

        elif action == "enable":
            cfg.auto.enabled = True
            cfg.save()
            return f"✅ **Hybrid Mode ENABLED — SHILATECH** — Auto online/offline switching ON, Sir.\n\nOnline: full stack ({cfg.auto.online_engine}), Offline: basic ({cfg.auto.offline_engine})\n\nInteractive: When online, you can still decide Full vs Basic — hybrid_mode interactive — same interface, you decide\n\nConfig: ~/.jarvis/config.toml [auto] enabled=true"

        elif action == "disable":
            cfg.auto.enabled = False
            cfg.save()
            return f"⚠️ **Hybrid Mode DISABLED — SHILATECH** — Auto switching OFF, Sir.\n\nNow uses fixed engine from [engine] type={cfg.engine.type.value}\n\nEnable: hybrid_mode enable"

        else:
            return self.run(action="status")
