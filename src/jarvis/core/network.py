"""
Network detection + auto engine selector for hybrid online/offline mode.

User wants: installed locally but when online run full stack online, when offline run basic.

This module:
- Detects if machine is online (internet reachable)
- Detects what engines are available (openai key, ollama, vllm, etc.)
- Picks best engine automatically
- Provides status for CLI and HUD

For i5-6300U + 8GB machine:
- Online: openai (best, fast, no local RAM) or ollama tinyllama/phi3:mini
- Offline: mock (basic) or ollama tinyllama if installed (still works offline)
"""

from __future__ import annotations

import os
import socket
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class NetworkStatus:
    online: bool
    method: str  # how we detected
    latency_ms: Optional[int] = None
    ip: Optional[str] = None
    error: Optional[str] = None


@dataclass
class EngineAvailability:
    openai: bool
    ollama: bool
    vllm: bool
    mlx: bool
    anthropic: bool
    tavily: bool
    faiss: bool
    details: Dict[str, Any]


def check_online(timeout: float = 2.0) -> NetworkStatus:
    """
    Check if internet is reachable. Tries multiple methods, fast.
    Returns NetworkStatus with online True/False.
    """
    start = time.time()

    # Method 1: DNS + socket to 8.8.8.8:53 (Google DNS) — fastest, no HTTP
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        latency = int((time.time() - start) * 1000)
        return NetworkStatus(online=True, method="8.8.8.8:53 socket", latency_ms=latency)
    except Exception as e:
        pass

    # Method 2: 1.1.1.1:53 Cloudflare
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=timeout)
        latency = int((time.time() - start) * 1000)
        return NetworkStatus(online=True, method="1.1.1.1:53 socket", latency_ms=latency)
    except:
        pass

    # Method 3: HTTP to https://api.openai.com or https://www.google.com
    try:
        import httpx
        with httpx.Client(timeout=timeout) as client:
            # Try OpenAI API (if key set, this is the real endpoint we need)
            # If no key, try google
            urls = ["https://1.1.1.1", "https://8.8.8.8", "https://www.google.com", "https://api.openai.com"]
            for url in urls:
                try:
                    r = client.get(url, timeout=timeout)
                    if r.status_code < 500:
                        latency = int((time.time() - start) * 1000)
                        return NetworkStatus(online=True, method=f"HTTP {url}", latency_ms=latency)
                except:
                    continue
    except:
        pass

    # Method 4: socket.gethostbyname
    try:
        socket.gethostbyname("www.google.com")
        # If DNS works but previous failed, still consider online but slow
        latency = int((time.time() - start) * 1000)
        return NetworkStatus(online=True, method="DNS google.com", latency_ms=latency)
    except Exception as e:
        return NetworkStatus(online=False, method="all failed", error=str(e))


def check_engines() -> EngineAvailability:
    """Check what engines/tools are available on this machine."""
    details: Dict[str, Any] = {}

    # OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    openai_ok = bool(openai_key and len(openai_key) > 10)
    details["openai"] = "OPENAI_API_KEY set" if openai_ok else "No OPENAI_API_KEY"

    # Ollama
    ollama_ok = False
    try:
        import httpx
        with httpx.Client(timeout=1.0) as client:
            r = client.get("http://localhost:11434/api/tags", timeout=1.0)
            if r.status_code == 200:
                ollama_ok = True
                data = r.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                details["ollama"] = f"Running, models: {', '.join(models[:3])}" if models else "Running, no models"
            else:
                details["ollama"] = f"HTTP {r.status_code}"
    except Exception as e:
        details["ollama"] = f"Not running: {e}"

    # vLLM
    vllm_ok = False
    try:
        import torch
        if torch.cuda.is_available():
            vllm_ok = True
            details["vllm"] = f"CUDA available: {torch.cuda.get_device_name(0)}"
        else:
            details["vllm"] = "No CUDA"
    except Exception as e:
        details["vllm"] = f"torch not installed or no CUDA: {e}"

    # MLX
    mlx_ok = False
    try:
        import platform
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            try:
                import mlx
                mlx_ok = True
                details["mlx"] = "Mac ARM64 + mlx available"
            except:
                details["mlx"] = "Mac ARM64 but mlx not installed"
        else:
            details["mlx"] = f"Not Mac ARM64: {platform.system()} {platform.machine()}"
    except Exception as e:
        details["mlx"] = str(e)

    # Anthropic
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    anthropic_ok = bool(anthropic_key and len(anthropic_key) > 10)
    details["anthropic"] = "ANTHROPIC_API_KEY set" if anthropic_ok else "No ANTHROPIC_API_KEY"

    # Tavily
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    tavily_ok = bool(tavily_key)
    details["tavily"] = "TAVILY_API_KEY set" if tavily_ok else "No TAVILY_API_KEY (DDGS fallback)"

    # FAISS
    faiss_ok = False
    try:
        import faiss
        faiss_ok = True
        details["faiss"] = f"FAISS {faiss.__version__ if hasattr(faiss, '__version__') else 'available'}"
    except Exception as e:
        details["faiss"] = f"Not installed: {e}"

    return EngineAvailability(
        openai=openai_ok,
        ollama=ollama_ok,
        vllm=vllm_ok,
        mlx=mlx_ok,
        anthropic=anthropic_ok,
        tavily=tavily_ok,
        faiss=faiss_ok,
        details=details
    )


