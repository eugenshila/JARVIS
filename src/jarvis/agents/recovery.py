"""
agents/recovery.py — decide what to do when a step fails.

WHY THIS EXISTS
    The ReAct loop had one failure mode: a tool raised, the observation became
    "Error: ...", and the model either gave up or retried the identical call
    forever. There was no distinction between "the network blipped" (try again)
    and "that file will never exist" (stop).

THE DESIGN
    A failure is classified into one of four decisions:

      RETRY   transient — network timeout, temporary lock, race. The same step
              can succeed unchanged.
      SKIP    not critical — the overall task can still succeed without it.
      REPLAN  the approach was wrong — a different tool or argument is needed.
      ABORT   fundamentally impossible or unsafe to continue.

    Classification is cheap and mostly deterministic: a rule table handles the
    obvious cases (timeouts, rate limits, permission denied, file not found)
    with no model call at all. Only genuinely ambiguous failures go to the
    model, and they go to the FAST ladder, not the SMART one.

    Every decision carries a ``user_message`` of at most fifteen words, because
    it is meant to be spoken.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from jarvis.core.types import Message, Role


class Decision(str, Enum):
    RETRY = "retry"
    SKIP = "skip"
    REPLAN = "replan"
    ABORT = "abort"


@dataclass
class Recovery:
    decision: Decision
    reason: str = ""
    fix_suggestion: str = ""
    max_retries: int = 1
    user_message: str = ""
    source: str = "rules"  # "rules" | "model" | "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "fix_suggestion": self.fix_suggestion,
            "max_retries": self.max_retries,
            "user_message": self.user_message,
            "source": self.source,
        }


def _clip_words(text: str, limit: int = 15) -> str:
    words = str(text).split()
    return " ".join(words[:limit])


# ── The rule table ────────────────────────────────────────────────────────────
#
# Ordered; first match wins. These cover the failures that actually happen, and
# handling them here means the common case costs no tokens and no latency.

_RULES: list[tuple[re.Pattern[str], Recovery]] = [
    (
        re.compile(r"timed?\s*out|timeout|deadline exceeded|etimedout", re.IGNORECASE),
        Recovery(Decision.RETRY, "Request timed out.", max_retries=2,
                 user_message="That timed out, sir. Trying again."),
    ),
    (
        re.compile(r"\b(429|rate[ _-]?limit|too many requests|quota)\b", re.IGNORECASE),
        Recovery(Decision.RETRY, "Rate limited or out of quota.", max_retries=1,
                 user_message="Rate limited. Falling back and retrying."),
    ),
    (
        re.compile(r"\b(50[0234]|bad gateway|service unavailable|server error)\b", re.IGNORECASE),
        Recovery(Decision.RETRY, "Upstream server error.", max_retries=2,
                 user_message="The service hiccuped. Retrying."),
    ),
    (
        re.compile(r"connection (refused|reset|aborted)|temporarily unavailable|network is unreachable", re.IGNORECASE),
        Recovery(Decision.RETRY, "Transient network failure.", max_retries=2,
                 user_message="Network dropped. Trying once more."),
    ),
    (
        re.compile(r"resource temporarily unavailable|being used by another process|file is locked", re.IGNORECASE),
        Recovery(Decision.RETRY, "Resource was locked.", max_retries=2,
                 user_message="Something had it locked. Retrying."),
    ),
    (
        re.compile(r"no such (file|directory)|filenotfound|not found on disk", re.IGNORECASE),
        Recovery(Decision.REPLAN, "The path does not exist.",
                 fix_suggestion="Locate the file first, or create it, before operating on it.",
                 user_message="That path does not exist. Trying another way."),
    ),
    (
        re.compile(r"unknown tool|no such tool|tool .* not found", re.IGNORECASE),
        Recovery(Decision.REPLAN, "The chosen tool does not exist.",
                 fix_suggestion="Pick a tool from the available list.",
                 user_message="Wrong tool for that. Rethinking."),
    ),
    (
        re.compile(r"missing (required )?(argument|parameter)|unexpected keyword|typeerror", re.IGNORECASE),
        Recovery(Decision.REPLAN, "The tool was called with the wrong arguments.",
                 fix_suggestion="Re-read the tool schema and supply the required parameters.",
                 user_message="I called that wrong. Correcting."),
    ),
    (
        re.compile(r"permission denied|access is denied|\b(401|403)\b|not authori[sz]ed|forbidden", re.IGNORECASE),
        Recovery(Decision.ABORT, "Not permitted.",
                 user_message="I am not permitted to do that, sir."),
    ),
    (
        re.compile(r"api[ _-]?key|credentials? (not|missing)|unauthenticated", re.IGNORECASE),
        Recovery(Decision.ABORT, "Missing or invalid credentials.",
                 user_message="That needs credentials I do not have."),
    ),
    (
        re.compile(r"awaiting confirmation|confirmation required|pending confirmation", re.IGNORECASE),
        Recovery(Decision.SKIP, "Waiting on the user to confirm — not a failure.",
                 user_message="Waiting on your confirmation, sir."),
    ),
    (
        re.compile(r"not installed|no module named|command not found|is not recognized", re.IGNORECASE),
        Recovery(Decision.SKIP, "An optional dependency is absent.",
                 user_message="That capability is not installed. Skipping it."),
    ),
    (
        re.compile(r"disk (is )?full|no space left", re.IGNORECASE),
        Recovery(Decision.ABORT, "Out of disk space.",
                 user_message="The disk is full, sir. Stopping here."),
    ),
]


_CLASSIFIER_PROMPT = """You are the error-recovery module of JARVIS.

