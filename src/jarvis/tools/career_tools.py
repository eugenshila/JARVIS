"""Career OS tools powered by JAUTOMATIC JOB SEARCH."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis.connectors.jautomatic import JAutomaticConnector
from jarvis.core.config import get_home
from jarvis.tools.base import BaseTool, ToolSpec


CAREER_MODES = {"seeking", "employed", "open_to_better", "paused"}


def _career_path() -> Path:
    home = get_home()
    home.mkdir(parents=True, exist_ok=True)
    return home / "career.json"


def _load_career_config() -> dict[str, Any]:
    path = _career_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"mode": "seeking", "updated": datetime.now().isoformat()}


def _save_career_config(data: dict[str, Any]) -> None:
    data["updated"] = datetime.now().isoformat()
    _career_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


class CareerTool(BaseTool):
    spec = ToolSpec(
        name="career_os",
        description=(
            "Career OS powered by JAUTOMATIC: job-search status, daily schedule, follow-ups, "
            "training progress, employed-mode growth plan, and safe launch. No PostgreSQL needed."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "today", "mode", "followups", "training", "open", "paths", "postgres"],
                    "description": "Career action",
                    "default": "status",
                },
                "mode": {
                    "type": "string",
                    "enum": ["seeking", "employed", "open_to_better", "paused"],
                    "description": "Career mode when action=mode",
                    "default": "seeking",
                },
                "confirm": {"type": "boolean", "description": "Confirm opening JAUTOMATIC", "default": False},
            },
            "required": [],
        },
        requires_approval=True,
    )

    def run(self, action: str = "status", mode: str = "seeking", confirm: bool = False, **kwargs: Any) -> str:
        action = (action or "status").lower()
        connector = JAutomaticConnector()
        if action == "today":
            return self._today(connector)
        if action == "mode":
            return self._set_mode(mode)
        if action == "followups":
            return self._followups(connector)
        if action == "training":
            return self._training(connector)
        if action == "open":
            return connector.launch(confirm=confirm)
        if action == "paths":
            return self._paths(connector)
        if action == "postgres":
            return self._postgres_answer(connector)
        return self._status(connector)

    def _mode(self) -> str:
        mode = str(_load_career_config().get("mode", "seeking"))
        return mode if mode in CAREER_MODES else "seeking"

    def _set_mode(self, mode: str) -> str:
        mode = (mode or "seeking").lower()
        if mode not in CAREER_MODES:
            return f"Unknown career mode '{mode}'. Use: seeking, employed, open_to_better, paused."
        config = _load_career_config()
        config["mode"] = mode
        _save_career_config(config)
        descriptions = {
            "seeking": "Actively job searching: applications, free training, follow-ups, interview prep.",
            "employed": "Employed and growing: achievements, upskilling, performance evidence, light CV maintenance.",
            "open_to_better": "Employed/open: current job first, passive better-opportunity monitoring weekly.",
            "paused": "Paused: no aggressive search, keep profile warm and training gentle.",
        }
        return f"Career mode set to **{mode}**. {descriptions[mode]}"

    def _status(self, connector: JAutomaticConnector) -> str:
        stats = connector.stats()
        mode = self._mode()
        profile = stats.get("profile", {})
        lines = [
            "💼 **Career OS — JAUTOMATIC Integration**",
            "",
            f"Mode: **{mode}**",
            f"Storage: {stats.get('storage')} — PostgreSQL required: **No**",
            f"Workspace: `{stats.get('workspace')}`",
            f"JAUTOMATIC app: {stats.get('app', {}).get('label') if stats.get('app') else 'not found yet'}",
            "",
            f"Profile: {profile.get('name') or 'not set'} — {profile.get('headline') or 'no headline yet'}",
        ]
        desired = profile.get("desired_titles") or []
        if desired:
            lines.append(f"Target roles: {', '.join(map(str, desired[:5]))}")
        lines.extend([
            "",
            "**Pipeline:**",
            f"  • Jobs discovered: {stats.get('jobs', 0)}",
            f"  • Applications tracked: {stats.get('applications', 0)}",
            f"  • Sent: {stats.get('sent', 0)}",
            f"  • Materials ready: {stats.get('materials_ready', 0)}",
            f"  • Interviews: {stats.get('interviews', 0)}",
            f"  • Offers: {stats.get('offers', 0)}",
            f"  • Follow-ups due: {stats.get('follow_ups_due', 0)}",
        ])
        training = stats.get("training", {})
        lines.extend([
            "",
            "**Training:**",
            f"  • In progress: {training.get('in_progress', 0)}",
            f"  • Completed: {training.get('completed', 0)}",
        ])
        top = stats.get("top_matches") or []
        if top:
            lines.extend(["", "**Top active matches:**"])
            for item in top[:5]:
                lines.append(f"  • {item.get('score', 0)}% — {item.get('title')} @ {item.get('company')} ({item.get('status')})")
        elif not stats.get("database_exists"):
            lines.extend(["", "JAUTOMATIC database not found yet. Open JAUTOMATIC once or set `JAUTOMATIC_DATA_DIR`."])
        lines.extend(["", "Next: `jarvis career today` for a 3-task schedule."])
        return "\n".join(lines)

    def _today(self, connector: JAutomaticConnector) -> str:
        stats = connector.stats()
        mode = self._mode()
        tasks: list[str] = []
        if mode == "seeking":
            if stats.get("follow_ups_due", 0):
                tasks.append(f"Send {min(2, int(stats['follow_ups_due']))} polite follow-up(s) from JAUTOMATIC.")
            if stats.get("materials_ready", 0):
                tasks.append("Review and submit 1-2 applications whose materials are ready.")
            if not tasks and stats.get("top_matches"):
                tasks.append("Pick the highest JAUTOMATIC match and prepare/apply after review.")
            tasks.append("Complete one free training module tied to your target role.")
            tasks.append("Search/import fresh roles for 30 minutes, then stop — no endless scrolling.")
            tasks.append("Update one career asset: JAUTOMATIC profile, CV bullet, LinkedIn line, or portfolio note.")
        elif mode == "employed":
            tasks.extend([
                "Log one work achievement with numbers/context for future CV and performance review.",
                "Do one 30-minute upskilling block from JAUTOMATIC Education.",
                "Keep job search passive: review opportunities only if already scheduled.",
            ])
        elif mode == "open_to_better":
            tasks.extend([
                "Protect current-job performance first: choose today’s work MIT.",
                "Spend 20 minutes reviewing strong JAUTOMATIC matches only — no mass applying.",
                "Log one achievement or skill learned so your CV stays warm.",
            ])
        else:
            tasks.extend([
                "Keep career system warm: update one profile detail or skill.",
                "Do one light training block if energy allows.",
                "No job-search pressure today unless there is an urgent follow-up.",
            ])

        tasks = tasks[:3]
        lines = [
            f"📅 **Career Plan for Today — Mode: {mode}**",
            "",
            "ADHD rule: maximum 3 career MITs. If you do one, today still counts.",
            "",
        ]
        for idx, task in enumerate(tasks, 1):
            lines.append(f"{idx}. {task}")
        lines.extend([
            "",
            "Suggested blocks:",
            "  • 25 min focus → 5 min break",
            "  • 10 min admin cleanup",
            "  • Stop after the planned block; JARVIS is allergic to doom-scrolling, Sir.",
        ])
        return "\n".join(lines)

    def _followups(self, connector: JAutomaticConnector) -> str:
        stats = connector.stats()
        items = stats.get("followups") or []
        if not items:
            return "No JAUTOMATIC follow-ups are due today, Sir. That is suspiciously civilized."
        lines = [f"📨 **JAUTOMATIC Follow-ups Due — {len(items)}**", ""]
        for item in items[:10]:
            lines.append(f"  • {item.get('follow_up_at')} — {item.get('title')} @ {item.get('company')} ({item.get('status')}, {item.get('score')}%)")
        lines.append("\nOpen JAUTOMATIC to draft/review follow-up emails before sending.")
        return "\n".join(lines)

    def _training(self, connector: JAutomaticConnector) -> str:
        stats = connector.stats()
        training = stats.get("training", {})
        lines = [
            "🎓 **Career Training — JAUTOMATIC Education**",
            "",
            f"Tracked courses: {training.get('total', 0)}",
            f"In progress: {training.get('in_progress', 0)}",
            f"Completed: {training.get('completed', 0)}",
            "",
            "Free training sources already fit this workflow:",
            "  • Microsoft Learn",
            "  • IBM SkillsBuild",
            "  • freeCodeCamp",
            "  • Google Digital Garage / Coursera audit",
            "  • Cisco Networking Academy",
            "  • Kaggle Learn",
            "",
            "Today: choose one module linked to a missing skill from your tracked jobs.",
        ]
        return "\n".join(lines)

    def _paths(self, connector: JAutomaticConnector) -> str:
        return "\n".join([
            "**JAUTOMATIC paths**",
            f"Workspace: `{connector.data_dir}`",
            f"Database: `{connector.db_path}` {'✅' if connector.db_path.exists() else '⚠️ missing'}",
            f"Profile: `{connector.profile_path}` {'✅' if connector.profile_path.exists() else '⚠️ missing'}",
            f"Documents: `{connector.documents_dir}`",
            f"Exports: `{connector.exports_dir}`",
            f"App: `{connector.app.get('path') if connector.app else 'not found'}`",
        ])

    def _postgres_answer(self, connector: JAutomaticConnector) -> str:
        return """**No — JARVIS does not need a PostgreSQL server for this integration.**

Current storage:
  • JARVIS: local JSON/TOML files plus optional local memory stores
  • JAUTOMATIC: SQLite database (`jautomatic.sqlite3`) plus JSON profile/settings
  • Calendar/email: OAuth token files or local JSON fallbacks

PostgreSQL would only be useful later if you want multi-user/team access, sync across many machines, a web-hosted dashboard, or very large analytics. For your personal MSI, SQLite/local files are simpler, private, and safer.
"""
