"""
Shared guardrails for the JARVIS morning-routine plugin suite.

This module is the single choke point every other file in the suite goes
through to touch the outside world. Its whole reason to exist is the hard rule
the user set: the morning routine observes and plans, it never acts on anyone's
behalf. Concretely it must NEVER

  * submit a job application,
  * send, reply to, or forward an email,
  * send a WhatsApp message,
  * delete or archive any message,
  * place, cancel or modify a trade.

Rather than trusting each adapter to remember that, the rule is enforced
mechanically in two places:

  `http_get()`  - the only HTTP helper the suite exposes. There is deliberately
                  no post()/put()/delete() anywhere in the suite, and this
                  function refuses any method other than GET/HEAD, so a future
                  edit cannot quietly gain write access by passing a `method=`.

  `guard()`     - a name-based veto for non-HTTP side effects (Outlook COM calls,
                  app automation). Adapters declare what they are about to do;
                  anything matching a forbidden intent raises BlockedAction
                  before the call is made, not after.

Every refusal is recorded in an in-memory audit trail that the routine prints in
its report, so a blocked attempt is visible to the user instead of silent.
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any

# Methods that cannot change state on a remote system. Anything else is refused.
_SAFE_METHODS = ("GET", "HEAD")

# Verb/noun pairs that describe the forbidden actions. Matched against the
# free-text `intent` an adapter passes to guard(). Kept as regexes because the
# point is to catch near-misses ("submit application", "apply to job",
# "send mail", "place order") rather than one exact spelling.
_FORBIDDEN = (
    (re.compile(r"\b(submit|apply|application)\w*\b.*\b(job|application|role|vacanc)", re.I),
     "submitting a job application"),
    (re.compile(r"\bapply\b.*\bto\b", re.I), "submitting a job application"),
    (re.compile(r"\b(send|reply|forward|compose)\w*\b.*\b(mail|email|message|whatsapp|sms)", re.I),
     "sending a message"),
    (re.compile(r"\b(mail|email|message|whatsapp)\w*\b.*\b(send|reply|forward)", re.I),
     "sending a message"),
    (re.compile(r"\b(delete|remove|purge|archive|trash|erase)\w*\b.*\b(mail|email|message|chat|thread|conversation)", re.I),
     "deleting a message"),
    (re.compile(r"\b(buy|sell|trade|order|execute|place|close|short|long)\w*\b.*\b(trade|order|position|stock|share|crypto|asset)", re.I),
     "executing a trade"),
    (re.compile(r"\b(trade|order|position)\w*\b.*\b(place|execute|submit|cancel|modify)", re.I),
     "executing a trade"),
    # "cancel the pending order" / "modify the open position" — the verb leads
    # and the noun trails, which the pair above (noun-then-verb) misses.
    (re.compile(r"\b(cancel|modify|amend|close)\w*\b.*\b(order|trade|position)", re.I),
     "executing a trade"),
)

# Read-only intents that would otherwise trip the broad patterns above —
# "read unread mail" contains no forbidden verb, but "mark as read" and
# "search sent mail" look close enough to warrant an explicit allowance.
_ALLOWED_EXCEPTIONS = (
    re.compile(r"^read\b", re.I),
    re.compile(r"^list\b", re.I),
    re.compile(r"^count\b", re.I),
    re.compile(r"^summar(y|ise|ize)\b", re.I),
    re.compile(r"^search\b", re.I),
    re.compile(r"^fetch\b", re.I),
    re.compile(r"^open\b", re.I),
    re.compile(r"^queue\b", re.I),
)


class BlockedAction(RuntimeError):
    """Raised when something in the suite tries to perform a forbidden action."""


@dataclass
class AuditEntry:
    when: float
    intent: str
    allowed: bool
    reason: str = ""

    def line(self) -> str:
        stamp = time.strftime("%H:%M:%S", time.localtime(self.when))
        verdict = "allowed" if self.allowed else f"BLOCKED ({self.reason})"
        return f"[{stamp}] {self.intent} -> {verdict}"


@dataclass
class AuditLog:
    entries: list[AuditEntry] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, intent: str, allowed: bool, reason: str = "") -> None:
        with self._lock:
            self.entries.append(AuditEntry(time.time(), intent, allowed, reason))

    @property
    def blocked(self) -> list[AuditEntry]:
        return [e for e in self.entries if not e.allowed]

    def clear(self) -> None:
        with self._lock:
            self.entries.clear()


AUDIT = AuditLog()


def classify(intent: str) -> tuple[bool, str]:
    """Return (allowed, reason). Pure function — no logging, easy to test."""
    text = (intent or "").strip()
    if not text:
        return False, "empty intent"
    for ok in _ALLOWED_EXCEPTIONS:
        if ok.match(text):
            return True, ""
    for pattern, reason in _FORBIDDEN:
        if pattern.search(text):
            return False, reason
    return True, ""


def guard(intent: str) -> None:
    """Veto a non-HTTP side effect by description. Raises BlockedAction."""
    allowed, reason = classify(intent)
    AUDIT.record(intent, allowed, reason)
    if not allowed:
        raise BlockedAction(
            f"Refused: '{intent}' would involve {reason}, which the morning "
            f"routine is permanently forbidden from doing."
        )


def http_get(url: str, *, headers: dict | None = None, params: dict | None = None,
             timeout: float = 8.0, method: str = "GET") -> tuple[int, str]:
    """
    The suite's only network call. Read-only by construction.

    Returns (status_code, body_text). Network failures are raised as OSError so
    callers can fall back; they are not swallowed here, because a silent empty
    result would look identical to "you have no unread mail".
    """
    m = (method or "GET").upper()
    if m not in _SAFE_METHODS:
        AUDIT.record(f"HTTP {m} {url}", False, "non-read-only HTTP method")
        raise BlockedAction(
            f"Refused: HTTP {m} is a state-changing request. This suite is "
            f"read-only and may only issue {' or '.join(_SAFE_METHODS)}."
        )
    AUDIT.record(f"HTTP {m} {url}", True)

    import json as _json
    import urllib.error
    import urllib.parse
    import urllib.request

    if params:
        sep = "&" if urllib.parse.urlparse(url).query else "?"
        url = f"{url}{sep}{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url, method=m, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        # An HTTP error is still a reply; let the caller decide what it means.
        return e.code, e.read().decode("utf-8", "replace") if e.fp else ""
    except Exception as e:  # URLError, timeout, DNS, refused connection
        raise OSError(str(e)) from e


def http_get_json(url: str, **kw) -> Any:
    import json as _json
    status, body = http_get(url, **kw)
    if status >= 400:
        raise OSError(f"HTTP {status} from {url}")
    try:
        return _json.loads(body)
    except Exception as e:
        raise OSError(f"Bad JSON from {url}: {e}") from e
