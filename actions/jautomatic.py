"""JARVIS action bridge for the JAUTOMATIC JOB SEARCH service layer.

The bridge deliberately imports JAUTOMATIC's headless models/services, not its Qt UI.
Set ``JAUTOMATIC_PATH`` to the JAUTOMATIC repository root when it is not installed
next to JARVIS. Both applications then use JAUTOMATIC's normal local workspace.
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterator


def _candidate_roots() -> list[Path]:
    configured = os.environ.get("JAUTOMATIC_PATH", "").strip()
    here = Path(__file__).resolve().parents[1]
    roots = [Path(configured).expanduser()] if configured else []
    roots += [
        here.parent / "JAUTOMATIC-JOB-SEARCH",
        Path.home() / "JAUTOMATIC-JOB-SEARCH",
        Path.home() / "Documents" / "JAUTOMATIC-JOB-SEARCH",
    ]
    return roots


def _load_api():
    try:
        from jautomatic.models import Workspace
        from jautomatic.services.application_pipeline import ApplicationPipeline
        return Workspace, ApplicationPipeline
    except ImportError:
        pass

    for root in _candidate_roots():
        if (root / "jautomatic" / "models.py").is_file():
            value = str(root.resolve())
            if value not in sys.path:
                sys.path.insert(0, value)
            from jautomatic.models import Workspace
            from jautomatic.services.application_pipeline import ApplicationPipeline
            return Workspace, ApplicationPipeline
    raise RuntimeError(
        "JAUTOMATIC was not found. Clone eugenshila/JAUTOMATIC-JOB-SEARCH next "
        "to JARVIS or set JAUTOMATIC_PATH to its repository folder."
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


def _row(row: Any) -> dict[str, Any]:
    return {
        "application_id": row.application.application_id,
        "title": row.job.title,
        "company": row.job.company,
        "location": row.job.display_location,
        "score": row.score,
        "status": row.application.status,
        "url": row.job.url,
        "follow_up_at": row.application.follow_up_at,
        "interview_at": row.application.interview_at,
    }


def _find(pipeline: Any, application_id: str) -> Any:
    application_id = str(application_id or "").strip()
    if not application_id:
        raise ValueError("application_id is required for this action")
    record = pipeline.workspace.get_application(application_id)
    if record is None:
        raise ValueError(f"Application not found: {application_id}")
    return record


def jautomatic_action(parameters: dict, player=None) -> str:
    """Run a headless JAUTOMATIC operation grouped by its desktop tab."""
    tab = str(parameters.get("tab") or "dashboard").lower().strip()
    action = str(parameters.get("action") or "view").lower().strip()
    data_dir = parameters.get("data_dir")

    with _pipeline(str(data_dir) if data_dir else None) as (workspace, pipeline):
        profile = workspace.load_profile()

        if tab == "dashboard":
            if action not in {"view", "stats", "refresh"}:
                raise ValueError("Dashboard supports view, stats, or refresh")
            return _json({"stats": pipeline.dashboard_stats(profile), "follow_ups_due": [_row(r) for r in pipeline.follow_ups_due(profile)]})

        if tab == "profile":
            if action in {"view", "get"}:
                return _json(profile.to_dict())
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
                return f"JAUTOMATIC profile updated. Completeness: {updated.completeness()}%."
            raise ValueError("Profile supports view or update")

        if tab == "education":
            if action in {"view", "list"}:
                return _json({"education": [asdict(x) for x in profile.education]})
            raise ValueError("Education currently supports view")

        if tab == "search":
            if action not in {"search", "find"}:
                raise ValueError("Search tab supports search")
            query = str(parameters.get("query") or "").strip()
            if not query:
                raise ValueError("query is required")
            overrides = {
                key: parameters[key] for key in ("remote_only", "min_salary", "limit_per_source", "max_post_age_days")
                if parameters.get(key) is not None
            }
            if parameters.get("offline"):
                overrides["sources"] = ["sample"]
                overrides["include_sample"] = True
            outcome, created = pipeline.search_and_import(query, str(parameters.get("location") or ""), **overrides)
            rows = pipeline.tracker(profile)
            wanted = {job.job_id for job in outcome.jobs}
            return _json({"summary": outcome.summary(), "new_applications": len(created), "results": [_row(r) for r in rows if r.job.job_id in wanted]})

        if tab in {"applications", "sent", "archive"}:
            rows = pipeline.tracker(profile)
            if tab == "sent":
                rows = [r for r in rows if r.application.status in {"sent", "interview", "offer"}]
            elif tab == "archive":
                rows = [r for r in rows if r.application.status in {"archived", "rejected", "withdrawn"}]
            if action in {"view", "list"}:
                return _json([_row(r) for r in rows])
            record = _find(pipeline, str(parameters.get("application_id") or ""))
            if action == "prepare":
                materials = pipeline.prepare(record, profile)
                return _json({"application_id": record.application_id, "documents": [str(path) for path in materials.paths]})
            if action == "set_status":
                updated = pipeline.set_status(record, str(parameters.get("status") or ""), str(parameters.get("note") or ""))
                return f"Application {updated.application_id} changed to {updated.status}."
            if action == "interview_prep":
                prep, added = pipeline.generate_interview_prep(record, profile)
                path = pipeline.export_interview_prep(record, profile)
                return _json({"questions": len(prep.questions), "new_questions": len(added), "path": str(path)})
            raise ValueError(f"{tab.title()} supports list, prepare, set_status, or interview_prep")

        if tab == "tasks":
            if action in {"view", "list"}:
                return _json({"follow_ups_due": [_row(r) for r in pipeline.follow_ups_due(profile)]})
            record = _find(pipeline, str(parameters.get("application_id") or ""))
            if action == "draft_follow_up":
                path, text = pipeline.draft_follow_up(record)
                return _json({"path": str(path), "draft": text})
            if action == "postpone":
                updated = pipeline.postpone_follow_up(record, int(parameters.get("days") or 5))
                return f"Follow-up postponed until {updated.follow_up_at}."
            raise ValueError("Tasks supports list, draft_follow_up, or postpone")

        if tab == "insights":
            if action not in {"view", "analytics", "refresh"}:
                raise ValueError("Insights supports view or analytics")
            return _json(pipeline.analytics(profile))

        if tab == "settings":
            settings = workspace.load_settings()
            if action in {"view", "get"}:
                return _json(settings.to_dict())
            if action == "update":
                updates = parameters.get("values") or {}
                if not isinstance(updates, dict):
                    raise ValueError("values must be an object")
                merged = settings.to_dict()
                unknown = sorted(set(updates) - set(merged))
                if unknown:
                    raise ValueError(f"Unknown settings: {', '.join(unknown)}")
                merged.update(updates)
                workspace.save_settings(type(settings).from_dict(merged))
                return "JAUTOMATIC settings updated."
            if action == "export_csv":
                return f"Tracker exported to {pipeline.export_tracker_csv(profile)}"
            if action == "export_calendar":
                return f"Calendar exported to {pipeline.export_calendar_ics(profile)}"
            raise ValueError("Settings supports view, update, export_csv, or export_calendar")

        raise ValueError("Unknown JAUTOMATIC tab. Use dashboard, profile, education, search, applications, sent, archive, tasks, insights, or settings.")
