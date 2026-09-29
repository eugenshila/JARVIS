"""
tools/discovery.py — find tools by scanning the package, not by editing a list.

WHY THIS EXISTS
    ``tools/registry.py`` was a hand-maintained import list: roughly twenty
    ``try: from ... import X / except ImportError: HAS_X = False`` blocks and a
    dict literal naming every class twice. Adding a tool meant editing that
    file, and forgetting to meant the tool silently did not exist.

    Discovery makes adding a bundled tool a one-file operation: drop a module
    into ``jarvis/tools/`` (or ``~/.jarvis/plugins/``) that defines a
    :class:`~jarvis.tools.base.BaseTool` subclass with a ``spec``, and it is
    found at startup.

WHAT A TOOL DECLARES
    Beyond the existing ``ToolSpec``, a tool may say how it should be *run*:

      ``behavior``    BLOCKING (default) or NON_BLOCKING — a slow tool can say
                      so, and the caller need not hold the conversation open
                      waiting for it.
      ``scheduling``  WHEN_IDLE (default), SILENT, or INTERRUPT — when a
                      NON_BLOCKING result is allowed back into the
                      conversation: at the next pause, not at all (the tool
                      already told the user), or immediately.

FAILURE POLICY
    Import errors, bad specs and name collisions are recorded on the record and
    the module is skipped. Discovery NEVER raises and never aborts the scan of
    the remaining modules — one broken optional dependency must not take the
    whole tool set down with it.

ENABLE / DISABLE
    Read from ``~/.jarvis/tools.json`` on *every* lookup (mtime-cached), so
    toggling a tool in the UI takes effect without a restart.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import pkgutil
import re
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from collections.abc import Iterable

from jarvis.tools.base import BaseTool

_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")

BEHAVIORS = ("BLOCKING", "NON_BLOCKING")
SCHEDULING = ("WHEN_IDLE", "SILENT", "INTERRUPT")

#: The module holding the fallback implementations. Anything else that claims
#: the same tool name is treated as a deliberate upgrade of it (e.g.
#: search_tools.HybridSearchTool over builtins.WebSearchTool) rather than as a
#: collision. Two *non*-builtin modules claiming one name is still an error.
_BUILTIN_MODULE = "jarvis.tools.builtins"

#: Modules in jarvis.tools that are infrastructure, not tools.
_SKIP_MODULES = {"base", "registry", "discovery"}


def _norm(value: Any, allowed: tuple[str, ...], default: str) -> str:
    v = str(value or "").strip().upper().replace("-", "_")
    return v if v in allowed else default


@dataclass
class ToolRecord:
    name: str
    cls: type[BaseTool] | None = None
    module: str = ""
    description: str = ""
    requires_approval: bool = False
    behavior: str = "BLOCKING"
    scheduling: str = "WHEN_IDLE"
    valid: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "module": self.module,
            "description": self.description,
            "requires_approval": self.requires_approval,
            "behavior": self.behavior,
            "scheduling": self.scheduling,
            "valid": self.valid,
            "error": self.error,
            "enabled": is_enabled(self.name),
        }


# ── Enable / disable state, re-read per lookup ────────────────────────────────


class _EnabledState:
    """``~/.jarvis/tools.json`` → ``{"disabled": ["shell", ...]}``.

    Re-read whenever the file's mtime changes, so a UI toggle needs no restart,
    but a hot loop does not stat-and-parse JSON on every single dispatch.
    """

    def __init__(self) -> None:
        self._disabled: set[str] = set()
        self._mtime: float = -1.0
        self._checked: float = 0.0
        self._lock = threading.Lock()

    def _path(self) -> Path:
        from jarvis.core.config import get_home

        return get_home() / "tools.json"

    def disabled(self) -> set[str]:
        now = time.monotonic()
        with self._lock:
            if now - self._checked < 1.0:
                return set(self._disabled)
            self._checked = now
            path = self._path()
            try:
                mtime = path.stat().st_mtime
            except OSError:
                self._disabled = set()
                self._mtime = -1.0
                return set()
            if mtime == self._mtime:
                return set(self._disabled)
            self._mtime = mtime
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                raw = data.get("disabled", []) if isinstance(data, dict) else []
                self._disabled = {str(x) for x in raw}
            except Exception:
                self._disabled = set()
            return set(self._disabled)

    def set_enabled(self, name: str, enabled: bool) -> None:
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        disabled = {str(x) for x in data.get("disabled", [])}
        disabled.discard(name) if enabled else disabled.add(name)
        data["disabled"] = sorted(disabled)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        with self._lock:
            self._mtime = -1.0
            self._checked = 0.0


_ENABLED = _EnabledState()


def is_enabled(name: str) -> bool:
    return name not in _ENABLED.disabled()


def set_enabled(name: str, enabled: bool) -> None:
    _ENABLED.set_enabled(name, enabled)


# ── The scan ──────────────────────────────────────────────────────────────────


def _record_for(cls: type[BaseTool], module_name: str) -> ToolRecord | None:
    spec = getattr(cls, "spec", None)
    if spec is None:
        return None
    name = str(getattr(spec, "name", "") or "").strip()
    rec = ToolRecord(
        name=name or cls.__name__,
        cls=cls,
        module=module_name,
        description=str(getattr(spec, "description", "") or ""),
        requires_approval=bool(getattr(spec, "requires_approval", False)),
        behavior=_norm(getattr(cls, "behavior", None), BEHAVIORS, "BLOCKING"),
        scheduling=_norm(getattr(cls, "scheduling", None), SCHEDULING, "WHEN_IDLE"),
    )
    if not name:
        rec.error = f"{cls.__name__} has a spec with no name"
        return rec
    if not _NAME_RE.match(name):
        rec.error = f"invalid tool name {name!r}"
        return rec
    if inspect.isabstract(cls):
        rec.error = f"{cls.__name__} is abstract"
        return rec
    rec.valid = True
    return rec


def _iter_modules(packages: Iterable[str]) -> Iterable[tuple[str, Any, str]]:
    """Yield ``(module_name, module_or_None, error)`` for every candidate."""
    for pkg_name in packages:
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception as exc:
            yield pkg_name, None, f"{exc}"
            continue
        for info in pkgutil.iter_modules(getattr(pkg, "__path__", [])):
            if info.name.startswith("_") or info.name in _SKIP_MODULES:
                continue
            full = f"{pkg_name}.{info.name}"
            try:
                yield full, importlib.import_module(full), ""
            except Exception as exc:
                yield full, None, f"{type(exc).__name__}: {exc}"


def _iter_plugin_files(directory: Path) -> Iterable[tuple[str, Any, str]]:
    """Same contract as :func:`_iter_modules`, for loose user plugin files."""
    if not directory.is_dir():
        return
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        mod_name = f"jarvis_plugin_{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, path)
            if spec is None or spec.loader is None:
                yield mod_name, None, "could not build import spec"
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            yield mod_name, module, ""
        except Exception as exc:
            yield mod_name, None, f"{type(exc).__name__}: {exc}"


class ToolRegistry:
    """The result of a scan: valid tools, plus everything that went wrong."""

    def __init__(self) -> None:
        self.tools: dict[str, ToolRecord] = {}
        self.records: list[ToolRecord] = []
        self.aliases: dict[str, str] = {}

    # -- lookup ----------------------------------------------------------

    def get(self, name: str) -> BaseTool | None:
        rec = self.record(name)
        if rec is None or not rec.valid or rec.cls is None:
            return None
        if not is_enabled(rec.name):  # re-read per dispatch, no restart needed
            return None
        try:
            return rec.cls()
        except Exception:
            return None

    def record(self, name: str) -> ToolRecord | None:
        rec = self.tools.get(name)
        if rec is not None:
            return rec
        target = self.aliases.get(name)
        return self.tools.get(target) if target else None

    def names(self, include_disabled: bool = False) -> list[str]:
        return sorted(
            n for n in self.tools if include_disabled or is_enabled(n)
        )

    def list_for_ui(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in sorted(self.records, key=lambda r: (not r.valid, r.name))]

    def problems(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self.records if not r.valid]

    # -- construction ----------------------------------------------------

    def add(self, rec: ToolRecord) -> None:
        self.records.append(rec)
        if not rec.valid:
            return
        existing = self.tools.get(rec.name)
        if existing is not None and existing.cls is not rec.cls:
            if existing.module == _BUILTIN_MODULE and rec.module != _BUILTIN_MODULE:
                # An enhanced implementation supersedes the builtin fallback.
                existing.error = f"superseded by {rec.module}"
                self.tools[rec.name] = rec
                return
            if rec.module == _BUILTIN_MODULE and existing.module != _BUILTIN_MODULE:
                rec.error = f"builtin fallback, superseded by {existing.module}"
                return
            rec.valid = False
            rec.error = (
                f"name collision: {rec.name!r} already provided by {existing.module}"
            )
            return
        self.tools[rec.name] = rec

    def alias(self, alias: str, target: str) -> None:
        if target in self.tools:
            self.aliases[alias] = target


_registry: ToolRegistry | None = None
_registry_lock = threading.Lock()


def discover(
    packages: Iterable[str] = ("jarvis.tools",),
    plugin_dir: Path | None = None,
) -> ToolRegistry:
    """Scan for tools. Never raises."""
    reg = ToolRegistry()
    sources = list(_iter_modules(packages))

    if plugin_dir is None:
        try:
            from jarvis.core.config import get_home

            plugin_dir = get_home() / "plugins"
        except Exception:
            plugin_dir = None
    if plugin_dir is not None:
        sources += list(_iter_plugin_files(Path(plugin_dir)))

    for mod_name, module, error in sources:
        if module is None:
            reg.add(
                ToolRecord(
                    name=mod_name.rsplit(".", 1)[-1],
                    module=mod_name,
                    valid=False,
                    error=error or "import failed",
                )
            )
            continue
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, BaseTool) or obj is BaseTool:
                continue
            # Only the module that defines a class registers it, so a tool
            # imported into three other modules is not discovered four times.
            if getattr(obj, "__module__", None) != getattr(module, "__name__", None):
                continue
            rec = _record_for(obj, mod_name)
            if rec is not None:
                reg.add(rec)
    return reg


def get_registry(refresh: bool = False) -> ToolRegistry:
    """Discovery runs once per process; the result is cached."""
    global _registry
    with _registry_lock:
        if _registry is None or refresh:
            _registry = discover()
        return _registry


def format_problems() -> str:
    """Human-readable report of everything discovery had to skip."""
    problems = get_registry().problems()
    if not problems:
        return "All discovered tools loaded cleanly."
    lines = [f"{len(problems)} tool module(s) skipped:"]
    for p in problems:
        lines.append(f"  • {p['module'] or p['name']}: {p['error']}")
    return "\n".join(lines)


def debug_trace() -> str:  # pragma: no cover - diagnostic helper
    return traceback.format_exc()
