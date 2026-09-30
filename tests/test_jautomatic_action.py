from __future__ import annotations

import sys
import types

import pytest

from actions import jautomatic


class FakeProfile:
    education = []

    def to_dict(self):
        return {"name": "Test User"}

    def completeness(self):
        return 50


class FakeSettings:
    def to_dict(self):
        return {"remote_only": False}

    @classmethod
    def from_dict(cls, values):
        obj = cls()
        obj.values = values
        return obj


class FakeWorkspace:
    closed = False

    def __init__(self, data_dir=None):
        self.root = data_dir

    def load_settings(self):
        return FakeSettings()

    def load_profile(self):
        return FakeProfile()

    def save_settings(self, settings):
        self.saved_settings = settings

    def close(self):
        self.closed = True


class FakePipeline:
    def __init__(self, workspace, settings):
        self.workspace = workspace

    def dashboard_stats(self, profile):
        return {"applications": 3}

    def follow_ups_due(self, profile):
        return []

    def analytics(self, profile):
        return {"response_rate": 25}


def install_fake_api(monkeypatch):
    models = types.ModuleType("jautomatic.models")
    models.Workspace = FakeWorkspace
    pipeline = types.ModuleType("jautomatic.services.application_pipeline")
    pipeline.ApplicationPipeline = FakePipeline
    monkeypatch.setitem(sys.modules, "jautomatic", types.ModuleType("jautomatic"))
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
