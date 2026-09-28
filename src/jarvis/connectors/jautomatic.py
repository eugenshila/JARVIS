"""Connector for eugenshila/JAUTOMATIC-JOB-SEARCH.

JAUTOMATIC remains the specialist job-search engine.  JARVIS reads its local
workspace and can launch it, then turns the data into daily ADHD-friendly career
plans.  No PostgreSQL server is required: JAUTOMATIC uses local SQLite and JSON.
"""

from __future__ import annotations

import json
import os
import platform
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


ACTIVE_STATUSES = {"discovered", "proposed", "shortlisted", "materials_ready", "sent", "interview", "offer"}
CLOSED_STATUSES = {"rejected", "archived"}


def default_data_dir() -> Path:
    """Return JAUTOMATIC's default workspace path for this OS."""
    if os.environ.get("JAUTOMATIC_DATA_DIR"):
        return Path(os.environ["JAUTOMATIC_DATA_DIR"]).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "JAUTOMATIC"
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base).expanduser() / "jautomatic-job-search"


def _repo_candidates() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("JAUTOMATIC_REPO", "JAUTOMATIC_SOURCE", "JAUTOMATIC_HOME"):
        if os.environ.get(env_name):
            candidates.append(Path(os.environ[env_name]).expanduser())
    cwd = Path.cwd()
    home = Path.home()
    candidates.extend([
        cwd.parent / "JAUTOMATIC-JOB-SEARCH",
        home / "JAUTOMATIC-JOB-SEARCH",
        home.parent / "JAUTOMATIC-JOB-SEARCH",
        Path("/home/user/JAUTOMATIC-JOB-SEARCH"),
    ])
    return candidates


def find_app() -> dict[str, Any] | None:
    """Find a launchable JAUTOMATIC app or source checkout."""
    if os.environ.get("JAUTOMATIC_APP_PATH"):
        path = Path(os.environ["JAUTOMATIC_APP_PATH"]).expanduser()
        if path.exists():
            return {"kind": "executable", "path": str(path), "label": "JAUTOMATIC executable"}

    if os.name == "nt":
        candidates = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "JAUTOMATIC" / "jautomatic.exe",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "JAUTOMATIC" / "jautomatic.exe",
            Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "JAUTOMATIC" / "jautomatic.exe",
        ]
        for path in candidates:
            if path.exists():
                return {"kind": "executable", "path": str(path), "label": "JAUTOMATIC installed app"}

    for repo in _repo_candidates():
        main_py = repo / "main.py"
        package = repo / "jautomatic"
        if main_py.exists() and package.exists():
            return {"kind": "source", "path": str(main_py), "repo": str(repo), "label": "JAUTOMATIC source checkout"}
    return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    if not text:
        return None
    for splitter in ("T", " "):
        head = text.split(splitter, 1)[0]
        try:
            return date.fromisoformat(head[:10])
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


