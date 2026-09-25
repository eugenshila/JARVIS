"""JARVIS client — minimal OpenAI-compatible + new stack support.

This module preserves backward compatibility with the original app.py
while also exposing the new engine abstraction.
"""

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from jarvis.core.config import JarvisConfig
    from jarvis.core.types import Message, Role
    from jarvis.engine.registry import get_engine
    HAS_NEW = True
except ImportError:
    HAS_NEW = False

# Legacy direct HTTP implementation (fallback)


def _legacy_generate(prompt: str, context: str) -> str:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError("Set OPENAI_API_KEY to enable AI responses, or use Copy prompt. For offline demo, use --mock or set JARVIS_MOCK=1.")
    url = os.environ.get("JARVIS_API_URL", "https://api.openai.com/v1/chat/completions")
    if not url.startswith("https://") and not url.startswith("http://"):
        raise ValueError("JARVIS_API_URL must use HTTPS.")
    payload = {
        "model": os.environ.get("JARVIS_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": "Use only supplied context for personal facts. Mark inferences clearly. Never invent meeting details."},
            {"role": "user", "content": f"{prompt}\n\nMeeting or task context:\n{context or '(No context supplied)'}"},
        ],
    }
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=45) as response:
            result = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"API returned HTTP {error.code}. Check your key, model and provider.") from error
    except URLError as error:
        raise RuntimeError(f"Could not connect to the API: {error.reason}") from error
    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("The API returned an unexpected response format.") from error


def generate(prompt: str, context: str, agent: str | None = None, engine: str | None = None, model: str | None = None) -> str:
    """Generate response — tries new stack first, falls back to legacy.

    Args:
        prompt: The prompt / task
        context: Additional context
        agent: Agent name (simple, react, orchestrator, etc)
        engine: Engine type (openai, ollama, mock)
        model: Model override
    """
    # Check for mock mode
    if os.environ.get("JARVIS_MOCK") == "1" or engine == "mock":
        if HAS_NEW:
            cfg = JarvisConfig.load()
            from jarvis.core.types import EngineType
            cfg.engine.type = EngineType.MOCK
            if model:
                cfg.engine.model = model
            eng = get_engine(cfg)
            msgs = [
                Message(role=Role.SYSTEM, content="You are JARVIS mock engine."),
                Message(role=Role.USER, content=f"{prompt}\n\nContext:\n{context}"),
            ]
            resp = eng.generate(msgs)
            return resp.content
        else:
            return f"[MOCK] Prompt: {prompt[:200]}\nContext: {context[:500]}\n\nSet OPENAI_API_KEY for real generation."

    if HAS_NEW:
        try:
            cfg = JarvisConfig.load()
            if engine:
                try:
                    from jarvis.core.types import EngineType
                    cfg.engine.type = EngineType(engine)
                except ValueError:
                    pass
            if model:
                cfg.engine.model = model
            if agent:
                cfg.preset = agent

            # Use agent if available
            if agent:
                from jarvis.agents.registry import get_agent
                ag = get_agent(agent, config=cfg)
                resp = ag.run(prompt, context=context)
                return resp.content
            else:
                eng = get_engine(cfg)
                msgs = [
                    Message(role=Role.SYSTEM, content=cfg.get_preset().system_prompt),
                    Message(role=Role.USER, content=f"{prompt}\n\nContext:\n{context}" if context else prompt),
                ]
                resp = eng.generate(msgs)
                return resp.content
        except Exception as e:
            # If new stack fails due to missing key, try legacy for better error
            if "OPENAI_API_KEY" in str(e) or "api_key" in str(e).lower():
                pass
            else:
                # For other errors, still return error but with context
                if os.environ.get("JARVIS_FALLBACK") != "0":
                    try:
                        return _legacy_generate(prompt, context)
                    except Exception:
                        pass
            # Re-raise original if fallback fails
            if "OPENAI_API_KEY" not in str(e):
                # Show new stack error
                raise
            # else try legacy which gives nicer message
    return _legacy_generate(prompt, context)


# Convenience async version
async def agenerate(prompt: str, context: str = "", **kwargs) -> str:
    import asyncio
    return await asyncio.to_thread(generate, prompt, context, **kwargs)
