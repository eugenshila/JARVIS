"""
core/undo.py — one shared undo stack for every action that changes state.

WHY THIS EXISTS
    An assistant misunderstands. When it does, "sorry" is not a remedy — the
    file is already in another folder. The alternative, asking "are you sure?"
    before everything, is worse: an assistant that checks with you before
    turning the volume down is one you stop talking to.

    So: act immediately, remember how to reverse it, and let the user say
    "undo". Confirmation is reserved for the handful of actions that genuinely
    cannot be reversed — see :mod:`jarvis.core.confirm`.

HOW A TOOL OPTS IN
    Tools capture the "before" state and hand back a zero-argument callable::

        from jarvis.core.undo import push_undo

        old = path.read_text()
        path.write_text(new)
        push_undo(f"write {path.name}", lambda: (path.write_text(old), "restored")[1])

    Only the tool can know that the reverse of "move A to B" is "move B to A",
    which is why this cannot be fully centralised. What IS central is the
    stack, the ordering, the thread safety and the tool the model calls.

COST
    Pushing is a list append behind a lock. Nothing here runs until the user
    actually asks to undo something.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from collections.abc import Callable

#: How many reversible operations we keep. Ten is roughly "this conversation":
#: far enough back to catch a mistake noticed a few commands later, short
#: enough that a closure holding a file's old contents cannot pile up in RAM.
MAX_DEPTH = 10


@dataclass
class UndoEntry:
    label: str
    undo: Callable[[], str] = field(repr=False)
    at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"label": self.label, "at": self.at, "age": max(0.0, time.time() - self.at)}


_stack: list[UndoEntry] = []
_lock = threading.Lock()


def push_undo(label: str, undo_fn: Callable[[], str]) -> None:
    """Record how to reverse the operation that just happened.

    ``label`` is a short human sentence ("volume -> 40%") that gets spoken back
    to the user. ``undo_fn`` takes no arguments and returns a short result
    string. Never raises out of here: a failure to *record* an undo must not
    fail the operation that succeeded.
    """
    if not callable(undo_fn):
        return
    entry = UndoEntry(label=str(label), undo=undo_fn)
    with _lock:
        _stack.append(entry)
        while len(_stack) > MAX_DEPTH:
            _stack.pop(0)


def undo_last() -> str:
    """Reverse the most recent reversible operation."""
    with _lock:
        entry = _stack.pop() if _stack else None
    if entry is None:
        return "Nothing to undo, sir."
    try:
        result = entry.undo()
    except Exception as exc:  # the reverse itself can fail (file gone, etc.)
        return f"Could not undo '{entry.label}': {exc}"
    return f"Undone: {entry.label}." + (f" {result}" if result else "")


def history() -> list[dict]:
    """Most recent first — what the UI shows and what the model can describe."""
    with _lock:
        return [e.to_dict() for e in reversed(_stack)]


def depth() -> int:
    with _lock:
        return len(_stack)


def clear() -> None:
    with _lock:
        _stack.clear()