def pick_best_engine(network: NetworkStatus, engines: EngineAvailability, 
                      online_pref: str = "auto", offline_pref: str = "mock") -> tuple[str, str]:
    """
    Pick best engine based on network + availability + user prefs.
    Returns (engine_name, reason)
    """
    if network.online:
        # Online mode — full stack
        if online_pref != "auto":
            # User forced preference
            if online_pref == "openai" and engines.openai:
                return "openai", "Online + user pref openai + OPENAI_API_KEY set"
            if online_pref == "ollama" and engines.ollama:
                return "ollama", "Online + user pref ollama + Ollama running"
            if online_pref == "vllm" and engines.vllm:
                return "vllm", "Online + user pref vllm + CUDA available"
            if online_pref == "mlx" and engines.mlx:
                return "mlx", "Online + user pref mlx + Mac ARM"
            if online_pref == "mock":
                return "mock", "Online + user pref mock (basic even online)"
            # If pref not available, fall through to auto

        # Auto online selection — best first
        if engines.openai:
            return "openai", f"Online ({network.method} {network.latency_ms}ms) + OPENAI_API_KEY set → full stack online (best for 8GB machine, no local RAM)"
        if engines.ollama:
            return "ollama", f"Online + Ollama running ({engines.details.get('ollama','')}) → full local (tinyllama/phi3:mini recommended for 8GB)"
        if engines.anthropic:
            return "litellm", f"Online + ANTHROPIC_API_KEY set → Claude via LiteLLM"
        if engines.vllm:
            return "vllm", f"Online + CUDA available → vLLM high-perf (needs 8GB+ VRAM, not your i5-6300U)"
        if engines.mlx:
            return "mlx", f"Online + Mac ARM → MLX (not your Windows machine)"

        # Online but no cloud/local LLM — still online for search, but LLM mock
        return "mock", f"Online ({network.method}) but no LLM key/Ollama → mock LLM + online search (Tavily/DDGS) — basic LLM but full search"

    else:
        # Offline mode — basic
        if offline_pref != "mock":
            if offline_pref == "ollama" and engines.ollama:
                return "ollama", f"Offline but Ollama still works offline ({engines.details.get('ollama','')}) → local LLM offline"
            # If pref not available, fall through

        if engines.ollama:
            # Ollama works offline! Good for offline full-ish
            return "ollama", f"Offline ({network.error or 'no internet'}) but Ollama running offline → local LLM offline (tinyllama recommended for 8GB)"

        return "mock", f"Offline ({network.error or 'no internet'}) → mock basic (offline, no API, keyword memory, local calendar/email mock) — always works"


def get_auto_status() -> Dict[str, Any]:
    """Get full auto status for CLI and HUD."""
    network = check_online()
    engines = check_engines()
    
    # Load user prefs from config if exists
    online_pref = "auto"
    offline_pref = "mock"
    try:
        from jarvis.core.config import JarvisConfig
        cfg = JarvisConfig.load()
        # Check if config has auto prefs
        config_path = cfg.config_path
        if config_path.exists():
            try:
                import tomllib
                data = tomllib.loads(config_path.read_text())
                auto_cfg = data.get("auto", {})
                online_pref = auto_cfg.get("online_engine", "auto")
                offline_pref = auto_cfg.get("offline_engine", "mock")
            except:
                pass
    except:
        pass

    engine, reason = pick_best_engine(network, engines, online_pref, offline_pref)

    return {
        "network": {
            "online": network.online,
            "method": network.method,
            "latency_ms": network.latency_ms,
            "error": network.error,
        },
        "engines": {
            "openai": engines.openai,
            "ollama": engines.ollama,
            "vllm": engines.vllm,
            "mlx": engines.mlx,
            "anthropic": engines.anthropic,
            "tavily": engines.tavily,
            "faiss": engines.faiss,
            "details": engines.details,
        },
        "prefs": {
            "online_engine": online_pref,
            "offline_engine": offline_pref,
        },
        "selected": {
            "engine": engine,
            "reason": reason,
            "mode": "FULL STACK ONLINE" if network.online and engine != "mock" else "BASIC OFFLINE" if not network.online else "ONLINE BUT BASIC (no LLM key)",
        }
    }
