"""
tools/monitor_tools.py — topics the user asked to be kept across.

WHAT THIS IS
    The user says "keep an eye on the Kenyan fintech licensing rules". The
    topic is stored, checked at most once a day, and new headlines are
    reported. That is all.

WHAT THIS IS NOT
    It is not ambient tracking. Three deliberate limits:

    * **Only what was explicitly asked for.** Nothing is monitored implicitly,
      ever. There is no "we noticed you talked about X" path into this list.
    * **A blocklist.** Crypto and speculative-asset topics are refused
      outright, in several spellings. An assistant that volunteers price moves
      is a trading nag that manufactures urgency, and the person most harmed
      is the one who asked for it at 2am. Refusing is the feature.
    * **Once per day, deduplicated by headline hash.** No polling loops, no
      repeating the same story because the wording changed slightly.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from jarvis.tools.base import BaseTool, ToolSpec

MAX_TOPICS = 10
CHECK_INTERVAL_SECONDS = 23 * 3600  # "once a day", minus drift
MAX_SEEN_PER_TOPIC = 60

#: Refused regardless of phrasing. Spelled across the languages where the root
#: is written differently, because the harm does not stop at English.
_BLOCKED = (
    "bitcoin", "ethereum", "dogecoin", "solana", "binance", "coinbase",
    "nft", "blockchain", "defi", "altcoin", "memecoin", "shitcoin",
    "crypto", "cryptocurrency", "kripto", "cripto", "krypto",
    "крипто", "仮想通貨", "暗号資産",
    "forex", "day trading", "penny stock", "pump and dump",
)


def is_blocked(topic: str) -> bool:
    lowered = str(topic).lower()
    return any(word in lowered for word in _BLOCKED)


def _slug(topic: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(topic).lower().strip())[:48].strip("_")


def _headline_hash(title: str) -> str:
    normalised = " ".join(str(title).lower().split())
    return hashlib.sha1(normalised.encode("utf-8")).hexdigest()[:12]


def _store_path() -> Path:
    from jarvis.core.config import get_home

    return get_home() / "memory" / "monitors.json"


def load_monitors() -> dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_monitors(monitors: dict[str, Any]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(monitors, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def due_topics(now: float | None = None) -> list[str]:
    """Which monitors may be checked right now."""
    now = time.time() if now is None else now
    return [
        entry.get("topic", key)
        for key, entry in load_monitors().items()
        if now - float(entry.get("last_checked", 0) or 0) >= CHECK_INTERVAL_SECONDS
    ]


def _search(topic: str, limit: int = 5) -> list[str]:
    """Headlines for a topic, via whichever search tool is configured."""
    from jarvis.tools.registry import get_tool

    tool = get_tool("web_search")
    if tool is None:
        return []
    try:
        raw = str(tool.run(query=f"{topic} news"))
    except Exception:
        return []
    titles: list[str] = []
    for line in raw.splitlines():
        text = line.strip(" -•*\t")
        if len(text) > 25 and not text.lower().startswith(("http", "error", "no results")):
            titles.append(text[:200])
        if len(titles) >= limit:
            break
    return titles


class TopicMonitorTool(BaseTool):
    spec = ToolSpec(
        name="topic_monitor",
        description=(
            "Keep the user across a topic they explicitly asked to follow, checking "
            "at most once a day and reporting only headlines not seen before. Use "
            "when the user says 'keep an eye on X', 'let me know if anything happens "
            "with Y', or asks what is new on something they are already following. "
            "Speculative-asset topics (crypto, forex, day trading) are refused."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "remove", "list", "check"],
                    "default": "list",
                },
                "topic": {"type": "string", "description": "What to follow"},
            },
            "required": [],
        },
    )

    def run(self, action: str = "list", topic: str = "", **kwargs) -> str:
        action = str(action).strip().lower()
        if action == "add":
            return self._add(topic)
        if action == "remove":
            return self._remove(topic)
        if action == "check":
            return self._check(topic)
        return self._list()

    # -- verbs --------------------------------------------------------------

    def _add(self, topic: str) -> str:
        topic = str(topic).strip()
        if not topic:
            return "What should I keep an eye on, sir?"
        if is_blocked(topic):
            return (
                f"I will not monitor '{topic}', sir. Speculative-asset alerts manufacture "
                "urgency and are the last thing anyone needs pushed at them unprompted. "
                "Ask me about it directly whenever you like."
            )
        monitors = load_monitors()
        if len(monitors) >= MAX_TOPICS and _slug(topic) not in monitors:
            return f"I am already following {len(monitors)} topics — the limit. Remove one first."
        monitors[_slug(topic)] = {
            "topic": topic,
            "added": time.time(),
            "last_checked": 0,
            "seen": monitors.get(_slug(topic), {}).get("seen", []),
        }
        save_monitors(monitors)
        return f"Following '{topic}'. I will check once a day and mention anything new."

    def _remove(self, topic: str) -> str:
        monitors = load_monitors()
        key = _slug(topic)
        if key not in monitors:
            return f"I was not following '{topic}'."
        monitors.pop(key)
        save_monitors(monitors)
        return f"Stopped following '{topic}'."

    def _list(self) -> str:
        monitors = load_monitors()
        if not monitors:
            return "I am not following any topics, sir."
        lines = [f"Following {len(monitors)} topic(s):"]
        now = time.time()
        for entry in monitors.values():
            last = float(entry.get("last_checked", 0) or 0)
            when = "never checked" if not last else f"checked {(now - last) / 3600:.0f}h ago"
            lines.append(f"  • {entry.get('topic')} ({when}, {len(entry.get('seen', []))} seen)")
        return "\n".join(lines)

    def _check(self, topic: str = "") -> str:
        monitors = load_monitors()
        if not monitors:
            return "I am not following any topics, sir."

        now = time.time()
        targets = (
            [k for k in monitors if k == _slug(topic)] if topic
            else [
                k for k, e in monitors.items()
                if now - float(e.get("last_checked", 0) or 0) >= CHECK_INTERVAL_SECONDS
            ]
        )
        if not targets:
            return "Nothing is due for a check yet, sir." if not topic else f"I am not following '{topic}'."

        report: list[str] = []
        for key in targets:
            entry = monitors[key]
            seen = set(entry.get("seen", []))
            fresh = []
            for title in _search(entry.get("topic", key)):
                digest = _headline_hash(title)
                if digest in seen:
                    continue
                seen.add(digest)
                fresh.append(title)
            entry["last_checked"] = now
            entry["seen"] = list(seen)[-MAX_SEEN_PER_TOPIC:]
            if fresh:
                report.append(f"{entry.get('topic')}:")
                report += [f"  • {t}" for t in fresh[:3]]
        save_monitors(monitors)
        return "\n".join(report) if report else "Nothing new on the topics you follow, sir."
