"""
core/task_queue.py — priority-ordered, cancellable background work.

WHY THIS EXISTS
    Every long-running thing JARVIS did blocked whatever asked for it. A
    five-minute research run and a one-second light switch went down the same
    path, nothing could be cancelled once started, and the HUD had no way to
    show "I am working on three things".

THE DESIGN
    A small priority queue with a worker pool:

      * Tasks carry a :class:`Priority`. HIGH work jumps the queue; ties break
        by submission order, so the queue is stable and never starves a task
        that has been waiting.
      * Every task gets a :class:`threading.Event` cancel flag. Long work is
        expected to check ``task.cancelled`` between steps; a task that has not
        started yet is cancelled outright.
      * Results, errors and state transitions are recorded on the task, so the
        HUD can poll :meth:`TaskQueue.snapshot` and render progress without
        holding anything open.

    This is deliberately threads, not asyncio: the work it wraps is tool calls
    and HTTP requests made by synchronous library code.
"""

from __future__ import annotations

import heapq
import itertools
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)


class Priority(int, Enum):
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class Task:
    """One unit of background work and everything known about it."""

    goal: str
    run: Callable[[Task], Any] = field(repr=False)
    priority: Priority = Priority.NORMAL
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    progress: str = ""
    on_complete: Callable[[Task], None] | None = field(default=None, repr=False)
    _cancel: threading.Event = field(default_factory=threading.Event, repr=False)
    _done: threading.Event = field(default_factory=threading.Event, repr=False)

    # -- cooperative cancellation ------------------------------------------

    @property
    def cancelled(self) -> bool:
        """Long-running work should check this between steps and bail out."""
        return self._cancel.is_set()

    def cancel(self) -> None:
        self._cancel.set()

    def note(self, message: str) -> None:
        """Report progress for the UI. Cheap; safe to call often."""
        self.progress = str(message)[:300]

    def wait(self, timeout: float | None = None) -> bool:
        """Block until the task reaches a terminal state."""
        return self._done.wait(timeout)

    @property
    def duration(self) -> float | None:
        if self.started_at is None:
            return None
        return (self.finished_at or time.time()) - self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "priority": self.priority.name,
            "status": self.status.value,
            "progress": self.progress,
            "error": self.error,
            "result": _summarise(self.result),
            "created_at": self.created_at,
            "duration": self.duration,
        }


def _summarise(result: Any, limit: int = 500) -> Any:
    if result is None or isinstance(result, (int, float, bool)):
        return result
    text = str(result)
    return text if len(text) <= limit else text[:limit] + "…"


