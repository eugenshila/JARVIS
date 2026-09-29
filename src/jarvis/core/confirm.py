"""
core/confirm.py — a confirmation the model cannot forge.

WHY THIS EXISTS
    Several JARVIS tools guard dangerous work with a ``confirm`` *tool
    parameter*::

        if not confirm:
            return "Run again with confirm=true."

    The model writes that parameter. Nothing stops it from sending
    ``confirm=true`` on the first call, and nothing checks that a human was
    ever involved. It is a convention, not a gate.

THE DESIGN HERE
    The confirmation token is issued by the *interface*, never by the model:

      1. A tool calls :func:`request` with a callable that does the real work.
      2. This module records a pending request and returns IMMEDIATELY with a
         sentence for the model to say out loud, plus the token.
      3. The UI (React HUD, CLI prompt, ...) shows CONFIRM / CANCEL and calls
         :func:`resolve` with that token only when a human acts.

    Nothing blocks, so this costs no latency. A pending request expires after
    :data:`TIMEOUT_SECONDS` so a live "shut down the machine" button never sits
    on the HUD for the rest of the day.

WHAT BELONGS HERE AND WHAT DOES NOT
    Only genuinely irreversible things. Anything reversible should be done at
    once and pushed onto :mod:`jarvis.core.undo` instead — undo is faster than
    a question, and an assistant that asks before every action is one nobody
    uses.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
from collections.abc import Callable

#: A pending confirmation is abandoned after this long. Long enough to outlast
#: a "hang on, let me look" pause; short enough that the button does not linger.
TIMEOUT_SECONDS = 90.0

#: Most a user can have queued at once. Prevents a looping agent from filling
#: the HUD with confirmation banners.
MAX_PENDING = 5


@dataclass
class PendingConfirmation:
    token: str
    title: str
    detail: str
    run: Callable[[], str] = field(repr=False)
    created_at: float = field(default_factory=time.monotonic)

    def expired(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        return (now - self.created_at) >= TIMEOUT_SECONDS

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "title": self.title,
            "detail": self.detail,
            "expires_in": max(
                0.0, TIMEOUT_SECONDS - (time.monotonic() - self.created_at)
            ),
        }


class ConfirmationError(RuntimeError):
    """Raised when a token is unknown, already used, or expired."""


_pending: dict[str, PendingConfirmation] = {}
_lock = threading.Lock()


def _reap(now: float | None = None) -> None:
    """Drop expired entries. Callers must hold ``_lock``."""
    now = time.monotonic() if now is None else now
    for token in [t for t, p in _pending.items() if p.expired(now)]:
        _pending.pop(token, None)


def request(title: str, detail: str, run: Callable[[], str]) -> PendingConfirmation:
    """Register work that needs a human CONFIRM before it may happen.

    Returns immediately — ``run`` is *not* called here. The caller should
    return :meth:`PendingConfirmation.spoken` (or its own sentence) to the
    model so it can tell the user a confirmation is waiting.
    """
    if not callable(run):
        raise TypeError("run must be callable")
    with _lock:
        _reap()
        if len(_pending) >= MAX_PENDING:
            # Drop the oldest rather than refusing: a stale banner is less
            # useful than the request the user just made.
            oldest = min(_pending.values(), key=lambda p: p.created_at)
            _pending.pop(oldest.token, None)
        entry = PendingConfirmation(
            token=secrets.token_urlsafe(16),
            title=str(title),
            detail=str(detail),
            run=run,
        )
        _pending[entry.token] = entry
    return entry


def pending() -> list[dict]:
    """Everything currently awaiting a human decision (for the UI to render)."""
    with _lock:
        _reap()
        return [p.to_dict() for p in sorted(_pending.values(), key=lambda p: p.created_at)]


def get(token: str) -> PendingConfirmation | None:
    with _lock:
        _reap()
        return _pending.get(token)


def resolve(token: str) -> str:
    """A human pressed CONFIRM. Runs the stored callable and returns its result.

    Raises :class:`ConfirmationError` if the token is unknown or expired. The
    entry is removed *before* the callable runs, so a double-click cannot run
    the work twice.
    """
    with _lock:
        _reap()
        entry = _pending.pop(token, None)
    if entry is None:
        raise ConfirmationError("No such pending confirmation (unknown, used, or expired).")
    return entry.run()


def cancel(token: str) -> bool:
    """A human pressed CANCEL. Returns True if something was actually dropped."""
    with _lock:
        _reap()
        return _pending.pop(token, None) is not None


def cancel_all() -> int:
    with _lock:
        count = len(_pending)
        _pending.clear()
        return count


def clear() -> None:
    """Test helper — drop all state."""
    cancel_all()
