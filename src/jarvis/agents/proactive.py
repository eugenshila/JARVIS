"""
agents/proactive.py — deciding WHEN to speak unprompted.

An assistant that volunteers things is either useful or intolerable, and the
difference is almost entirely timing and repetition. This module owns both and
deliberately owns nothing else: the model decides *what* to say, this decides
whether it may say anything at all.

THE GATES, IN ORDER
    1. Enabled at all (off by default — nobody should be surprised by this).
    2. Quiet hours: never during the night.
    3. The user has been silent for at least ``min_silence`` (they are not
       mid-thought).
    4. We last spoke unprompted at least ``cooldown`` ago.
    5. JARVIS is not currently speaking or executing a task.

NON-REPETITION
    A proactive assistant that opens with the same line every time gets muted
    within a day. Two mechanisms: the *focus* rotates through the available
    context areas, and a hash of each generated opener is remembered so the
    same message is not delivered twice in a session.
"""

from __future__ import annotations

import hashlib
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

#: Focus areas, rotated so consecutive nudges are never about the same thing.
FOCUS_AREAS = ("priorities", "monitors", "calendar", "wellbeing")


@dataclass
class ProactiveConfig:
    enabled: bool = False  # opt-in: never surprise a new user
    min_silence: float = 900.0  # 15 min — they are not mid-thought
    cooldown: float = 1200.0  # 20 min between unprompted messages
    quiet_start_hour: int = 22
    quiet_end_hour: int = 7
    max_per_day: int = 6


@dataclass
class ProactiveEngine:
    config: ProactiveConfig = field(default_factory=ProactiveConfig)
    _last_triggered: float = 0.0
    _rotation: int = 0
    _sent_today: int = 0
    _day: str = ""
    _recent_hashes: deque = field(default_factory=lambda: deque(maxlen=20))

    # -- the gate -----------------------------------------------------------

    def _in_quiet_hours(self, when: datetime) -> bool:
        start, end = self.config.quiet_start_hour, self.config.quiet_end_hour
        hour = when.hour
        if start == end:
            return False
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end  # window wraps midnight

    def _roll_day(self, when: datetime) -> None:
        today = when.strftime("%Y-%m-%d")
        if today != self._day:
            self._day = today
            self._sent_today = 0

    def should_speak(
        self,
        last_user_activity: float,
        now: float | None = None,
        wall_clock: datetime | None = None,
        busy: bool = False,
    ) -> tuple[bool, str]:
        """Returns ``(allowed, why_not)`` — the reason is for logs, not users."""
        now = time.monotonic() if now is None else now
        wall_clock = wall_clock or datetime.now()
        self._roll_day(wall_clock)

        if not self.config.enabled:
            return False, "proactive mode is off"
        if self._in_quiet_hours(wall_clock):
            return False, "quiet hours"
        if busy:
            return False, "busy speaking or executing"
        if self._sent_today >= self.config.max_per_day:
            return False, "daily limit reached"
        silence = now - last_user_activity
        if silence < self.config.min_silence:
            return False, f"user active {silence:.0f}s ago"
        since_last = now - self._last_triggered
        if self._last_triggered and since_last < self.config.cooldown:
            return False, f"cooldown, {self.config.cooldown - since_last:.0f}s left"
        return True, ""

    def mark_spoken(
        self,
        message: str = "",
        now: float | None = None,
        wall_clock: datetime | None = None,
    ) -> None:
        # Roll the day here too, not only in should_speak: otherwise the first
        # gate check after a message resets the counter we just incremented,
        # and the daily limit never bites.
        self._roll_day(wall_clock or datetime.now())
        self._last_triggered = time.monotonic() if now is None else now
        self._rotation += 1
        self._sent_today += 1
        if message:
            self._recent_hashes.append(self._fingerprint(message))

    # -- non-repetition -----------------------------------------------------

    @staticmethod
    def _fingerprint(message: str) -> str:
        normalised = " ".join(str(message).lower().split())
        return hashlib.sha1(normalised.encode("utf-8")).hexdigest()[:16]

    def is_repeat(self, message: str) -> bool:
        return self._fingerprint(message) in self._recent_hashes

    @property
    def focus(self) -> str:
        return FOCUS_AREAS[self._rotation % len(FOCUS_AREAS)]

    # -- the prompt ---------------------------------------------------------

    def build_prompt(
        self,
        profile_text: str = "",
        monitors: list[str] | None = None,
        recent_turns: list[str] | None = None,
        wall_clock: datetime | None = None,
    ) -> str:
        """Context for the model, focused on one area so nudges differ."""
        wall_clock = wall_clock or datetime.now()
        hour = wall_clock.hour
        part = (
            "early morning" if hour < 9
            else "morning" if hour < 12
            else "afternoon" if hour < 17
            else "evening" if hour < 22
            else "night"
        )
        focus = self.focus
        lines = [
            "You may say ONE short unprompted thing to the user. They have been "
            "quiet for a while; you are interrupting, so it must earn its place.",
            "",
            f"Time: {wall_clock:%A %H:%M} ({part}).",
            f"Focus this time on: {focus}. Do not cover the other areas.",
        ]
        if profile_text:
            lines += ["", profile_text]
        if monitors:
            lines += ["", "Topics the user asked to be kept across: " + ", ".join(monitors[:8])]
        if recent_turns:
            lines += ["", "Recent conversation:"] + [f"  {t}" for t in recent_turns[-4:]]
        lines += [
            "",
            "Rules: one or two sentences. Concrete and actionable, never small talk. "
            "If you have nothing genuinely worth interrupting for, reply with exactly "
            "NOTHING and it will not be delivered.",
        ]
        return "\n".join(lines)

    @staticmethod
    def is_declined(reply: str) -> bool:
        """The model's way of saying 'nothing worth saying'."""
        return str(reply).strip().upper().rstrip(".") in ("NOTHING", "")

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.config.enabled,
            "focus_next": self.focus,
            "sent_today": self._sent_today,
            "max_per_day": self.config.max_per_day,
            "min_silence": self.config.min_silence,
            "cooldown": self.config.cooldown,
        }
