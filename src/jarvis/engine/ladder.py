"""
engine/ladder.py — one ladder of models per *purpose*, with timeouts and cooldowns.

WHY THIS EXISTS
    Before this module, every caller picked an engine by name and called it.
    Three faults followed from that:

    NO TIMEOUT.     Nothing in the stack bounded a single request. One unwell
                    endpoint returning 504s turns every call into an unbounded
                    hang, and a voice assistant that goes silent for a minute
                    is broken even though nothing crashed.

    NO FALLBACK.    One hardcoded engine meant that when that engine was
                    rate-limited or offline, the feature was simply gone. A
                    ladder costs nothing when the first rung works and saves
                    the feature when it does not.

    NO ROUTING.     "Is this a yes or a no?" and "write me a design document"
                    went to the same model. Cheap classification burning a
                    frontier model is both slow and expensive.

THE DESIGN
    Callers ask for a *purpose*, never a model::

        from jarvis.engine.ladder import for_purpose, FAST
        engine = for_purpose(FAST)
        reply  = engine.generate(messages)

    Each purpose is an ordered list of rungs ``(engine, model, timeout_s)``.
    A call walks the ladder top to bottom. When a rung times out or raises, it
    is put on a **cooldown** and the next rung takes the call — so the next
    request does not pay the same timeout again. Cooldown length grows with
    consecutive failures (30s, 60s, 120s ... capped) and resets on success.

    Defaults are deliberately local-first: Ollama leads, hosted models sit
    behind it. Override the whole thing in ``~/.jarvis/config.toml``::

        [ladder.fast]
        rungs = [
            { engine = "ollama", model = "qwen2.5:3b",   timeout = 20 },
            { engine = "openai", model = "gpt-4o-mini",  timeout = 30 },
            { engine = "mock",   model = "mock",         timeout = 5  },
        ]

    Change a model HERE and the whole app follows.
"""

from __future__ import annotations

import concurrent.futures
import os
import threading
import time
from dataclasses import dataclass
from typing import Any
from collections.abc import Iterator

from jarvis.core.config import JarvisConfig
from jarvis.core.types import AgentResponse, EngineConfig, EngineType, Message
from jarvis.engine.base import BaseEngine

# ── Purposes ──────────────────────────────────────────────────────────────────
FAST = "fast"  # short classification, extraction, one-line decisions
SMART = "smart"  # reasoning, generation, long documents
SEARCH = "search"  # grounded / tool-heavy work
PURPOSES = (FAST, SMART, SEARCH)

#: Backoff schedule, in seconds, indexed by consecutive-failure count.
COOLDOWN_STEPS = (30.0, 60.0, 120.0, 300.0)


@dataclass(frozen=True)
class Rung:
    """One attempt in a ladder: which engine, which model, how long we wait."""

    engine: str
    model: str
    timeout: float = 30.0

    @property
    def key(self) -> str:
        return f"{self.engine}:{self.model}"


# Local-first defaults. A rung that cannot be constructed (missing dependency,
# no API key) is skipped at call time, so listing openai here costs nothing
# when OPENAI_API_KEY is unset.
DEFAULT_LADDERS: dict[str, list[Rung]] = {
    FAST: [
        Rung("ollama", "qwen2.5:3b", timeout=20.0),
        Rung("openai", "gpt-4o-mini", timeout=30.0),
        Rung("mock", "mock", timeout=5.0),
    ],
    SMART: [
        Rung("openai", "gpt-4o-mini", timeout=60.0),
        Rung("ollama", "qwen2.5:7b", timeout=90.0),
        Rung("ollama", "qwen2.5:3b", timeout=60.0),
        Rung("mock", "mock", timeout=5.0),
    ],
    SEARCH: [
        Rung("openai", "gpt-4o-mini", timeout=60.0),
        Rung("ollama", "qwen2.5:3b", timeout=60.0),
        Rung("mock", "mock", timeout=5.0),
    ],
}


# ── Cooldown bookkeeping ──────────────────────────────────────────────────────


@dataclass
class _RungHealth:
    failures: int = 0
    until: float = 0.0
    last_error: str = ""