@dataclass
class JAutomaticConnector:
    data_dir: Path | None = None

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir).expanduser() if self.data_dir else default_data_dir()
        self.db_path = self.data_dir / "jautomatic.sqlite3"
        self.profile_path = self.data_dir / "profile.json"
        self.settings_path = self.data_dir / "settings.json"
        self.documents_dir = self.data_dir / "documents"
        self.exports_dir = self.data_dir / "exports"
        self.app = find_app()

    @property
    def workspace_exists(self) -> bool:
        return bool(self.data_dir and self.data_dir.exists())

    @property
    def database_exists(self) -> bool:
        return self.db_path.exists()

    @property
    def profile_exists(self) -> bool:
        return self.profile_path.exists()

    def load_profile(self) -> dict[str, Any]:
        if not self.profile_path.exists():
            return {}
        try:
            data = json.loads(self.profile_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def profile_summary(self) -> dict[str, Any]:
        profile = self.load_profile()
        extra = profile.get("extra") if isinstance(profile.get("extra"), dict) else {}
        education_progress = extra.get("education_progress") if isinstance(extra.get("education_progress"), dict) else {}
        records = [r for r in education_progress.values() if isinstance(r, dict)]
        return {
            "name": profile.get("name") or profile.get("full_name") or "",
            "headline": profile.get("headline") or "",
            "desired_titles": profile.get("desired_titles") or [],
            "target_locations": profile.get("target_locations") or profile.get("locations") or [],
            "skills": profile.get("skills") or [],
            "education_progress": {
                "total": len(records),
                "in_progress": sum(1 for item in records if item.get("status") == "In progress"),
                "completed": sum(1 for item in records if item.get("status") == "Completed"),
            },
        }

    def _connect_readonly(self) -> sqlite3.Connection | None:
        if not self.db_path.exists():
            return None
        try:
            uri = f"file:{self.db_path.resolve().as_posix()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=3)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error:
            return None

    def stats(self) -> dict[str, Any]:
        base = {
            "workspace": str(self.data_dir),
            "workspace_exists": self.workspace_exists,
            "database_exists": self.database_exists,
            "profile_exists": self.profile_exists,
            "app": self.app,
            "postgres_required": False,
            "storage": "SQLite + JSON files",
            "jobs": 0,
            "applications": 0,
            "by_status": {},
            "sent": 0,
            "interviews": 0,
            "offers": 0,
            "materials_ready": 0,
            "follow_ups_due": 0,
            "top_matches": [],
            "followups": [],
            "training": self.profile_summary().get("education_progress", {"total": 0, "in_progress": 0, "completed": 0}),
            "profile": self.profile_summary(),
        }
        conn = self._connect_readonly()
        if conn is None:
            return base
        try:
            jobs_row = conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()
            base["jobs"] = int(jobs_row["c"] if jobs_row else 0)

            status_rows = conn.execute("SELECT status, COUNT(*) AS c FROM applications GROUP BY status").fetchall()
            by_status = {str(row["status"] or "discovered"): int(row["c"] or 0) for row in status_rows}
            base["by_status"] = by_status
            base["applications"] = sum(by_status.values())
            base["sent"] = int(conn.execute("SELECT COUNT(*) AS c FROM applications WHERE sent_at <> ''").fetchone()["c"])
            base["interviews"] = by_status.get("interview", 0)
            base["offers"] = by_status.get("offer", 0)
            base["materials_ready"] = by_status.get("materials_ready", 0)

            today = date.today()
            followups: list[dict[str, Any]] = []
            follow_rows = conn.execute(
                """
                SELECT a.application_id, a.status, a.follow_up_at, a.sent_at, a.match_score,
                       j.title, j.company, j.url
                FROM applications a JOIN jobs j ON j.job_id = a.job_id
                WHERE a.follow_up_at <> '' AND lower(a.status) NOT IN ('rejected','archived','offer')
                ORDER BY a.follow_up_at ASC
                LIMIT 25
                """
            ).fetchall()
            for row in follow_rows:
                due_date = _parse_date(row["follow_up_at"])
                due = bool(due_date and due_date <= today)
                item = {
                    "application_id": row["application_id"],
                    "company": row["company"],
                    "title": row["title"],
                    "follow_up_at": row["follow_up_at"],
                    "status": row["status"],
                    "score": row["match_score"],
                    "url": row["url"],
                    "due": due,
                }
                if due:
                    followups.append(item)
            base["followups"] = followups
            base["follow_ups_due"] = len(followups)

            top_rows = conn.execute(
                """
                SELECT a.application_id, a.status, a.match_score,
                       j.title, j.company, j.location, j.remote, j.url
                FROM applications a JOIN jobs j ON j.job_id = a.job_id
                WHERE lower(a.status) NOT IN ('rejected','archived')
                ORDER BY a.match_score DESC, a.updated_at DESC
                LIMIT 8
                """
            ).fetchall()
            base["top_matches"] = [
                {
                    "application_id": row["application_id"],
                    "company": row["company"],
                    "title": row["title"],
                    "location": row["location"],
                    "remote": bool(row["remote"]),
                    "status": row["status"],
                    "score": row["match_score"],
                    "url": row["url"],
                }
                for row in top_rows
            ]
            return base
        except sqlite3.Error as exc:
            base["error"] = str(exc)
            return base
        finally:
            conn.close()

    def launch(self, confirm: bool = False) -> str:
        if not confirm:
            return "Confirm required before opening JAUTOMATIC. Run with confirm=true / --yes."
        if not self.app:
            return self.setup_instructions()
        kind = self.app.get("kind")
        path = Path(str(self.app.get("path", ""))).expanduser()
        if not path.exists():
            return f"JAUTOMATIC path no longer exists: {path}"
        try:
            if kind == "source":
                subprocess.Popen([sys.executable, str(path), "--data-dir", str(self.data_dir)], cwd=str(path.parent), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            else:
                if os.name == "nt":
                    os.startfile(str(path))  # type: ignore[attr-defined]
                else:
                    subprocess.Popen([str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return "Opening JAUTOMATIC JOB SEARCH, Sir."
        except Exception as exc:
            return f"Failed to open JAUTOMATIC: {exc}"

    def setup_instructions(self) -> str:
        return """JAUTOMATIC was not found yet.

Install or clone it, then JARVIS will integrate with its local workspace:

  git clone https://github.com/eugenshila/JAUTOMATIC-JOB-SEARCH
  cd JAUTOMATIC-JOB-SEARCH
  python -m venv .venv
  .venv/bin/pip install -r requirements.txt
  .venv/bin/python main.py

Optional environment variables:
  JAUTOMATIC_DATA_DIR  = path to workspace containing jautomatic.sqlite3
  JAUTOMATIC_REPO      = path to source checkout
  JAUTOMATIC_APP_PATH  = path to installed jautomatic.exe

Storage note: no PostgreSQL server is required. JAUTOMATIC uses SQLite + JSON files locally.
"""
