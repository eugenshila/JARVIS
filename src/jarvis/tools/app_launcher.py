"""Safe launcher for installed desktop applications.

JARVIS may open installed software, but only through an allow-list.  This
prevents a chat prompt from becoming arbitrary shell execution.
"""

from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from jarvis.core import confirm as confirm_gate

from jarvis.core.config import get_home
from jarvis.tools.base import BaseTool, ToolSpec


SAFE_EXTENSIONS = {".exe", ".lnk", ".app", ""}
SCRIPT_EXTENSIONS = {".bat", ".cmd", ".ps1", ".vbs", ".js", ".jar"}


def _apps_path() -> Path:
    home = get_home()
    home.mkdir(parents=True, exist_ok=True)
    return home / "apps.json"


def _key(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _is_safe_app_path(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in SCRIPT_EXTENSIONS:
        return False
    return suffix in SAFE_EXTENSIONS


class AppLauncherTool(BaseTool):
    spec = ToolSpec(
        name="app_launcher",
        description=(
            "Safely list, register, and launch installed desktop software. "
            "Launches only allow-listed apps and requires confirm=true."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "discover", "add", "remove", "launch", "instructions"],
                    "description": "Action to perform",
                    "default": "list",
                },
                "app": {"type": "string", "description": "App name to launch/remove", "default": ""},
                "name": {"type": "string", "description": "Friendly app name when adding", "default": ""},
                "path": {"type": "string", "description": "Absolute path to app executable/shortcut", "default": ""},
                "args": {"type": "string", "description": "Optional args; ignored unless app allows args", "default": ""},
                "confirm": {"type": "boolean", "description": "Must be true to launch", "default": False},
                "allow_args": {"type": "boolean", "description": "Allow this app to receive args when adding", "default": False},
            },
            "required": [],
        },
        requires_approval=True,
    )

    def run(
        self,
        action: str = "list",
        app: str = "",
        name: str = "",
        path: str = "",
        args: str = "",
        confirm: bool = False,
        allow_args: bool = False,
        **kwargs: Any,
    ) -> str:
        action = (action or "list").lower()
        if action == "discover":
            apps = self.discover_apps()
            self._save_apps(apps)
            return self._format_apps(apps, title="Discovered safe apps")
        if action == "add":
            return self.add_app(name=name or app, path=path, allow_args=allow_args)
        if action == "remove":
            return self.remove_app(app=app or name)
        if action == "launch":
            return self.launch_app(app=app or name, args=args, confirm=confirm)
        if action == "instructions":
            return self.instructions()
        return self._format_apps(self.load_apps(), title="Allowed apps")

    def instructions(self) -> str:
        return """**Safe App Launcher**

JARVIS can open installed software only from a local allow-list.

Commands:
  • `jarvis apps --list` — show allowed apps
  • `jarvis apps --discover` — find common installed apps
  • `jarvis apps --add --name Outlook --path "C:\\...\\OUTLOOK.EXE"` — approve an app
  • `jarvis apps --launch Outlook --yes` — launch approved app

Safety rules:
  • No arbitrary shell commands from chat
  • Scripts like .bat/.cmd/.ps1 are blocked
  • Launch requires explicit confirmation
  • App paths are stored locally in ~/.jarvis/apps.json
"""

    def load_apps(self) -> list[dict[str, Any]]:
        path = _apps_path()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    cleaned = [self._clean_record(item) for item in data if isinstance(item, dict)]
                    return [item for item in cleaned if item]
            except Exception:
                pass
        apps = self.discover_apps()
        if apps:
            self._save_apps(apps)
        return apps

    def discover_apps(self) -> list[dict[str, Any]]:
        candidates: list[tuple[str, str]] = []
        system = platform.system().lower()
        if system == "windows":
            program_files = [os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
            local_appdata = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
            windir = os.environ.get("WINDIR", r"C:\Windows")
            candidates.extend([
                ("Notepad", str(Path(windir) / "System32" / "notepad.exe")),
                ("Calculator", str(Path(windir) / "System32" / "calc.exe")),
                ("Paint", str(Path(windir) / "System32" / "mspaint.exe")),
                ("Chrome", str(Path(program_files[0]) / "Google" / "Chrome" / "Application" / "chrome.exe")),
                ("Edge", str(Path(program_files[0]) / "Microsoft" / "Edge" / "Application" / "msedge.exe")),
                ("VS Code", str(Path(local_appdata) / "Programs" / "Microsoft VS Code" / "Code.exe")),
                ("Outlook", str(Path(program_files[0]) / "Microsoft Office" / "root" / "Office16" / "OUTLOOK.EXE")),
                ("Word", str(Path(program_files[0]) / "Microsoft Office" / "root" / "Office16" / "WINWORD.EXE")),
                ("Excel", str(Path(program_files[0]) / "Microsoft Office" / "root" / "Office16" / "EXCEL.EXE")),
                ("PowerPoint", str(Path(program_files[0]) / "Microsoft Office" / "root" / "Office16" / "POWERPNT.EXE")),
                ("Teams", str(Path(local_appdata) / "Microsoft" / "Teams" / "current" / "Teams.exe")),
                ("JAUTOMATIC", str(Path(program_files[0]) / "JAUTOMATIC" / "jautomatic.exe")),
            ])
            # Office may be installed under Program Files (x86)
            candidates.extend([
                ("Outlook", str(Path(program_files[1]) / "Microsoft Office" / "root" / "Office16" / "OUTLOOK.EXE")),
                ("Word", str(Path(program_files[1]) / "Microsoft Office" / "root" / "Office16" / "WINWORD.EXE")),
                ("Excel", str(Path(program_files[1]) / "Microsoft Office" / "root" / "Office16" / "EXCEL.EXE")),
            ])
        elif system == "darwin":
            candidates.extend([
                ("Safari", "/Applications/Safari.app"),
                ("Calendar", "/System/Applications/Calendar.app"),
                ("Mail", "/System/Applications/Mail.app"),
                ("VS Code", "/Applications/Visual Studio Code.app"),
                ("Chrome", "/Applications/Google Chrome.app"),
            ])
        else:
            for label, executable in [
                ("VS Code", "code"),
                ("Chrome", "google-chrome"),
                ("Chromium", "chromium"),
                ("Firefox", "firefox"),
                ("LibreOffice", "libreoffice"),
            ]:
                found = shutil.which(executable)
                if found:
                    candidates.append((label, found))

        apps: list[dict[str, Any]] = []
        seen: set[str] = set()
        for label, raw_path in candidates:
            p = Path(raw_path).expanduser()
            if not p.exists() or not _is_safe_app_path(p):
                continue
            key = _key(label)
            if key in seen:
                continue
            seen.add(key)
            apps.append({"name": label, "path": str(p), "allow_args": False, "source": "discovered"})
        return apps

    def add_app(self, name: str, path: str, allow_args: bool = False) -> str:
        if not name.strip():
            return "App name is required, Sir."
        if not path.strip():
            return "App path is required. Use the installed executable path, not a shell command."
        p = Path(path).expanduser()
        if not p.exists():
            return f"App path not found: {p}"
        if not _is_safe_app_path(p):
            return "Blocked: scripts and unsafe file types cannot be added to the app launcher. Use the real installed app executable."

        apps = self.load_apps()
        new_record = {"name": name.strip(), "path": str(p), "allow_args": bool(allow_args), "source": "user"}
        replaced = False
        for idx, record in enumerate(apps):
            if _key(record.get("name", "")) == _key(name):
                apps[idx] = new_record
                replaced = True
                break
        if not replaced:
            apps.append(new_record)
        self._save_apps(apps)
        return f"{'Updated' if replaced else 'Added'} app allow-list entry: {name} → {p}"

    def remove_app(self, app: str) -> str:
        if not app.strip():
            return "App name required."
        apps = self.load_apps()
        before = len(apps)
        apps = [record for record in apps if _key(record.get("name", "")) != _key(app)]
        self._save_apps(apps)
        if len(apps) == before:
            return f"No app named '{app}' was in the allow-list."
        return f"Removed '{app}' from the app allow-list."

    def launch_app(self, app: str, args: str = "", confirm: bool = False, **kwargs) -> str:
        if not app.strip():
            return "Which app should I open, Sir? Use `jarvis apps --list` to see approved apps."
        record = self._find_app(app)
        if not record:
            return (
                f"'{app}' is not approved yet. Add it first with `jarvis apps --add --name {app} --path <installed app path>`. "
                "I will not run arbitrary commands from chat."
            )
        # `confirm` is a tool parameter, which means the MODEL writes it — it is
        # not evidence a human agreed. It is still honoured for the CLI
        # (`jarvis apps --launch X --yes`), which is a real human at a real
        # keyboard, but a model-driven call now goes through the interface gate
        # in jarvis/core/confirm.py instead.
        if not confirm:
            pending = confirm_gate.request(
                title=f"Launch {record['name']}",
                detail=str(record.get("path", "")),
                run=lambda: self._launch_now(record, args),
            )
            return (
                f"Awaiting your confirmation to launch {record['name']} "
                f"(token {pending.token[:8]}…). Or run "
                f"`jarvis apps --launch {record['name']} --yes`."
            )
        return self._launch_now(record, args)

    def _launch_now(self, record: dict, args: str = "") -> str:

        p = Path(record["path"]).expanduser()
        if not p.exists() or not _is_safe_app_path(p):
            return f"Approved app path is no longer valid or safe: {p}"

        argv: list[str] = []
        if args.strip():
            if record.get("allow_args"):
                try:
                    argv = shlex.split(args, posix=platform.system().lower() != "windows")
                except ValueError as exc:
                    return f"Could not parse app arguments: {exc}"
            else:
                return f"Arguments are disabled for {record['name']} for safety. Launching with arguments was blocked."

        try:
            if platform.system().lower() == "windows" and p.suffix.lower() == ".lnk":
                os.startfile(str(p))  # type: ignore[attr-defined]
            elif platform.system().lower() == "darwin" and p.suffix.lower() == ".app":
                subprocess.Popen(["open", str(p), *argv], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen([str(p), *argv], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except Exception as exc:
            return f"Failed to launch {record['name']}: {exc}"
        return f"Launching {record['name']}, Sir."

    def _find_app(self, app: str) -> dict[str, Any] | None:
        requested = _key(app)
        for record in self.load_apps():
            if _key(record.get("name", "")) == requested:
                return record
        # Fuzzy contains for convenience: "out" -> Outlook, if unique.
        matches = [record for record in self.load_apps() if requested and requested in _key(record.get("name", ""))]
        if len(matches) == 1:
            return matches[0]
        return None

    def _clean_record(self, item: dict[str, Any]) -> dict[str, Any] | None:
        name = str(item.get("name", "")).strip()
        path = str(item.get("path", "")).strip()
        if not name or not path:
            return None
        p = Path(path).expanduser()
        if not p.exists() or not _is_safe_app_path(p):
            return None
        return {
            "name": name,
            "path": str(p),
            "allow_args": bool(item.get("allow_args", False)),
            "source": str(item.get("source", "user")),
        }

    def _save_apps(self, apps: list[dict[str, Any]]) -> None:
        cleaned = [self._clean_record(record) for record in apps]
        final = [record for record in cleaned if record]
        _apps_path().write_text(json.dumps(final, indent=2), encoding="utf-8")

    def _format_apps(self, apps: list[dict[str, Any]], title: str) -> str:
        if not apps:
            return (
                f"**{title}: none found yet.**\n\n"
                "Use `jarvis apps --discover` or add an app path manually. "
                "Only approved installed apps can be launched."
            )
        lines = [f"**{title} — {len(apps)} approved:**", ""]
        for record in apps:
            args_note = " args allowed" if record.get("allow_args") else ""
            lines.append(f"  • {record.get('name')} — {record.get('path')}{args_note}")
        lines.extend(["", "Launch example: `jarvis apps --launch Outlook --yes`"])
        return "\n".join(lines)
