from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass

import pytest

from actions import jautomatic


class FakeProfile:
    education = []

    def __init__(self):
        self.extra = {}
        self.skills = []

    def to_dict(self):
        return {"name": "Test User"}

    def completeness(self):
        return 50


class FakeSettings:
    last_search_job_ids = []
    min_match_score = 80

    def to_dict(self):
        return {"remote_only": False}

    @classmethod
    def from_dict(cls, values):
        obj = cls()
        obj.values = values
        return obj


@dataclass
class FakeJob:
    job_id: str
    title: str = "Data Analyst"
    company: str = "Example Ltd"
    display_location: str = "Remote"
    salary_text: str = "Not disclosed"
    source: str = "sample"
    url: str = "https://example.com/job"


@dataclass
class FakeApplication:
    application_id: str
    job_id: str
    status: str = "discovered"


class FakeWorkspace:
    closed = False
    last_instance = None

    def __init__(self, data_dir=None):
        self.root = data_dir
        self.profile = FakeProfile()
        self.settings = FakeSettings()
        self.jobs_by_id = {}
        self.apps_by_job = {}
        self.saved_profile = None
        type(self).last_instance = self

    def load_settings(self):
        return self.settings

    def save_settings(self, settings):
        self.settings = settings

    def load_profile(self):
        return self.profile

    def save_profile(self, profile):
        self.saved_profile = profile
        self.profile = profile

    def get_job(self, job_id):
        return self.jobs_by_id.get(job_id)

    def application_for_job(self, job_id):
        return self.apps_by_job.get(job_id)

    def get_application(self, application_id):
        return next((app for app in self.apps_by_job.values()
                     if app.application_id == application_id), None)

    def close(self):
        self.closed = True


class FakeMatch:
    score = 84
    matched_keywords = ["excel"]
    missing_keywords = ["power bi"]
    reasons = ["profile match"]


class FakePipeline:
    def __init__(self, workspace, settings):
        self.workspace = workspace
        self.settings = settings

    def dashboard_stats(self, profile):
        return {"applications": 3}

    def follow_ups_due(self, profile):
        return []

    def analytics(self, profile):
        return {"response_rate": 25}

    def refresh_scores(self, profile):
        return 0

    def import_jobs(self, jobs):
        created = []
        for job in jobs:
            if self.workspace.application_for_job(job.job_id) is None:
                application = FakeApplication(f"app-{job.job_id}", job.job_id)
                self.workspace.apps_by_job[job.job_id] = application
                created.append(application)
        return created


def install_fake_api(monkeypatch):
    models = types.ModuleType("jautomatic.models")
    models.Workspace = FakeWorkspace
    pipeline = types.ModuleType("jautomatic.services.application_pipeline")
    pipeline.ApplicationPipeline = FakePipeline
    pipeline.match_job = lambda *_args, **_kwargs: FakeMatch()
    package = types.ModuleType("jautomatic")
    package.__file__ = "/fake/jautomatic/__init__.py"
    monkeypatch.setitem(sys.modules, "jautomatic", package)
    monkeypatch.setitem(sys.modules, "jautomatic.models", models)
    monkeypatch.setitem(sys.modules, "jautomatic.services", types.ModuleType("jautomatic.services"))
    monkeypatch.setitem(sys.modules, "jautomatic.services.application_pipeline", pipeline)


def test_dashboard_action_uses_headless_pipeline(monkeypatch):
    install_fake_api(monkeypatch)
    result = jautomatic.jautomatic_action({"tab": "dashboard", "action": "view"})
    assert '"applications": 3' in result


def test_insights_action_maps_to_analytics(monkeypatch):
    install_fake_api(monkeypatch)
    result = jautomatic.jautomatic_action({"tab": "insights", "action": "analytics"})
    assert '"response_rate": 25' in result


def test_unknown_tab_is_rejected(monkeypatch):
    install_fake_api(monkeypatch)
    with pytest.raises(ValueError, match="Unknown JAUTOMATIC tab"):
        jautomatic.jautomatic_action({"tab": "unknown", "action": "view"})


def test_navigate_opens_requested_desktop_tab_without_loading_workspace(monkeypatch):
    opened = []
    monkeypatch.setattr(jautomatic, "_navigate_desktop", lambda tab: opened.append(tab) or "opened")

    result = jautomatic.jautomatic_action({"tab": "education", "action": "navigate"})

    assert result == "opened"
    assert opened == ["education"]


def test_education_lists_real_course_records_instead_of_profile_degrees(monkeypatch):
    install_fake_api(monkeypatch)
    monkeypatch.setattr(jautomatic, "_course_catalog", lambda: [{
        "id": "power-bi",
        "title": "Power BI",
        "provider": "Microsoft Learn",
        "skills": ["power bi"],
        "url": "https://example.com/course",
        "credential": "Training",
    }])

    result = json.loads(jautomatic.jautomatic_action({
        "tab": "education", "action": "list_courses",
    }))

    assert result["count"] == 1
    assert result["courses"][0]["id"] == "power-bi"
    assert result["courses"][0]["status"] == "Not started"


def test_education_progress_is_saved_to_shared_profile(monkeypatch):
    install_fake_api(monkeypatch)
    monkeypatch.setattr(jautomatic, "_course_catalog", lambda: [{
        "id": "power-bi", "title": "Power BI", "provider": "Microsoft Learn",
        "skills": ["power bi"], "url": "https://example.com/course",
    }])

    result = jautomatic.jautomatic_action({
        "tab": "education", "action": "complete", "course_id": "power-bi",
    })

    workspace = FakeWorkspace.last_instance
    assert "marked Completed" in result
    assert workspace.saved_profile.extra["education_progress"]["power-bi"]["status"] == "Completed"


def test_latest_search_jobs_can_move_to_applications(monkeypatch):
    install_fake_api(monkeypatch)
    original_init = FakeWorkspace.__init__

    def initialise_with_job(self, data_dir=None):
        original_init(self, data_dir)
        job = FakeJob("job-1")
        self.jobs_by_id[job.job_id] = job
        self.settings.last_search_job_ids = [job.job_id]

    monkeypatch.setattr(FakeWorkspace, "__init__", initialise_with_job)

    result = json.loads(jautomatic.jautomatic_action({
        "tab": "search",
        "action": "move_to_applications",
        "job_id": "job-1",
    }))

    assert result["moved"] == 1
    assert result["new_applications"] == 1
    assert result["applications"][0]["application_id"] == "app-job-1"
