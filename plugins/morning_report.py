"""
Read back the last saved morning report, and the safety ledger with it.

Separate from `morning_routine` on purpose: re-running the routine takes
seconds and hits five external systems, so "what did you say earlier?" should
never trigger it. This plugin only reads files the routine already wrote.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent.parent / "memory"

PLUGIN = {
    "name": "morning_report",
    "description": (
        "Read back today's already-generated morning report, or list recent ones, plus the "
        "pending Applications queue. Trigger phrases: 'what was my morning briefing', "
        "'read back the morning report', 'what jobs did you queue'. Does NOT re-run the "
        "routine — use morning_routine for a fresh run."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "date": {"type": "STRING",
                     "description": "Report date as YYYY-MM-DD. Defaults to today, "
                                    "falling back to the most recent."},
            "section": {"type": "STRING",
                        "description": "'full', 'plan', 'jobs', or 'queue'. Default 'full'."},
        },
        "required": [],
    },
}


def _reports() -> list[Path]:
    return sorted(REPORT_DIR.glob("morning_report_*.md"), reverse=True)


def _extract(text: str, section: str) -> str:
    lines = text.splitlines()
    if section == "plan":
        try:
            start = next(i for i, l in enumerate(lines) if l.startswith("Today's plan"))
        except StopIteration:
            return "No plan section in that report."
        end = next((i for i in range(start + 1, len(lines))
                    if lines[i].startswith("Briefing")), len(lines))
        return "\n".join(lines[start:end]).strip()
    if section == "jobs":
        return "\n".join(l for l in lines
                         if l.startswith("Job Search") or l.strip().startswith("•")
                         or l.startswith("Moved ")).strip() or "No job lines found."
    return text


def run(parameters: dict, player=None, session_memory=None) -> str:
    section = str(parameters.get("section") or "full").lower()

    if section == "queue":
        path = REPORT_DIR / "jautomatic_pending_queue.json"
        if not path.exists():
            return "There is no local pending queue — jobs went straight into JAUTOMATIC."
        try:
            import json
            items = json.loads(path.read_text("utf-8"))
            if not items:
                return "The local pending queue is empty."
            lines = [f"{i.get('score', '?')}%  {i.get('title')} — {i.get('company')} "
                     f"(queued {i.get('queued_at', '?')})" for i in items]
            return (f"{len(items)} job(s) staged for your review, none submitted:\n  "
                    + "\n  ".join(lines))
        except Exception as e:
            return f"Sir, I could not read the pending queue: {e}"

    wanted = str(parameters.get("date") or datetime.now().strftime("%Y-%m-%d"))
    target = REPORT_DIR / f"morning_report_{wanted}.md"
    if not target.exists():
        available = _reports()
        if not available:
            return "I have no saved morning reports yet — ask me to run the morning routine."
        target = available[0]

    try:
        text = target.read_text("utf-8")
    except Exception as e:
        return f"Sir, I could not read {target.name}: {e}"

    out = _extract(text, section)
    if player:
        try:
            for line in out.splitlines():
                player.write_log(line)
        except Exception:
            pass
    return out
