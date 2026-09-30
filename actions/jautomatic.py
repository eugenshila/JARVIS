"""JARVIS bridge for JAUTOMATIC JOB SEARCH.

The bridge uses JAUTOMATIC's headless service layer for reliable data actions and,
on Windows, can also focus the desktop app and select one of its navigation tabs.
Set ``JAUTOMATIC_PATH`` to the JAUTOMATIC source checkout when it is not next to
JARVIS.  The installed desktop executable and the source bridge share the normal
JAUTOMATIC workspace under ``%APPDATA%\\JAUTOMATIC``.
"""
from __future__ import annotations

import ast
import importlib
import json
import os
import subprocess
import sys
import time
import webbrowser
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any, Iterator


_TAB_ALIASES = {
    "application": "applications",
    "application queue": "applications",
    "courses": "education",
    "jobs": "search",
    "job": "search",
    "job search": "search",
    "analytics": "insights",
}
_TAB_LABELS = {
    "dashboard": "Dashboard",
    "profile": "Profile",
    "search": "Job search",
    "tasks": "Tasks",
    "education": "Education",
    "applications": "Applications",
    "sent": "Sent",
    "archive": "Archive",
    "insights": "Insights",
    "settings": "Settings",
}


def _candidate_roots() -> list[Path]:
    configured = os.environ.get("JAUTOMATIC_PATH", "").strip()
    here = Path(__file__).resolve().parents[1]
    roots = [Path(configured).expanduser()] if configured else []
    roots += [
        here.parent / "JAUTOMATIC-JOB-SEARCH",
        Path.home() / "JAUTOMATIC-JOB-SEARCH",
        Path.home() / "Documents" / "JAUTOMATIC-JOB-SEARCH",
        Path.home() / "Documents" / "GitHub" / "JAUTOMATIC-JOB-SEARCH",
    ]
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _source_root() -> Path | None:
    try:
        package = importlib.import_module("jautomatic")
        package_file = Path(str(package.__file__)).resolve()
        if package_file.parent.name == "jautomatic":
            return package_file.parent.parent
    except (ImportError, AttributeError, TypeError):
        pass
    for root in _candidate_roots():
        if (root / "jautomatic" / "models.py").is_file():
            return root.resolve()
    return None


def _load_api():
    try:
        from jautomatic.models import Workspace
        from jautomatic.services.application_pipeline import ApplicationPipeline
        return Workspace, ApplicationPipeline
    except ImportError:
        pass

    root = _source_root()
    if root is not None:
        value = str(root)
        if value not in sys.path:
            sys.path.insert(0, value)
        from jautomatic.models import Workspace
        from jautomatic.services.application_pipeline import ApplicationPipeline
        return Workspace, ApplicationPipeline
    raise RuntimeError(
        "JAUTOMATIC source was not found. Clone eugenshila/JAUTOMATIC-JOB-SEARCH "
        "next to JARVIS or set JAUTOMATIC_PATH to its repository folder. The "
        "installed desktop executable alone does not expose the service bridge."
    )


@contextmanager
def _pipeline(data_dir: str | None = None) -> Iterator[tuple[Any, Any]]:
    Workspace, ApplicationPipeline = _load_api()
    workspace = Workspace(data_dir or None)
    try:
        yield workspace, ApplicationPipeline(workspace, workspace.load_settings())
    finally:
        workspace.close()


def _json(value: Any) -> str:
    if is_dataclass(value):
        value = asdict(value)
    return json.dumps(value, ensure_ascii=False, default=str, indent=2)


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalise_tab(value: Any) -> str:
    tab = str(value or "dashboard").lower().strip().replace("_", " ")
    tab = _TAB_ALIASES.get(tab, tab)
    if tab not in _TAB_LABELS:
        raise ValueError(
            "Unknown JAUTOMATIC tab. Use dashboard, profile, search, tasks, "
            "education, applications, sent, archive, insights, or settings."
        )
    return tab


def _row(row: Any) -> dict[str, Any]:
    application = row.application
    job = row.job
    return {
        "application_id": application.application_id,
        "job_id": job.job_id,
        "title": job.title,
        "company": job.company,
        "location": job.display_location,
        "score": row.score,
        "status": application.status,
        "url": job.url,
        "follow_up_at": application.follow_up_at,
        "interview_at": application.interview_at,
        "documents": {
            "cv": application.cv_path,
            "cover_letter": application.cover_letter_path,
            "email": application.email_path,
        },
    }


