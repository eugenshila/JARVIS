"""
memory/profile.py — the small set of facts that are ALWAYS in the prompt.

WHY A SECOND MEMORY
    The vector store (:mod:`jarvis.memory.vector_store`) answers "what do I
    know about X?" well. It cannot answer "who am I talking to?", because that
    question is never asked — it has to already be in the system prompt before
    the user says anything. A retrieval store only surfaces a fact when
    something in the query happens to resemble it, so JARVIS could hold a
    thousand memories and still not know the user's name.

    So: two layers. Recall stays in the vector store. A small, curated,
    *always-injected* profile lives here.

THE BUDGET IS THE POINT
    A layer that is always in the prompt is a tax on every single request, so
    it must be bounded — otherwise it grows until it crowds out the
    conversation and slows every call down.

      * categories:  identity, preferences, projects, relationships, goals, notes
      * per value:   MAX_VALUE_CHARS
      * whole file:  MAX_TOTAL_CHARS, enforced by evicting the least valuable
                     entries first — cheap categories before precious ones
                     (``notes`` long before ``identity``), and oldest-updated
                     first within a category. Two hundred scratch notes must
                     never push out the user's name.

    Eviction is what makes this safe to write to freely: the model can record
    whatever it likes, and the budget quietly keeps the prompt small.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CATEGORIES = ("identity", "preferences", "projects", "relationships", "goals", "notes")

#: A single fact longer than this is a document, not a fact — it belongs in the
#: vector store.
MAX_VALUE_CHARS = 400

#: Total serialised budget for everything injected into every prompt.
MAX_TOTAL_CHARS = 2400

#: Evicted first when over budget: cheap to lose, cheapest to re-learn.
_EVICTION_ORDER = ("notes", "projects", "preferences", "relationships", "goals", "identity")

_lock = threading.RLock()


@dataclass
class Fact:
    value: str
    updated: float = field(default_factory=time.time)
    hits: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "updated": self.updated, "hits": self.hits}

    @classmethod
    def from_any(cls, raw: Any) -> Fact:
        if isinstance(raw, dict) and "value" in raw:
            return cls(
                value=str(raw.get("value", ""))[:MAX_VALUE_CHARS],
                updated=float(raw.get("updated", time.time()) or time.time()),
                hits=int(raw.get("hits", 0) or 0),
            )
        return cls(value=str(raw)[:MAX_VALUE_CHARS])


class Profile:
    """The curated facts layer. JSON on disk, one file, atomic writes."""

    def __init__(self, home: Path | None = None) -> None:
        if home is None:
            from jarvis.core.config import get_home

            home = get_home()
        self.path = Path(home) / "memory" / "profile.json"

    # -- persistence --------------------------------------------------------

    def _empty(self) -> dict[str, dict[str, Fact]]:
        return {c: {} for c in CATEGORIES}

    def load(self) -> dict[str, dict[str, Fact]]:
        with _lock:
            if not self.path.exists():
                return self._empty()
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return self._empty()  # a corrupt profile must not break startup
            data = self._empty()
            if isinstance(raw, dict):
                for category, entries in raw.items():
                    if category not in data or not isinstance(entries, dict):
                        continue
                    for key, value in entries.items():
                        data[category][str(key)] = Fact.from_any(value)
            return data

    def _save(self, data: dict[str, dict[str, Fact]]) -> None:
        with _lock:
            data = self._enforce_budget(data)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                c: {k: f.to_dict() for k, f in entries.items()} for c, entries in data.items()
            }
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)

    # -- budget -------------------------------------------------------------

    @staticmethod
    def _serialised_size(data: dict[str, dict[str, Fact]]) -> int:
        return len(
            json.dumps(
                {c: {k: f.value for k, f in e.items()} for c, e in data.items()},
                ensure_ascii=False,
            )
        )

    def _enforce_budget(self, data: dict[str, dict[str, Fact]]) -> dict[str, dict[str, Fact]]:
        if self._serialised_size(data) <= MAX_TOTAL_CHARS:
            return data
        # Category rank dominates, then age. Sorting by age first would evict
        # the user's name (written once, long ago) before a note written this
        # morning, which is exactly backwards.
        def _rank(category: str) -> int:
            return _EVICTION_ORDER.index(category) if category in _EVICTION_ORDER else 0

        candidates = [
            (_rank(c), f.updated, c, k)
            for c, entries in data.items()
            for k, f in entries.items()
        ]
        candidates.sort(key=lambda t: (t[0], t[1]))
        for _, _, category, key in candidates:
            if self._serialised_size(data) <= MAX_TOTAL_CHARS:
                break
            data[category].pop(key, None)
        return data

    # -- the API ------------------------------------------------------------

    def remember(self, category: str, key: str, value: str) -> str:
        category = str(category).strip().lower()
        if category not in CATEGORIES:
            return f"Unknown category {category!r}. Use one of: {', '.join(CATEGORIES)}."
        key = str(key).strip()
        if not key:
            return "A fact needs a key, sir."
        text = str(value).strip()
        if not text:
            return "A fact needs a value, sir."
        truncated = len(text) > MAX_VALUE_CHARS

        data = self.load()
        data[category][key] = Fact(value=text[:MAX_VALUE_CHARS])
        self._save(data)
        note = " (trimmed — long text belongs in the searchable store)" if truncated else ""
        return f"Noted under {category}: {key}{note}."

    def forget(self, category: str, key: str) -> str:
        data = self.load()
        if category in data and key in data[category]:
            data[category].pop(key)
            self._save(data)
            return f"Forgotten: {category}/{key}."
        return f"I had nothing under {category}/{key}."

    def get(self, category: str, key: str) -> str | None:
        fact = self.load().get(category, {}).get(key)
        return fact.value if fact else None

    def all(self) -> dict[str, dict[str, str]]:
        return {c: {k: f.value for k, f in e.items()} for c, e in self.load().items() if e}

    def clear(self) -> None:
        self._save(self._empty())

    # -- what actually goes in the prompt -----------------------------------

    def for_prompt(self) -> str:
        """Render the profile as system-prompt text. Empty string if empty."""
        data = self.all()
        if not any(data.values()):
            return ""
        lines = ["What you already know about the user (do not ask again):"]
        for category in CATEGORIES:
            entries = data.get(category)
            if not entries:
                continue
            lines.append(f"  {category}:")
            for key, value in entries.items():
                lines.append(f"    - {key}: {value}")
        return "\n".join(lines)

    def size(self) -> dict[str, int]:
        data = self.load()
        return {
            "facts": sum(len(e) for e in data.values()),
            "chars": self._serialised_size(data),
            "budget": MAX_TOTAL_CHARS,
        }


_default: Profile | None = None


def get_profile() -> Profile:
    global _default
    if _default is None:
        _default = Profile()
    return _default


def reset() -> None:
    """Test helper — drop the cached instance so JARVIS_HOME is re-read."""
    global _default
    _default = None