class _CooldownRegistry:
    """Process-wide memory of which rungs are currently unwell."""

    def __init__(self) -> None:
        self._health: dict[str, _RungHealth] = {}
        self._lock = threading.Lock()

    def available(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            h = self._health.get(key)
            return h is None or now >= h.until

    def note_failure(self, key: str, error: str) -> float:
        """Record a failure and return the cooldown length just applied."""
        now = time.monotonic()
        with self._lock:
            h = self._health.setdefault(key, _RungHealth())
            step = COOLDOWN_STEPS[min(h.failures, len(COOLDOWN_STEPS) - 1)]
            h.failures += 1
            h.until = now + step
            h.last_error = str(error)[:300]
            return step

    def note_success(self, key: str) -> None:
        with self._lock:
            self._health.pop(key, None)

    def status(self) -> dict[str, dict[str, Any]]:
        now = time.monotonic()
        with self._lock:
            return {
                key: {
                    "failures": h.failures,
                    "cooling_for": max(0.0, h.until - now),
                    "last_error": h.last_error,
                }
                for key, h in self._health.items()
            }

    def clear(self) -> None:
        with self._lock:
            self._health.clear()


COOLDOWNS = _CooldownRegistry()


# ── Ladder configuration ──────────────────────────────────────────────────────


def _rungs_from_toml(raw: Any) -> list[Rung]:
    out: list[Rung] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        engine = str(item.get("engine", "")).strip()
        model = str(item.get("model", "")).strip()
        if not engine or not model:
            continue
        try:
            timeout = float(item.get("timeout", 30.0))
        except (TypeError, ValueError):
            timeout = 30.0
        out.append(Rung(engine=engine, model=model, timeout=max(1.0, timeout)))
    return out


def load_ladders(config: JarvisConfig | None = None) -> dict[str, list[Rung]]:
    """Merge ``[ladder.*]`` from config.toml over :data:`DEFAULT_LADDERS`."""
    ladders = {p: list(rungs) for p, rungs in DEFAULT_LADDERS.items()}
    cfg = config or JarvisConfig.load()
    path = cfg.config_path
    if not path.exists():
        return ladders
    try:
        try:
            import tomllib
        except ModuleNotFoundError:  # pragma: no cover
            import tomli as tomllib  # type: ignore

        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ladders
    section = data.get("ladder", {})
    if not isinstance(section, dict):
        return ladders
    for purpose in PURPOSES:
        entry = section.get(purpose)
        if isinstance(entry, dict):
            rungs = _rungs_from_toml(entry.get("rungs"))
            if rungs:
                ladders[purpose] = rungs
    return ladders


# ── The engine ────────────────────────────────────────────────────────────────


class LadderExhausted(RuntimeError):
    """Every rung in the ladder failed or was cooling down."""


class LadderEngine(BaseEngine):
    """A :class:`BaseEngine` that walks a purpose's rungs until one answers."""

    def __init__(
        self,
        purpose: str = SMART,
        rungs: list[Rung] | None = None,
        config: JarvisConfig | None = None,
    ) -> None:
        if purpose not in PURPOSES:
            raise ValueError(f"Unknown purpose {purpose!r}; expected one of {PURPOSES}")
        self.purpose = purpose
        self.name = f"ladder:{purpose}"
        self._config = config
        self.rungs = rungs if rungs is not None else load_ladders(config).get(purpose, [])
        self._instances: dict[str, BaseEngine] = {}
        self._lock = threading.Lock()
        #: Populated after every call — which rung answered and what was skipped.
        self.last_trace: list[dict[str, Any]] = []

    # -- rung construction ---------------------------------------------------

    def _build(self, rung: Rung) -> BaseEngine:
        """Instantiate (and cache) the engine behind a rung."""
        with self._lock:
            cached = self._instances.get(rung.key)
        if cached is not None:
            return cached

        from jarvis.engine.registry import get_engine  # late: avoids a cycle

        base = (self._config or JarvisConfig.load()).engine
        eng_cfg = EngineConfig(
            type=_engine_type(rung.engine),
            model=rung.model,
            api_url=base.api_url,
            api_key=base.api_key,
            temperature=base.temperature,
            max_tokens=base.max_tokens,
        )
        engine = get_engine(eng_cfg, engine_type=rung.engine)
        with self._lock:
            self._instances[rung.key] = engine
        return engine

    # -- the walk ------------------------------------------------------------

    def generate(self, messages: list[Message], **kwargs) -> AgentResponse:
        trace: list[dict[str, Any]] = []
        errors: list[str] = []

        for rung in self.rungs:
            if not COOLDOWNS.available(rung.key):
                trace.append({"rung": rung.key, "result": "cooling_down"})
                continue

            started = time.monotonic()
            try:
                engine = self._build(rung)
            except Exception as exc:
                # Missing dependency or no credentials — not the rung's fault
                # at runtime, but there is nothing to call. Cool it briefly.
                COOLDOWNS.note_failure(rung.key, f"unavailable: {exc}")
                trace.append({"rung": rung.key, "result": "unavailable", "error": str(exc)})
                errors.append(f"{rung.key}: {exc}")
                continue

            try:
                resp = _call_with_timeout(engine, messages, rung.timeout, kwargs)
            except concurrent.futures.TimeoutError:
                cooled = COOLDOWNS.note_failure(rung.key, f"timeout after {rung.timeout}s")
                trace.append(
                    {"rung": rung.key, "result": "timeout", "cooldown": cooled,
                     "elapsed": time.monotonic() - started}
                )
                errors.append(f"{rung.key}: timed out after {rung.timeout}s")
                continue
            except Exception as exc:
                cooled = COOLDOWNS.note_failure(rung.key, str(exc))
                trace.append(
                    {"rung": rung.key, "result": "error", "error": str(exc),
                     "cooldown": cooled, "elapsed": time.monotonic() - started}
                )
                errors.append(f"{rung.key}: {exc}")
                continue

            if resp is None or not str(getattr(resp, "content", "")).strip():
                # An empty body is a failure. Silently returning "" is how a
                # dying endpoint looks from the outside.
                cooled = COOLDOWNS.note_failure(rung.key, "empty response")
                trace.append({"rung": rung.key, "result": "empty", "cooldown": cooled})
                errors.append(f"{rung.key}: empty response")
                continue

            COOLDOWNS.note_success(rung.key)
            trace.append(
                {"rung": rung.key, "result": "ok", "elapsed": time.monotonic() - started}
            )
            self.last_trace = trace
            if not resp.model:
                resp.model = rung.model
            return resp

        self.last_trace = trace
        raise LadderExhausted(
            f"All {len(self.rungs)} rungs of the '{self.purpose}' ladder failed: "
            + "; ".join(errors or ["no rungs configured"])
        )

    async def agenerate(self, messages: list[Message], **kwargs) -> AgentResponse:
        import asyncio

        return await asyncio.get_running_loop().run_in_executor(
            None, lambda: self.generate(messages, **kwargs)
        )

    def stream(self, messages: list[Message], **kwargs) -> Iterator[str]:
        yield self.generate(messages, **kwargs).content

    def describe(self) -> dict:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "rungs": [
                {
                    "engine": r.engine,
                    "model": r.model,
                    "timeout": r.timeout,
                    "available": COOLDOWNS.available(r.key),
                }
                for r in self.rungs
            ],
            "cooldowns": COOLDOWNS.status(),
        }