def _job_payload(workspace: Any, pipeline: Any, profile: Any, job: Any) -> dict[str, Any]:
    from jautomatic.services.application_pipeline import match_job

    match = match_job(profile, job, pipeline.settings)
    application = workspace.application_for_job(job.job_id)
    return {
        "job_id": job.job_id,
        "application_id": application.application_id if application else "",
        "title": job.title,
        "company": job.company,
        "location": job.display_location,
        "score": match.score,
        "status": application.status if application else "not_tracked",
        "salary": job.salary_text,
        "source": job.source,
        "url": job.url,
        "matched_keywords": match.matched_keywords,
        "missing_keywords": match.missing_keywords,
        "reasons": match.reasons,
    }


def _find(pipeline: Any, application_id: str) -> Any:
    application_id = str(application_id or "").strip()
    if not application_id:
        raise ValueError("application_id is required for this action")
    record = pipeline.workspace.get_application(application_id)
    if record is None:
        raise ValueError(f"Application not found: {application_id}")
    return record


def _find_job(workspace: Any, job_id: str) -> Any:
    job_id = str(job_id or "").strip()
    if not job_id:
        raise ValueError("job_id is required for this action")
    job = workspace.get_job(job_id)
    if job is None:
        raise ValueError(f"Job not found: {job_id}")
    return job


def _latest_jobs(workspace: Any) -> list[Any]:
    settings = workspace.load_settings()
    identifiers = getattr(settings, "last_search_job_ids", None)
    if identifiers is None:
        return []
    return [job for job_id in identifiers if (job := workspace.get_job(str(job_id))) is not None]


def _requested_job_ids(parameters: dict) -> list[str]:
    values = parameters.get("job_ids") or []
    if isinstance(values, str):
        values = [part.strip() for part in values.split(",")]
    identifiers = [str(value).strip() for value in values if str(value).strip()]
    one = str(parameters.get("job_id") or "").strip()
    if one and one not in identifiers:
        identifiers.insert(0, one)
    return identifiers


def _select_jobs(workspace: Any, pipeline: Any, profile: Any, parameters: dict,
                 *, allow_latest_default: bool = False) -> list[Any]:
    identifiers = _requested_job_ids(parameters)
    if identifiers:
        return [_find_job(workspace, identifier) for identifier in identifiers]

    application_id = str(parameters.get("application_id") or "").strip()
    if application_id:
        record = _find(pipeline, application_id)
        return [_find_job(workspace, record.job_id)]

    latest = _latest_jobs(workspace)
    query = str(parameters.get("title") or "").strip().lower()
    if query:
        latest = [job for job in latest if query in f"{job.title} {job.company}".lower()]
    if not latest:
        raise ValueError("No saved JAUTOMATIC search results were found. Run a search first.")

    if _as_bool(parameters.get("all_results")):
        return latest
    count = int(parameters.get("count") or 0)
    if count > 0:
        from jautomatic.services.application_pipeline import match_job

        latest.sort(key=lambda job: match_job(profile, job, pipeline.settings).score, reverse=True)
        return latest[:count]
    if allow_latest_default and len(latest) == 1:
        return latest
    raise ValueError(
        "Choose a job_id/job_ids, provide count for the top matches, or set "
        "all_results=true to act on every saved search result."
    )


def _materials_payload(materials: Any) -> dict[str, Any]:
    return {
        "application_id": materials.application.application_id,
        "job_id": materials.job.job_id,
        "title": materials.job.title,
        "company": materials.job.company,
        "documents": [str(path) for path in materials.paths],
    }


def _prepare_jobs(workspace: Any, pipeline: Any, profile: Any, parameters: dict) -> str:
    jobs = _select_jobs(workspace, pipeline, profile, parameters, allow_latest_default=True)
    prepared = []
    for job in jobs:
        application = pipeline.ensure_application(job)
        prepared.append(_materials_payload(pipeline.prepare(application, profile)))
    return _json({"prepared": len(prepared), "applications": prepared})


def _open_url(url: str, label: str) -> str:
    if not str(url or "").strip():
        raise ValueError(f"No URL is stored for {label}.")
    if not webbrowser.open(str(url)):
        raise RuntimeError(f"Windows could not open {label} in the default browser.")
    return f"Opened {label} in the default browser."


