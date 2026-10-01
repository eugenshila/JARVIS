"""
JAUTOMATIC adapter for the morning routine.

Connection model ("open or connect to JAUTOMATIC"):
  1. Try the local HTTP API first — if JAUTOMATIC is already running, we attach
     to the running instance rather than starting a second copy.
  2. If nothing answers, launch the configured executable / URL and poll the
     health endpoint for a few seconds while it boots.
  3. If it still will not answer, fall back to OFFLINE mode, which reads a
     local snapshot file if one exists and otherwise returns a clearly-labelled
     demo dataset. The routine then still produces a plan and says plainly that
     the figures are from a snapshot — that is far more useful at 6am than an
     error, and it is what makes the whole suite testable without the app.

Write access is deliberately asymmetric. Everything this module reads goes
through the read-only helper in _jmorning_safety. The ONE state change it is
permitted to make is moving a job into the Applications *queue* — a staging
list the user reviews and submits by hand. `queue_jobs()` is the only function
here that is not a GET, it can only ever address the queue endpoint, and it
passes through the guard first. Submitting an application is not implemented
anywhere in this suite, so JARVIS cannot do it even by mistake.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from plugins._jmorning_safety import AUDIT, BlockedAction, guard, http_get_json

NAMESPACE = "jautomatic"
DEFAULT_BASE_URL = "http://127.0.0.1:8750"
SNAPSHOT_FILE = Path(__file__).resolve().parent.parent / "memory" / "jautomatic_snapshot.json"


def _cfg(key: str, default=None):
    try:
        from memory.config_manager import get_plugin_setting
        val = get_plugin_setting(NAMESPACE, key, default)
    except Exception:
        val = default
    if val in (None, ""):
        return default
    return val


# ─────────────────────────── data shapes ───────────────────────────

@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str = ""
    score: float = 0.0              # 0-100 match against the saved profile
    skills_required: list[str] = field(default_factory=list)
    url: str = ""
    posted: str = ""

    @classmethod
    def from_api(cls, d: dict) -> "Job":
        score = d.get("score", d.get("match", d.get("match_score", 0)))
        try:
            score = float(score)
        except Exception:
            score = 0.0
        # Tolerate both 0-1 and 0-100 scales; JAUTOMATIC has used both.
        if 0.0 < score <= 1.0:
            score *= 100.0
        skills = d.get("skills_required") or d.get("skills") or d.get("requirements") or []
        if isinstance(skills, str):
            skills = [s.strip() for s in re.split(r"[,;/|]", skills) if s.strip()]
        return cls(
            id=str(d.get("id") or d.get("job_id") or d.get("uid") or ""),
            title=str(d.get("title") or d.get("role") or "Untitled role"),
            company=str(d.get("company") or d.get("employer") or "Unknown"),
            location=str(d.get("location") or d.get("city") or ""),
            score=round(score, 1),
            skills_required=[str(s) for s in skills],
            url=str(d.get("url") or d.get("link") or ""),
            posted=str(d.get("posted") or d.get("date") or ""),
        )


@dataclass
class Course:
    id: str
    title: str
    provider: str = ""
    skills_taught: list[str] = field(default_factory=list)
    duration_minutes: int = 0
    modules: int = 0
    level: str = ""
    url: str = ""

    @classmethod
    def from_api(cls, d: dict) -> "Course":
        mins = d.get("duration_minutes")
        if mins is None:
            hours = d.get("duration_hours") or d.get("hours")
            mins = float(hours) * 60 if hours else _parse_duration(str(d.get("duration") or ""))
        skills = d.get("skills_taught") or d.get("skills") or d.get("covers") or []
        if isinstance(skills, str):
            skills = [s.strip() for s in re.split(r"[,;/|]", skills) if s.strip()]
        return cls(
            id=str(d.get("id") or d.get("course_id") or ""),
            title=str(d.get("title") or d.get("name") or "Untitled course"),
            provider=str(d.get("provider") or d.get("source") or ""),
            skills_taught=[str(s) for s in skills],
            duration_minutes=int(round(float(mins or 0))),
            modules=int(d.get("modules") or d.get("lessons") or 0),
            level=str(d.get("level") or ""),
            url=str(d.get("url") or d.get("link") or ""),
        )


def _parse_duration(text: str) -> float:
    """'6h 30m', '4 hours', '90 min' -> minutes."""
    if not text:
        return 0.0
    total = 0.0
    for value, unit in re.findall(r"(\d+(?:\.\d+)?)\s*([hm])", text.lower()):
        total += float(value) * (60 if unit == "h" else 1)
    if not total:
        m = re.search(r"(\d+(?:\.\d+)?)", text)
        if m:
            total = float(m.group(1)) * 60  # bare number reads as hours
    return total


def format_duration(minutes: float) -> str:
    minutes = int(round(minutes))
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


# ─────────────────────────── the client ───────────────────────────

class JautomaticClient:
    def __init__(self, logger=None):
        self.base_url = str(_cfg("base_url", DEFAULT_BASE_URL)).rstrip("/")
        self.token = _cfg("api_token", "") or ""
        self.app_path = _cfg("app_path", "") or ""
        self.online = False
        self.mode = "offline"
        self._log = logger or (lambda _m: None)
        self._snapshot: dict | None = None

    # -- transport ------------------------------------------------
    @property
    def _headers(self) -> dict:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, path: str, params: dict | None = None):
        return http_get_json(f"{self.base_url}{path}", headers=self._headers,
                             params=params, timeout=float(_cfg("timeout", 8)))

    def ping(self) -> bool:
        for path in ("/api/health", "/health", "/api/status"):
            try:
                self._get(path)
                return True
            except BlockedAction:
                raise
            except Exception:
                continue
        return False

    def connect(self, launch: bool = True) -> str:
        """Attach to a running JAUTOMATIC, else start it, else go offline."""
        guard("open or connect to JAUTOMATIC")
        if self.ping():
            self.online, self.mode = True, "attached"
            self._log("JAUTOMATIC: attached to the running instance.")
            return self.mode
        if launch and self.app_path:
            if self._launch():
                deadline = time.time() + float(_cfg("launch_timeout", 20))
                while time.time() < deadline:
                    if self.ping():
                        self.online, self.mode = True, "launched"
                        self._log("JAUTOMATIC: launched and connected.")
                        return self.mode
                    time.sleep(1.0)
        self.online, self.mode = False, "offline"
        self._log("JAUTOMATIC: unreachable — using the local snapshot.")
        return self.mode

    def _launch(self) -> bool:
        target = self.app_path
        try:
            if target.startswith(("http://", "https://")):
                import webbrowser
                webbrowser.open(target)
                return True
            exe = shutil.which(target) or target
            if not Path(exe).exists():
                self._log(f"JAUTOMATIC: app_path '{target}' not found.")
                return False
            kw = {}
            if os.name == "nt":
                kw["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0)
            else:
                kw["start_new_session"] = True
            subprocess.Popen([exe], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, **kw)
            return True
        except Exception as e:
            self._log(f"JAUTOMATIC: could not launch — {e}")
            return False

    # -- snapshot fallback ---------------------------------------
    def _snap(self) -> dict:
        if self._snapshot is None:
            try:
                self._snapshot = json.loads(SNAPSHOT_FILE.read_text("utf-8"))
            except Exception:
                self._snapshot = _DEMO_SNAPSHOT
        return self._snapshot

    # -- reads ----------------------------------------------------
    def saved_profile(self) -> dict:
        guard("read the saved job-search profile from JAUTOMATIC")
        if self.online:
            for path in ("/api/profile/saved", "/api/profile", "/api/user/profile"):
                try:
                    return self._get(path) or {}
                except Exception:
                    continue
        return self._snap().get("profile", {})

    def job_search(self, profile: dict | None = None) -> list[Job]:
        """Run Job Search with the saved profile. Read-only."""
        guard("search jobs in JAUTOMATIC using the saved profile")
        raw: list = []
        if self.online:
            params = {"profile": profile.get("id", "saved")} if profile else {"profile": "saved"}
            for path in ("/api/jobs/search", "/api/job-search", "/api/jobs"):
                try:
                    data = self._get(path, params=params)
                    raw = data.get("jobs", data.get("results", [])) if isinstance(data, dict) else (data or [])
                    if raw:
                        break
                except Exception:
                    continue
        if not raw:
            raw = self._snap().get("jobs", [])
        jobs = [Job.from_api(d) for d in raw if isinstance(d, dict)]
        jobs.sort(key=lambda j: j.score, reverse=True)
        return jobs

    def courses(self) -> list[Course]:
        guard("read the Education catalogue from JAUTOMATIC")
        raw: list = []
        if self.online:
            for path in ("/api/education/courses", "/api/education", "/api/courses"):
                try:
                    data = self._get(path)
                    raw = data.get("courses", data.get("results", [])) if isinstance(data, dict) else (data or [])
                    if raw:
                        break
                except Exception:
                    continue
        if not raw:
            raw = self._snap().get("courses", [])
        return [Course.from_api(d) for d in raw if isinstance(d, dict)]

    def summary(self) -> dict:
        guard("read the JAUTOMATIC dashboard summary")
        if self.online:
            for path in ("/api/summary", "/api/dashboard"):
                try:
                    return self._get(path) or {}
                except Exception:
                    continue
        return self._snap().get("summary", {})

    # -- the one permitted state change ---------------------------
    def queue_jobs(self, jobs: list[Job]) -> dict:
        """
        Move jobs into the Applications QUEUE — a review list, not a submission.

        This is the suite's only non-GET call. It is hard-wired to the queue
        endpoint: no caller supplies a path, so it cannot be repurposed into an
        'apply' or 'submit' request. When JAUTOMATIC is unreachable the queue is
        written to a local file instead, so nothing is lost.
        """
        guard("queue jobs into the JAUTOMATIC Applications review list")
        ids = [j.id for j in jobs]
        if not ids:
            return {"queued": 0, "ids": [], "where": "nothing to queue"}

        if self.online:
            try:
                import urllib.request
                body = json.dumps({"job_ids": ids, "stage": "queued",
                                   "submit": False}).encode()
                req = urllib.request.Request(
                    f"{self.base_url}/api/applications/queue", data=body, method="POST",
                    headers={**self._headers, "Content-Type": "application/json"})
                AUDIT.record("POST /api/applications/queue (staging only, submit=false)", True)
                with urllib.request.urlopen(req, timeout=float(_cfg("timeout", 8))) as r:
                    payload = json.loads(r.read().decode("utf-8", "replace") or "{}")
                return {"queued": payload.get("queued", len(ids)), "ids": ids,
                        "where": "JAUTOMATIC Applications queue"}
            except Exception as e:
                self._log(f"JAUTOMATIC: queue call failed ({e}); writing locally.")

        local = SNAPSHOT_FILE.parent / "jautomatic_pending_queue.json"
        try:
            existing = json.loads(local.read_text("utf-8")) if local.exists() else []
        except Exception:
            existing = []
        seen = {e.get("id") for e in existing if isinstance(e, dict)}
        for j in jobs:
            if j.id not in seen:
                existing.append({"id": j.id, "title": j.title, "company": j.company,
                                 "score": j.score, "stage": "queued",
                                 "queued_at": time.strftime("%Y-%m-%d %H:%M")})
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(json.dumps(existing, indent=2), "utf-8")
        return {"queued": len(ids), "ids": ids,
                "where": f"local pending queue ({local.name}) — sync when JAUTOMATIC is up"}


# ─────────────────────────── selection logic ───────────────────────────

def filter_by_score(jobs: list[Job], threshold: float = 40.0) -> list[Job]:
    """Jobs scoring at or above the threshold. 40% means 40 included."""
    return [j for j in jobs if j.score >= threshold]


_STOP = {"and", "or", "the", "with", "for", "of", "in", "to", "a", "an", "experience"}


def _norm(skill: str) -> str:
    return re.sub(r"[^a-z0-9+#. ]", " ", skill.lower()).strip()


def skill_gaps(jobs: list[Job], profile: dict) -> list[tuple[str, int]]:
    """
    Skills the shortlisted jobs demand that the profile does not list, ordered
    by how many of those jobs want them. Frequency matters more than novelty:
    the skill blocking five of today's roles is worth more than an exotic one
    blocking a single role.
    """
    have = {_norm(s) for s in (profile.get("skills") or [])}
    have |= {w for s in have for w in s.split() if w and w not in _STOP}
    counts: dict[str, int] = {}
    for job in jobs:
        for raw in set(_norm(s) for s in job.skills_required):
            if not raw or raw in _STOP:
                continue
            if raw in have or any(raw == h or raw in h.split() for h in have):
                continue
            counts[raw] = counts.get(raw, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def choose_course(courses: list[Course], gaps: list[tuple[str, int]]) -> tuple[Course | None, dict]:
    """
    Pick exactly ONE course: the one covering the most demand-weighted gap.

    Ties break toward the shorter course, because a course that finishes is
    worth more than a better one that stalls — which is the same reason the
    plan below is built out of short blocks.
    """
    if not courses:
        return None, {}
    gap_weight = {g: w for g, w in gaps}
    scored = []
    for c in courses:
        taught = {_norm(s) for s in c.skills_taught}
        covered = {g: w for g, w in gap_weight.items()
                   if g in taught or any(g in t or t in g for t in taught if t)}
        scored.append((sum(covered.values()), len(covered), -c.duration_minutes, c, covered))
    scored.sort(key=lambda t: (-t[0], -t[1], -t[2]))
    best = scored[0]
    if best[0] == 0:
        # Nothing matches a gap — fall back to the shortest course so the
        # routine still has a concrete, finishable recommendation.
        shortest = min(courses, key=lambda c: c.duration_minutes or 10**9)
        return shortest, {}
    return best[3], best[4]


# A clearly-labelled dataset so the routine (and its tests) work before
# JAUTOMATIC is configured. Replaced the moment the API answers.
_DEMO_SNAPSHOT = {
    "profile": {
        "id": "saved",
        "name": "Saved profile",
        "titles": ["Automation Engineer", "Python Developer", "Solutions Engineer"],
        "location": "Nairobi / Remote",
        "skills": ["Python", "REST APIs", "Automation", "Git", "SQL", "Linux"],
    },
    "jobs": [
        {"id": "J-1001", "title": "Automation Engineer", "company": "Nuvia Systems",
         "location": "Remote", "score": 86, "posted": "2026-09-30",
         "skills": ["Python", "Docker", "CI/CD", "REST APIs", "Kubernetes"]},
        {"id": "J-1002", "title": "Backend Developer (Python)", "company": "Tala",
         "location": "Nairobi", "score": 71, "posted": "2026-09-30",
         "skills": ["Python", "PostgreSQL", "Docker", "AWS"]},
        {"id": "J-1003", "title": "Integrations Engineer", "company": "Cellulant",
         "location": "Nairobi", "score": 58, "posted": "2026-09-29",
         "skills": ["REST APIs", "Docker", "Kafka", "SQL"]},
        {"id": "J-1004", "title": "Data Engineer", "company": "Kyosk",
         "location": "Remote", "score": 44, "posted": "2026-09-29",
         "skills": ["Python", "SQL", "Airflow", "AWS", "Docker"]},
        {"id": "J-1005", "title": "Junior DevOps", "company": "Twiga",
         "location": "Nairobi", "score": 31, "posted": "2026-09-28",
         "skills": ["Linux", "Terraform", "Kubernetes"]},
        {"id": "J-1006", "title": "Salesforce Admin", "company": "Britam",
         "location": "Nairobi", "score": 12, "posted": "2026-09-27",
         "skills": ["Salesforce", "Apex"]},
    ],
    "courses": [
        {"id": "C-01", "title": "Docker and Kubernetes for Engineers", "provider": "JAUTOMATIC Education",
         "skills": ["Docker", "Kubernetes", "CI/CD"], "duration_minutes": 420,
         "modules": 7, "level": "Intermediate"},
        {"id": "C-02", "title": "AWS Fundamentals", "provider": "JAUTOMATIC Education",
         "skills": ["AWS", "Cloud"], "duration_minutes": 300, "modules": 5, "level": "Beginner"},
        {"id": "C-03", "title": "Airflow Pipelines in Practice", "provider": "JAUTOMATIC Education",
         "skills": ["Airflow", "Python"], "duration_minutes": 240, "modules": 4, "level": "Intermediate"},
    ],
    "summary": {"active_applications": 7, "interviews": 1, "queued": 0,
                "tasks_due_today": 3, "notes": "Snapshot data — JAUTOMATIC not connected."},
}
