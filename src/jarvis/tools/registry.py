"""Tool registry — thin facade over directory-based discovery.

This file used to be a hand-maintained import list: ~20 ``try/except
ImportError`` blocks and a dict literal naming every tool class twice. Adding
a tool meant editing it, and forgetting to meant the tool silently did not
exist.

Now :mod:`jarvis.tools.discovery` scans the package and any user plugins in
``~/.jarvis/plugins/``; this module only keeps the public API stable
(:func:`get_tool`, :func:`list_tools`, :func:`get_tools`, ``REGISTRY``) and
declares the historical aliases.
"""

from __future__ import annotations

from typing import Any
from collections.abc import Mapping

from jarvis.tools.base import BaseTool
from jarvis.tools.discovery import (
    format_problems,
    get_registry,
    is_enabled,
    set_enabled,
)

#: Extra names that must keep resolving, for callers and agent presets that
#: were written against the old hand-maintained table.
ALIASES: dict[str, str] = {
    "code_exec": "shell",
    "career": "career_os",
    "online_status": "network_status",
    "search": "web_search",
    "memory": "memory_search",
}


def _registry():
    reg = get_registry()
    for alias, target in ALIASES.items():
        if alias not in reg.tools:
            reg.alias(alias, target)
    return reg


class _RegistryView(Mapping[str, type]):
    """Back-compat: ``REGISTRY`` used to be a ``dict[str, type[BaseTool]]``.

    Kept as a live read-only view so existing ``REGISTRY[name]`` /
    ``name in REGISTRY`` / ``REGISTRY.keys()`` callers keep working, but it now
    reflects discovery instead of a frozen literal.
    """

    def _classes(self) -> dict[str, type]:
        reg = _registry()
        out = {name: rec.cls for name, rec in reg.tools.items() if rec.cls}
        for alias, target in reg.aliases.items():
            rec = reg.tools.get(target)
            if rec and rec.cls:
                out[alias] = rec.cls
        return out

    def __getitem__(self, key: str) -> type:
        return self._classes()[key]

    def __iter__(self):
        return iter(self._classes())

    def __len__(self) -> int:
        return len(self._classes())

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        return self._classes().get(key, default)

    def update(self, *_args, **_kwargs) -> None:
        raise TypeError(
            "REGISTRY is discovered, not assembled. Define a BaseTool subclass "
            "in jarvis/tools/ or drop a module in ~/.jarvis/plugins/."
        )


REGISTRY = _RegistryView()


def get_tool(name: str) -> BaseTool | None:
    """Instantiate a tool by name, honouring the enable/disable file."""
    return _registry().get(name)


def list_tools(include_disabled: bool = False) -> list[str]:
    return _registry().names(include_disabled=include_disabled)


def get_tools(names: list[str]) -> list[BaseTool]:
    tools: list[BaseTool] = []
    for n in names:
        t = get_tool(n)
        if t:
            tools.append(t)
    return tools


def tool_record(name: str):
    """Full metadata (behavior, scheduling, approval, load error) for one tool."""
    return _registry().record(name)


def list_tool_details() -> list[dict[str, Any]]:
    """Everything discovery found, valid or not — what a settings UI renders."""
    return _registry().list_for_ui()


def refresh() -> None:
    """Re-run discovery (after installing a plugin, say)."""
    get_registry(refresh=True)


__all__ = [
    "ALIASES",
    "REGISTRY",
    "format_problems",
    "get_tool",
    "get_tools",
    "is_enabled",
    "list_tool_details",
    "list_tools",
    "refresh",
    "set_enabled",
    "tool_record",
]