def _open_path(path: str, label: str) -> str:
    target = Path(str(path or "")).expanduser()
    if not target.is_file():
        raise ValueError(f"The {label} file does not exist yet. Prepare materials first.")
    if os.name == "nt":
        os.startfile(str(target))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])
    return f"Opened {label}: {target}"


# ---------------------------------------------------------------------------
# Desktop navigation (Windows)
# ---------------------------------------------------------------------------
def _installed_executable() -> Path | None:
    candidates = []
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidates.append(Path(program_files) / "JAUTOMATIC" / "jautomatic.exe")
    root = _source_root()
    if root is not None:
        candidates += [
            root / "dist" / "jautomatic" / "jautomatic.exe",
            root / ".venv" / "Scripts" / "pythonw.exe",
        ]
    return next((path for path in candidates if path.is_file()), None)


def _desktop_window(timeout: float = 0.0):
    if os.name != "nt":
        return None
    from pywinauto import Desktop

    deadline = time.monotonic() + max(0.0, timeout)
    while True:
        for window in Desktop(backend="uia").windows():
            if "jautomatic" in window.window_text().lower():
                return window
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.25)


def _launch_desktop() -> None:
    executable = _installed_executable()
    if executable is None:
        raise RuntimeError(
            "JAUTOMATIC desktop is not running and no installed executable or source "
            "virtual environment was found. Open JAUTOMATIC once, then repeat the command."
        )
    root = _source_root()
    if executable.name.lower() == "pythonw.exe":
        if root is None:
            raise RuntimeError("JAUTOMATIC source folder was not found.")
        command = [str(executable), str(root / "main.py")]
        cwd = root
    else:
        command = [str(executable)]
        cwd = executable.parent
    subprocess.Popen(command, cwd=str(cwd), close_fds=True)


def _navigate_desktop(tab: str) -> str:
    if os.name != "nt":
        return f"JAUTOMATIC { _TAB_LABELS[tab] } data is available; visual tab navigation is Windows-only."
    try:
        window = _desktop_window()
        if window is None:
            _launch_desktop()
            window = _desktop_window(timeout=12.0)
        if window is None:
            raise RuntimeError("JAUTOMATIC opened but its window was not detected.")
        try:
            window.restore()
        except Exception:
            pass
        window.set_focus()
        label = _TAB_LABELS[tab].lower()
        candidates = []
        for button in window.descendants(control_type="Button"):
            text = " ".join(button.window_text().lower().split())
            if text == label:
                candidates.append((0, button))
            elif text.endswith(f" {label}"):
                candidates.append((1, button))
            elif label in text:
                candidates.append((2, button))
        if candidates:
            min(candidates, key=lambda item: item[0])[1].click_input()
            return f"Opened the JAUTOMATIC {_TAB_LABELS[tab]} tab."
        raise RuntimeError(f"The {_TAB_LABELS[tab]} navigation button was not found.")
    except ImportError as exc:
        raise RuntimeError("pywinauto is required for visible JAUTOMATIC tab navigation.") from exc


def _show_if_requested(result: str, tab: str, parameters: dict) -> str:
    if not _as_bool(parameters.get("show")):
        return result
    try:
        navigation = _navigate_desktop(tab)
    except Exception as exc:
        navigation = f"Data action succeeded, but the desktop tab could not be opened: {exc}"
    return f"{result}\n\n{navigation}"


# ---------------------------------------------------------------------------
# Education tab (course catalog is read without importing PySide6)
# ---------------------------------------------------------------------------
def _course_catalog() -> list[dict[str, Any]]:
    _load_api()
    root = _source_root()
    source = root / "jautomatic" / "ui" / "education_tab.py" if root else None
    if source is None or not source.is_file():
        raise RuntimeError("This JAUTOMATIC version does not include the Education course catalog.")
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "COURSE_CATALOG" for target in targets):
                value = ast.literal_eval(node.value)
                if isinstance(value, list):
                    return [dict(course) for course in value if isinstance(course, dict)]
    raise RuntimeError("JAUTOMATIC's Education course catalog could not be read.")


