import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml must define a project version"
    return match.group(1)


def test_release_version_has_one_value():
    version = _project_version()
    package_init = (ROOT / "src/jarvis/__init__.py").read_text(encoding="utf-8")
    frontend = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))

    assert f'__version__ = "{version}"' in package_init
    assert frontend["version"] == version


def test_canonical_installer_is_opt_in_for_startup():
    wix = (ROOT / "deploy/windows/jarvis.wxs").read_text(encoding="utf-8")

    assert "jarvis-desktop.exe" in wix
    assert "MajorUpgrade" in wix
    assert "CurrentVersion\\Run" not in wix
    assert 'Component Id="AutoStart"' not in wix


def test_only_canonical_msi_workflow_remains():
    workflow_dir = ROOT / ".github/workflows"
    msi_workflows = sorted(path.name for path in workflow_dir.glob("*msi*.yml"))
    assert msi_workflows == ["windows-msi.yml"]