def _engine_type(name: str) -> EngineType:
    try:
        return EngineType(name)
    except ValueError:
        return EngineType.OPENAI


def _call_with_timeout(
    engine: BaseEngine, messages: list[Message], timeout: float, kwargs: dict
) -> AgentResponse | None:
    """Bound one rung's call.

    The worker thread is left to finish on timeout — we cannot kill a blocking
    socket read in CPython — but the *caller* is released on schedule, which is
    the property that matters. The abandoned thread is a daemon and dies with
    the process.
    """
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(engine.generate, messages, **kwargs)
        return future.result(timeout=timeout)
    finally:
        pool.shutdown(wait=False)


# ── Public helpers ────────────────────────────────────────────────────────────

_cache: dict[str, LadderEngine] = {}
_cache_lock = threading.Lock()


def for_purpose(purpose: str = SMART, config: JarvisConfig | None = None) -> LadderEngine:
    """Get the (cached) ladder engine for a purpose. This is the front door."""
    if os.environ.get("JARVIS_LADDER_DISABLED"):
        raise RuntimeError("Ladder disabled via JARVIS_LADDER_DISABLED")
    with _cache_lock:
        engine = _cache.get(purpose)
        if engine is None:
            engine = LadderEngine(purpose, config=config)
            _cache[purpose] = engine
        return engine


def reset() -> None:
    """Test helper — drop cached engines and all cooldown state."""
    with _cache_lock:
        _cache.clear()
    COOLDOWNS.clear()


def status() -> dict[str, Any]:
    """What the HUD and ``jarvis doctor`` render."""
    ladders = load_ladders()
    return {
        "purposes": {
            purpose: [
                {
                    "engine": r.engine,
                    "model": r.model,
                    "timeout": r.timeout,
                    "available": COOLDOWNS.available(r.key),
                }
                for r in rungs
            ]
            for purpose, rungs in ladders.items()
        },
        "cooldowns": COOLDOWNS.status(),
    }