def _education_store(profile: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(profile.extra, dict):
        profile.extra = {}
    store = profile.extra.get("education_progress")
    if not isinstance(store, dict):
        store = {}
        profile.extra["education_progress"] = store
    return store


def _course_record(profile: Any, course_id: str) -> dict[str, Any]:
    store = _education_store(profile)
    record = store.get(course_id)
    if not isinstance(record, dict):
        record = {"status": "Not started", "certificate_path": "", "completed_on": ""}
        store[course_id] = record
    return record


def _course_payload(profile: Any, course: dict[str, Any]) -> dict[str, Any]:
    record = _course_record(profile, str(course["id"]))
    return {**course, "status": record.get("status") or "Not started",
            "certificate_path": record.get("certificate_path") or "",
            "completed_on": record.get("completed_on") or ""}


def _find_course(profile: Any, parameters: dict) -> dict[str, Any]:
    course_id = str(parameters.get("course_id") or "").strip().lower()
    title = str(parameters.get("query") or parameters.get("title") or "").strip().lower()
    catalog = _course_catalog()
    if course_id:
        match = next((course for course in catalog if str(course.get("id", "")).lower() == course_id), None)
        if match:
            return match
        raise ValueError(f"Course not found: {course_id}")
    matches = [course for course in catalog if title and title in " ".join([
        str(course.get("title", "")), str(course.get("provider", "")),
        " ".join(course.get("skills") or []),
    ]).lower()]
    if len(matches) == 1:
        return matches[0]
    if not title:
        raise ValueError("course_id or a course title/query is required for this action")
    if not matches:
        raise ValueError(f"No course matched: {title}")
    raise ValueError("Several courses matched. Use the course_id returned by list_courses.")


def _education_action(workspace: Any, pipeline: Any, profile: Any,
                      action: str, parameters: dict) -> str:
    if action in {"view", "list", "list_courses", "courses", "recommendations"}:
        query = str(parameters.get("query") or "").strip().lower()
        courses = [_course_payload(profile, course) for course in _course_catalog()]
        if query:
            courses = [course for course in courses if query in " ".join([
                course["title"], course["provider"], " ".join(course["skills"]),
            ]).lower()]
        return _json({"courses": courses, "count": len(courses)})

    course = _find_course(profile, parameters)
    course_id = str(course["id"])
    if action in {"details", "get"}:
        return _json(_course_payload(profile, course))
    if action in {"open", "open_course"}:
        return _open_url(str(course.get("url") or ""), str(course.get("title") or "course"))
    if action in {"start", "in_progress", "complete", "set_status"}:
        if action == "set_status" and not str(parameters.get("status") or "").strip():
            raise ValueError("status is required when setting course progress")
        requested = str(parameters.get("status") or action).strip().lower().replace("_", " ")
        statuses = {
            "start": "In progress", "in progress": "In progress",
            "complete": "Completed", "completed": "Completed",
            "not started": "Not started", "reset": "Not started",
        }
        if requested not in statuses:
            raise ValueError("Course status must be Not started, In progress, or Completed.")
        status = statuses[requested]
        record = _course_record(profile, course_id)
        record["status"] = status
        record["completed_on"] = date.today().isoformat() if status == "Completed" else ""
        workspace.save_profile(profile)
        return f"{course['title']} marked {status}."
    if action in {"add_skills", "add_skills_to_profile"}:
        record = _course_record(profile, course_id)
        if record.get("status") != "Completed":
            raise ValueError("Mark the course Completed before adding its skills to the profile.")
        existing = {str(skill).lower() for skill in profile.skills}
        added = []
        for skill in course.get("skills") or []:
            if str(skill).lower() not in existing:
                profile.skills.append(str(skill))
                existing.add(str(skill).lower())
                added.append(str(skill))
        workspace.save_profile(profile)
        pipeline.refresh_scores(profile)
        return "Added course skills to the profile: " + (", ".join(added) if added else "none; they were already present")
    if action in {"reset", "reset_progress"}:
        _education_store(profile).pop(course_id, None)
        workspace.save_profile(profile)
        return f"Reset course progress for {course['title']}."
    raise ValueError(
        "Education supports list_courses, details, open_course, start, complete, "
        "set_status, add_skills, or reset_progress."
    )


# ---------------------------------------------------------------------------
# Tasks tab
# ---------------------------------------------------------------------------
def _task_api():
    _load_api()
    module = importlib.import_module("jautomatic.services.paid_tasks")
    recommendations = importlib.import_module("jautomatic.services.task_recommendations")
    return module.PaidTask, module.TaskStore, recommendations.recommended_task_sources


def _task_payload(task: Any) -> dict[str, Any]:
    payload = asdict(task)
    payload["expired"] = task.expired
    payload["pay_label"] = task.pay_label
    return payload


def _tasks_action(workspace: Any, profile: Any, action: str, parameters: dict) -> str:
    PaidTask, TaskStore, recommended_task_sources = _task_api()
    store = TaskStore(workspace)
    if action in {"view", "list"}:
        query = str(parameters.get("query") or "").strip().lower()
        status = str(parameters.get("status") or "").strip().lower()
        tasks = store.tasks()
        if query:
            tasks = [task for task in tasks if query in f"{task.title} {task.platform} {task.description}".lower()]
        if status:
            tasks = [task for task in tasks if task.status.lower() == status]
        return _json({"tasks": [_task_payload(task) for task in tasks], "earnings": store.earnings()})
    if action in {"recommendations", "sources"}:
        return _json({"recommendations": recommended_task_sources(profile)})
    if action == "add":
        values = parameters.get("values") or {}
        if not isinstance(values, dict):
            raise ValueError("values must contain the task details")
        allowed = set(PaidTask.__dataclass_fields__) - {"task_id", "history"}
        task = PaidTask(**{key: value for key, value in values.items() if key in allowed})
        saved, changed = store.save(task)
        return _json({"created": bool(changed), "task": _task_payload(saved)})

    task_id = str(parameters.get("task_id") or "").strip()
    task = next((item for item in store.tasks() if item.task_id == task_id), None)
    if task is None:
        raise ValueError(f"Task not found: {task_id or 'task_id is required'}")
    if action in {"open", "open_task"}:
        return _open_url(task.url, task.title)
    if action == "update":
        values = parameters.get("values") or {}
        if not isinstance(values, dict):
            raise ValueError("values must contain the task changes")
        allowed = set(PaidTask.__dataclass_fields__) - {"task_id", "history"}
        saved, _ = store.save(replace(task, **{key: value for key, value in values.items() if key in allowed}))
        return _json(_task_payload(saved))
    if action in {"set_status", "update_progress"}:
        status = str(parameters.get("status") or "").strip()
        received = parameters.get("received")
        updated = store.set_stage(task_id, status, float(received) if received is not None else None)
        return _json(_task_payload(updated))
    raise ValueError("Tasks supports list, recommendations, add, update, open_task, or set_status.")


# ---------------------------------------------------------------------------
# Public action
# ---------------------------------------------------------------------------
def jautomatic_action(parameters: dict, player=None) -> str:
    """Run a JAUTOMATIC tab action and optionally reveal that tab in its desktop UI."""
    del player  # Kept for the common JARVIS action signature.
    tab = _normalise_tab(parameters.get("tab") or "dashboard")
    action = str(parameters.get("action") or "view").lower().strip().replace(" ", "_")

    if action in {"navigate", "open_tab", "show_tab"} or (
        action in {"open", "show"} and not any(parameters.get(key) for key in (
            "job_id", "application_id", "course_id", "task_id"
        ))
    ):
        return _navigate_desktop(tab)

    data_dir = parameters.get("data_dir")
    with _pipeline(str(data_dir) if data_dir else None) as (workspace, pipeline):
        profile = workspace.load_profile()

        if tab == "dashboard":
            if action not in {"view", "stats", "refresh"}:
                raise ValueError("Dashboard supports view, stats, refresh, or navigate")
            result = _json({
                "stats": pipeline.dashboard_stats(profile),
                "follow_ups_due": [_row(row) for row in pipeline.follow_ups_due(profile)],
            })
            return _show_if_requested(result, tab, parameters)

        if tab == "profile":
            if action in {"view", "get"}:
                return _show_if_requested(_json(profile.to_dict()), tab, parameters)
            if action == "update":
                updates = parameters.get("values") or {}
                if not isinstance(updates, dict):
                    raise ValueError("values must be an object")
                allowed = set(profile.to_dict())
                unknown = sorted(set(updates) - allowed)
                if unknown:
                    raise ValueError(f"Unknown profile fields: {', '.join(unknown)}")
                merged = profile.to_dict()
                merged.update(updates)
                updated = type(profile).from_dict(merged)
                workspace.save_profile(updated)
                pipeline.refresh_scores(updated)
                result = f"JAUTOMATIC profile updated. Completeness: {updated.completeness()}%."
                return _show_if_requested(result, tab, parameters)
            raise ValueError("Profile supports view, update, or navigate")

        if tab == "education":
            result = _education_action(workspace, pipeline, profile, action, parameters)
            return _show_if_requested(result, tab, parameters)

        if tab == "search":
            if action in {"view", "list", "results", "list_jobs"}:
                jobs = _latest_jobs(workspace)
                result = _json({
                    "count": len(jobs),
                    "results": [_job_payload(workspace, pipeline, profile, job) for job in jobs],
                })
                return _show_if_requested(result, tab, parameters)
            if action in {"search", "find", "refresh"}:
                query = str(parameters.get("query") or "").strip()
                if not query:
                    raise ValueError("query is required")
                overrides = {
                    key: parameters[key]
                    for key in ("remote_only", "min_salary", "limit_per_source", "max_post_age_days")
                    if parameters.get(key) is not None
                }
                offline = _as_bool(parameters.get("offline"))
                if offline:
                    overrides["sources"] = ["sample"]
                    overrides["include_sample"] = True
                location = str(parameters.get("location") or "")
                if offline:
                    # JAUTOMATIC normally adds its UAE feed in build_query even when
                    # a caller supplies a source list. Force the declared offline
                    # mode back to the sample source before any network work starts.
                    built_query = pipeline.build_query(query, location, **overrides)
                    built_query.sources = ["sample"]
                    built_query.include_sample = True
                    outcome = pipeline.scraper.search(built_query)
                else:
                    outcome = pipeline.search(query, location, **overrides)
                workspace.save_jobs(outcome.jobs)
                settings = workspace.load_settings()
                settings.last_search_query = query
                settings.last_search_location = location
                settings.last_search_job_ids = [job.job_id for job in outcome.jobs]
                workspace.save_settings(settings)
                result = _json({
                    "summary": outcome.summary(),
                    "saved_results": len(outcome.jobs),
                    "results": [_job_payload(workspace, pipeline, profile, job) for job in outcome.jobs],
                    "next": "Use move_to_applications with job_ids, count, or all_results=true; use prepare to generate materials.",
                })
                return _show_if_requested(result, tab, parameters)
            if action in {"move", "track", "import", "move_to_applications", "add_to_applications"}:
                jobs = _select_jobs(workspace, pipeline, profile, parameters, allow_latest_default=True)
                created = pipeline.import_jobs(jobs)
                result = _json({
                    "moved": len(jobs),
                    "new_applications": len(created),
                    "applications": [
                        _job_payload(workspace, pipeline, profile, job) for job in jobs
                    ],
                })
                target = "applications" if _as_bool(parameters.get("show")) else tab
                return _show_if_requested(result, target, parameters)
            if action in {"prepare", "prepare_materials"}:
                result = _prepare_jobs(workspace, pipeline, profile, parameters)
                target = "applications" if _as_bool(parameters.get("show")) else tab
                return _show_if_requested(result, target, parameters)
            if action in {"open_job", "open_posting"}:
                job = _select_jobs(workspace, pipeline, profile, parameters, allow_latest_default=True)[0]
                return _open_url(job.url, f"{job.title} at {job.company}")
            if action == "shortlist":
                jobs = _select_jobs(workspace, pipeline, profile, parameters, allow_latest_default=True)
                for job in jobs:
                    pipeline.set_status(pipeline.ensure_application(job), "shortlisted", "shortlisted by JARVIS")
                return _json({"shortlisted": len(jobs), "job_ids": [job.job_id for job in jobs]})
            raise ValueError(
                "Search supports search, list_jobs, move_to_applications, prepare, "
                "shortlist, open_job, or navigate."
            )

        if tab == "tasks":
            result = _tasks_action(workspace, profile, action, parameters)
            return _show_if_requested(result, tab, parameters)

        if tab in {"applications", "sent", "archive"}:
            rows = pipeline.tracker(profile)
            if tab == "sent":
                rows = [row for row in rows if row.application.status in {"sent", "interview", "offer"}]
            elif tab == "archive":
                rows = [row for row in rows if row.application.status in {"archived", "rejected", "withdrawn"}]
            if action in {"view", "list"}:
                return _show_if_requested(_json([_row(row) for row in rows]), tab, parameters)
            if action in {"add_matching", "add_matching_jobs"}:
                threshold = int(parameters.get("min_score") or pipeline.settings.min_match_score)
                _, added = pipeline.import_qualified(workspace.jobs(), profile, threshold=threshold)
                result = f"Added {len(added)} matching saved job(s) to Applications."
                return _show_if_requested(result, "applications", parameters)
            if action in {"prepare", "prepare_materials"}:
                if parameters.get("application_id"):
                    materials = pipeline.prepare(_find(pipeline, str(parameters.get("application_id"))), profile)
                    result = _json(_materials_payload(materials))
                else:
                    result = _prepare_jobs(workspace, pipeline, profile, parameters)
                return _show_if_requested(result, "applications", parameters)

            record = _find(pipeline, str(parameters.get("application_id") or ""))
            if action == "set_status":
                updated = pipeline.set_status(record, str(parameters.get("status") or ""),
                                              str(parameters.get("note") or ""))
                result = f"Application {updated.application_id} changed to {updated.status}."
            elif action in {"interview_prep", "prepare_interview"}:
                prep, added = pipeline.generate_interview_prep(record, profile)
                path = pipeline.export_interview_prep(record, profile)
                result = _json({"questions": len(prep.questions), "new_questions": len(added), "path": str(path)})
            elif action in {"open_job", "open_posting"}:
                job = _find_job(workspace, record.job_id)
                result = _open_url(job.url, f"{job.title} at {job.company}")
            elif action in {"open_document", "open_material"}:
                kind = str(parameters.get("document_kind") or "cv").lower().strip()
                paths = {"cv": record.cv_path, "cover": record.cover_letter_path,
                         "cover_letter": record.cover_letter_path, "email": record.email_path,
                         "interview_prep": record.prep_path}
                if kind not in paths:
                    raise ValueError("document_kind must be cv, cover_letter, email, or interview_prep")
                result = _open_path(paths[kind], kind.replace("_", " "))
            elif action == "draft_follow_up":
                path, text = pipeline.draft_follow_up(record)
                result = _json({"path": str(path), "draft": text})
            elif action == "postpone":
                updated = pipeline.postpone_follow_up(record, int(parameters.get("days") or 5))
                result = f"Follow-up postponed until {updated.follow_up_at}."
            elif action == "mark_follow_up_sent":
                updated = pipeline.mark_follow_up_sent(record)
                result = f"Follow-up recorded; next reminder: {updated.follow_up_at or 'none'}."
            elif action in {"save_notes", "update_notes"}:
                updated = pipeline.update_notes(record, str(parameters.get("note") or ""))
                result = f"Notes saved for application {updated.application_id}."
            else:
                raise ValueError(
                    f"{tab.title()} supports list, add_matching, prepare, set_status, "
                    "open_job, open_document, interview_prep, follow-up actions, or navigate."
                )
            return _show_if_requested(result, tab, parameters)

        if tab == "insights":
            if action not in {"view", "analytics", "refresh"}:
                raise ValueError("Insights supports view, analytics, refresh, or navigate")
            return _show_if_requested(_json(pipeline.analytics(profile)), tab, parameters)

        if tab == "settings":
            settings = workspace.load_settings()
            if action in {"view", "get"}:
                result = _json(settings.to_dict())
            elif action == "update":
                updates = parameters.get("values") or {}
                if not isinstance(updates, dict):
                    raise ValueError("values must be an object")
                merged = settings.to_dict()
                unknown = sorted(set(updates) - set(merged))
                if unknown:
                    raise ValueError(f"Unknown settings: {', '.join(unknown)}")
                merged.update(updates)
                workspace.save_settings(type(settings).from_dict(merged))
                result = "JAUTOMATIC settings updated."
            elif action == "export_csv":
                result = f"Tracker exported to {pipeline.export_tracker_csv(profile)}"
            elif action == "export_calendar":
                result = f"Calendar exported to {pipeline.export_calendar_ics(profile)}"
            else:
                raise ValueError("Settings supports view, update, export_csv, export_calendar, or navigate")
            return _show_if_requested(result, tab, parameters)

    raise AssertionError("unreachable")