class TaskQueue:
    """A priority queue with worker threads. Start it, submit to it, poll it."""

    def __init__(self, workers: int = 1, history: int = 50) -> None:
        self.workers = max(1, workers)
        self._heap: list[tuple[int, int, str]] = []
        self._tasks: dict[str, Task] = {}
        self._order = itertools.count()
        self._history_limit = max(0, history)
        self._lock = threading.Lock()
        self._wake = threading.Condition(self._lock)
        self._threads: list[threading.Thread] = []
        self._running = False

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._threads = [
                threading.Thread(target=self._worker, name=f"jarvis-task-{i}", daemon=True)
                for i in range(self.workers)
            ]
        for t in self._threads:
            t.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stop accepting work, signal in-flight tasks, and join the workers."""
        with self._wake:
            self._running = False
            for task in self._tasks.values():
                if not task.status.terminal:
                    task.cancel()
            self._wake.notify_all()
        for t in self._threads:
            t.join(timeout=timeout)
        self._threads = []

    # -- submission ---------------------------------------------------------

    def submit(
        self,
        goal: str,
        run: Callable[[Task], Any],
        priority: Priority = Priority.NORMAL,
        on_complete: Callable[[Task], None] | None = None,
    ) -> Task:
        task = Task(goal=goal, run=run, priority=priority, on_complete=on_complete)
        with self._wake:
            if not self._running:
                self.start_locked_hint()
            self._tasks[task.task_id] = task
            # (priority, submission order) keeps the ordering stable: HIGH work
            # jumps the queue, but equal priorities are strictly FIFO so nothing
            # waiting can be starved by a stream of new arrivals.
            heapq.heappush(self._heap, (int(task.priority), next(self._order), task.task_id))
            self._wake.notify()
        return task

    def start_locked_hint(self) -> None:
        """Auto-start on first submit. Called with the lock already held."""
        self._running = True
        self._threads = [
            threading.Thread(target=self._worker, name=f"jarvis-task-{i}", daemon=True)
            for i in range(self.workers)
        ]
        for t in self._threads:
            t.start()

    # -- inspection ---------------------------------------------------------

    def get(self, task_id: str) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        """Cancel a task. Pending tasks never run; running tasks are signalled."""
        with self._wake:
            task = self._tasks.get(task_id)
            if task is None or task.status.terminal:
                return False
            task.cancel()
            if task.status is TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.finished_at = time.time()
                task._done.set()
            self._wake.notify_all()
            return True

    def snapshot(self) -> dict[str, Any]:
        """What the HUD renders: active work first, then recent history."""
        with self._lock:
            tasks = sorted(self._tasks.values(), key=lambda t: t.created_at)
        active = [t.to_dict() for t in tasks if not t.status.terminal]
        done = [t.to_dict() for t in tasks if t.status.terminal]
        return {
            "active": active,
            "recent": list(reversed(done))[: self._history_limit],
            "counts": {
                "active": len(active),
                "pending": sum(1 for t in tasks if t.status is TaskStatus.PENDING),
                "running": sum(1 for t in tasks if t.status is TaskStatus.RUNNING),
            },
        }

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.status is TaskStatus.PENDING)

    # -- the worker ---------------------------------------------------------

    def _next_task(self) -> Task | None:
        with self._wake:
            while self._running:
                while self._heap:
                    _, _, task_id = heapq.heappop(self._heap)
                    task = self._tasks.get(task_id)
                    if task is None or task.status.terminal:
                        continue  # cancelled while queued
                    if task.cancelled:
                        task.status = TaskStatus.CANCELLED
                        task.finished_at = time.time()
                        task._done.set()
                        continue
                    task.status = TaskStatus.RUNNING
                    task.started_at = time.time()
                    return task
                self._wake.wait(timeout=0.5)
            return None

    def _worker(self) -> None:
        while True:
            task = self._next_task()
            if task is None:
                return
            try:
                result = task.run(task)
                if task.cancelled:
                    task.status = TaskStatus.CANCELLED
                else:
                    task.result = result
                    task.status = TaskStatus.COMPLETED
            except Exception as exc:
                task.error = f"{type(exc).__name__}: {exc}"
                task.status = TaskStatus.CANCELLED if task.cancelled else TaskStatus.FAILED
            finally:
                task.finished_at = time.time()
                task._done.set()
                self._trim()
                if task.on_complete:
                    try:
                        task.on_complete(task)
                    except Exception:
                        pass  # a bad callback must not kill the worker

    def _trim(self) -> None:
        """Keep finished tasks bounded so a long session cannot grow forever."""
        with self._lock:
            finished = sorted(
                (t for t in self._tasks.values() if t.status.terminal),
                key=lambda t: t.finished_at or 0,
            )
            for task in finished[: max(0, len(finished) - self._history_limit)]:
                self._tasks.pop(task.task_id, None)


_default: TaskQueue | None = None
_default_lock = threading.Lock()


def get_queue() -> TaskQueue:
    """The process-wide queue the API and CLI share."""
    global _default
    with _default_lock:
        if _default is None:
            _default = TaskQueue(workers=2)
            _default.start()
        return _default


def reset() -> None:
    """Test helper."""
    global _default
    with _default_lock:
        if _default is not None:
            _default.stop(timeout=1.0)
        _default = None
