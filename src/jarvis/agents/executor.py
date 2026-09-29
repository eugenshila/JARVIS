"""
agents/executor.py — run a validated plan, recovering from failures.

This is the third piece of plan → queue → execute. The planner
(:mod:`jarvis.agents.planner`) decides *what*; the task queue
(:mod:`jarvis.core.task_queue`) decides *when*; this decides what to do when
reality disagrees with the plan.

Per step:

  * run the tool;
  * if it fails, ask :mod:`jarvis.agents.recovery` for a decision;
  * RETRY within a bounded budget, SKIP and carry on, REPLAN (re-plan the
    *remainder* of the goal once, using what the failure taught us), or ABORT;
  * check for cancellation between steps, so a queued run can be stopped.

Steps deliberately do not reference each other's output as parameters — the
planner is told not to write such plans. Instead each result is appended to a
running transcript, and a REPLAN gets that transcript as context.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from jarvis.agents.planner import Plan, Step
from jarvis.agents.planner import plan as make_plan
from jarvis.agents.recovery import Decision, RetryBudget, classify
from jarvis.tools.registry import get_tool

MAX_REPLANS = 1


@dataclass
class StepResult:
    step: Step
    output: str = ""
    ok: bool = False
    attempts: int = 1
    decision: str = ""
    note: str = ""
    duration: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.step.tool,
            "arguments": self.step.arguments,
            "purpose": self.step.purpose,
            "ok": self.ok,
            "output": self.output[:2000],
            "attempts": self.attempts,
            "decision": self.decision,
            "note": self.note,
            "duration": self.duration,
        }


@dataclass
class ExecutionResult:
    goal: str
    results: list[StepResult] = field(default_factory=list)
    aborted: bool = False
    cancelled: bool = False
    replans: int = 0
    messages: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.aborted and not self.cancelled and all(r.ok or r.decision == "skip" for r in self.results)

    def transcript(self) -> str:
        lines = []
        for i, r in enumerate(self.results, 1):
            status = "ok" if r.ok else (r.decision or "failed")
            lines.append(f"{i}. {r.step.describe()} -> [{status}] {r.output[:400]}")
        return "\n".join(lines)

    def summary(self) -> str:
        done = sum(1 for r in self.results if r.ok)
        head = f"{done}/{len(self.results)} step(s) completed"
        if self.cancelled:
            head = f"Cancelled after {head}"
        elif self.aborted:
            head = f"Stopped after {head}"
        tail = f" ({'; '.join(self.messages[-3:])})" if self.messages else ""
        return head + tail

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "ok": self.ok,
            "aborted": self.aborted,
            "cancelled": self.cancelled,
            "replans": self.replans,
            "messages": self.messages,
            "steps": [r.to_dict() for r in self.results],
        }


def _run_tool(step: Step) -> tuple[str, bool]:
    """Returns ``(output, failed)``. Never raises."""
    tool = get_tool(step.tool)
    if tool is None:
        return f"Error: unknown tool {step.tool}", True
    try:
        output = tool.run(**step.arguments)
    except TypeError as exc:
        return f"Error: {step.tool} called with wrong arguments: {exc}", True
    except Exception as exc:
        return f"Tool error: {exc}", True
    text = str(output)
    failed = text.strip().lower().startswith(("error", "tool error", "failed"))
    return text, failed


def execute(
    plan_obj: Plan,
    engine: Any = None,
    is_cancelled: Callable[[], bool] | None = None,
    progress: Callable[[str], None] | None = None,
    max_replans: int = MAX_REPLANS,
) -> ExecutionResult:
    """Run a plan to completion, or until it aborts or is cancelled."""
    result = ExecutionResult(goal=plan_obj.goal)
    budget = RetryBudget(total=max(3, len(plan_obj.steps) * 2), per_step=2)
    queue = list(plan_obj.steps)
    index = 0

    def _report(message: str) -> None:
        if progress:
            try:
                progress(message)
            except Exception:
                pass

    while index < len(queue):
        if is_cancelled and is_cancelled():
            result.cancelled = True
            result.messages.append("Cancelled, sir.")
            return result

        step = queue[index]
        index += 1
        step_key = f"{step.tool}:{sorted(step.arguments.items())}"
        _report(f"{step.tool}: {step.purpose or 'working'}")

        started = time.monotonic()
        output, failed = _run_tool(step)
        record = StepResult(step=step, output=output, ok=not failed)

        while failed:
            attempt = budget.attempts(step_key) + 1
            recovery = classify(
                error=output,
                step=step.describe(),
                goal=plan_obj.goal,
                attempt=attempt,
                engine=engine,
            )
            record.decision = recovery.decision.value
            record.note = recovery.reason
            if recovery.user_message:
                result.messages.append(recovery.user_message)
                _report(recovery.user_message)

            if recovery.decision is Decision.ABORT:
                result.aborted = True
                break

            if recovery.decision is Decision.RETRY and budget.allows(step_key):
                budget.spend(step_key)
                record.attempts += 1
                if is_cancelled and is_cancelled():
                    result.cancelled = True
                    break
                output, failed = _run_tool(step)
                record.output = output
                record.ok = not failed
                continue

            if recovery.decision is Decision.SKIP:
                record.decision = "skip"
                break

            # REPLAN — or a retry whose budget is spent, which becomes a
            # replan. Re-plan only what is LEFT, with the failure as context,
            # and only once, so a hopeless goal cannot loop.
            if result.replans < max_replans:
                result.replans += 1
                remainder = make_plan(
                    goal=(
                        f"{plan_obj.goal}\n\n"
                        f"Progress so far:\n{result.transcript()}\n"
                        f"The step '{step.describe()}' failed: {recovery.reason}. "
                        f"{recovery.fix_suggestion}\n"
                        "Plan only the remaining work."
                    ),
                    engine=engine,
                )
                if remainder.ok:
                    queue = queue[:index] + remainder.steps
                    _report("Replanned the remaining steps.")
                else:
                    result.aborted = True
            else:
                result.aborted = True
            break

        record.duration = time.monotonic() - started
        result.results.append(record)

        if result.aborted or result.cancelled:
            break

    return result


def run_goal(
    goal: str,
    engine: Any = None,
    tools: list[str] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    progress: Callable[[str], None] | None = None,
) -> tuple[Plan, ExecutionResult]:
    """Plan a goal and execute it. The front door for the whole pipeline."""
    plan_obj = make_plan(goal, engine=engine, tools=tools)
    if not plan_obj.ok:
        empty = ExecutionResult(goal=goal, aborted=True)
        empty.messages.append(
            "I could not build a workable plan: " + "; ".join(plan_obj.errors or ["no steps"])
        )
        return plan_obj, empty
    return plan_obj, execute(
        plan_obj, engine=engine, is_cancelled=is_cancelled, progress=progress
    )


def submit_goal(goal: str, engine: Any = None, tools: list[str] | None = None, priority=None):
    """Run a goal on the shared background queue; returns the :class:`Task`."""
    from jarvis.core.task_queue import Priority, get_queue

    queue = get_queue()

    def _work(task):
        _, execution = run_goal(
            goal,
            engine=engine,
            tools=tools,
            is_cancelled=lambda: task.cancelled,
            progress=task.note,
        )
        return execution.to_dict()

    return queue.submit(goal, _work, priority=priority or Priority.NORMAL)