A task step has failed. Decide what to do.

DECISIONS
  retry   Transient error (network blip, temporary lock, race). The same step,
          unchanged, can succeed if tried again.
  skip    This step is not critical; the overall task can succeed without it.
  replan  The approach was wrong. A different tool or different arguments are
          needed.
  abort   The task is fundamentally impossible or unsafe to continue.

Return ONLY valid JSON, no prose, no code fences:
{"decision": "retry|skip|replan|abort",
 "reason": "one sentence on why it failed",
 "fix_suggestion": "what to try instead (only for replan, else empty)",
 "max_retries": 1,
 "user_message": "what to tell the user, MAXIMUM 15 WORDS"}"""


def _extract_json(text: str) -> dict[str, Any] | None:
    text = re.sub(r"^```(?:json)?|```$", "", str(text).strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def classify(
    error: str,
    step: str = "",
    goal: str = "",
    attempt: int = 1,
    engine: Any = None,
    use_model: bool = True,
) -> Recovery:
    """Decide how to handle a failed step.

    Tries the rule table first (free, instant). Falls back to the FAST model
    ladder only when nothing matches, and falls back again to a safe default
    if the model is unavailable or answers with nonsense.
    """
    text = str(error or "").strip()
    if not text:
        return Recovery(Decision.SKIP, "Empty error.", user_message="That returned nothing. Moving on.",
                        source="default")

    for pattern, template in _RULES:
        if pattern.search(text):
            rec = Recovery(**{**template.to_dict(), "decision": template.decision})
            rec.source = "rules"
            # A rule that says retry stops saying so once we have used up the
            # attempts it allowed for.
            if rec.decision is Decision.RETRY and attempt > rec.max_retries:
                return Recovery(
                    Decision.REPLAN,
                    f"Retried {attempt - 1} times and it kept failing: {rec.reason}",
                    fix_suggestion="Try a different tool or a different approach.",
                    user_message="Retries did not help. Trying another way.",
                    source="rules",
                )
            return rec

    if not use_model:
        return _default_for(attempt)

    try:
        if engine is None:
            from jarvis.engine.ladder import FAST, for_purpose

            engine = for_purpose(FAST)
        messages = [
            Message(role=Role.SYSTEM, content=_CLASSIFIER_PROMPT),
            Message(
                role=Role.USER,
                content=(
                    f"GOAL: {goal or '(unknown)'}\n"
                    f"FAILED STEP: {step or '(unknown)'}\n"
                    f"ATTEMPT: {attempt}\n"
                    f"ERROR: {text[:1500]}"
                ),
            ),
        ]
        parsed = _extract_json(engine.generate(messages).content)
    except Exception:
        parsed = None

    if not parsed:
        return _default_for(attempt)

    try:
        decision = Decision(str(parsed.get("decision", "")).strip().lower())
    except ValueError:
        return _default_for(attempt)

    try:
        max_retries = max(0, min(2, int(parsed.get("max_retries", 1))))
    except (TypeError, ValueError):
        max_retries = 1

    if decision is Decision.RETRY and attempt > max_retries:
        decision = Decision.REPLAN

    return Recovery(
        decision=decision,
        reason=str(parsed.get("reason", ""))[:300],
        fix_suggestion=str(parsed.get("fix_suggestion", ""))[:300],
        max_retries=max_retries,
        user_message=_clip_words(parsed.get("user_message", "") or "Something failed, sir."),
        source="model",
    )


def _default_for(attempt: int) -> Recovery:
    """When we genuinely cannot tell: one retry, then replan, never a loop."""
    if attempt <= 1:
        return Recovery(Decision.RETRY, "Unclassified failure; one retry.", max_retries=1,
                        user_message="That failed. Trying once more.", source="default")
    return Recovery(Decision.REPLAN, "Unclassified failure that survived a retry.",
                    fix_suggestion="Try a different tool or approach.",
                    user_message="Still failing. Trying a different approach.", source="default")


@dataclass
class RetryBudget:
    """Guards a loop against burning its whole budget on one bad step."""

    total: int = 6
    per_step: int = 2
    _spent: int = field(default=0, init=False)
    _by_step: dict[str, int] = field(default_factory=dict, init=False)

    def allows(self, step_key: str) -> bool:
        return self._spent < self.total and self._by_step.get(step_key, 0) < self.per_step

    def spend(self, step_key: str) -> int:
        self._spent += 1
        self._by_step[step_key] = self._by_step.get(step_key, 0) + 1
        return self._by_step[step_key]

    def attempts(self, step_key: str) -> int:
        return self._by_step.get(step_key, 0)
