"""Built-in tools."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from typing import Any

from jarvis.tools.base import BaseTool, ToolSpec


class FileReadTool(BaseTool):
    spec = ToolSpec(
        name="file_read",
        description="Read a file from disk. Use relative or absolute path.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        },
    )

    def run(self, path: str, **kwargs) -> str:
        p = pathlib.Path(path).expanduser()
        if not p.exists():
            return f"Error: file not found: {path}"
        if p.stat().st_size > 200_000:
            return f"Error: file too large ({p.stat().st_size} bytes). Limit 200KB."
        try:
            return p.read_text(encoding="utf-8", errors="replace")[:10000]
        except Exception as e:
            return f"Error reading {path}: {e}"


class FileWriteTool(BaseTool):
    spec = ToolSpec(
        name="file_write",
        description="Write content to a file.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
        requires_approval=True,
    )

    def run(self, path: str, content: str, **kwargs) -> str:
        p = pathlib.Path(path).expanduser()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} chars to {path}"
        except Exception as e:
            return f"Error writing {path}: {e}"


class ShellTool(BaseTool):
    spec = ToolSpec(
        name="shell",
        description="Execute a shell command. Returns stdout/stderr. Use with care.",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command"},
                "cwd": {"type": "string", "description": "Working directory"},
            },
            "required": ["command"],
        },
        requires_approval=True,
    )

    def run(self, command: str, cwd: str | None = None, **kwargs) -> str:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            out = result.stdout[-5000:] if result.stdout else ""
            err = result.stderr[-2000:] if result.stderr else ""
            return f"Exit {result.returncode}\nSTDOUT:\n{out}\nSTDERR:\n{err}"
        except subprocess.TimeoutExpired:
            return "Error: command timed out after 30s"
        except Exception as e:
            return f"Error: {e}"


class WebSearchTool(BaseTool):
    spec = ToolSpec(
        name="web_search",
        description="Search the web (mock implementation, returns guidance). In production, plug Tavily/DDGS.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )

    def run(self, query: str, **kwargs) -> str:
        # Mock search — in real OpenJarvis this would call Tavily/DDGS
        return (
            f"[MOCK WEB SEARCH for: {query}]\n"
            "To enable real search, set TAVILY_API_KEY and install tavily-python.\n"
            "For now, answer from knowledge cutoff and ask user for more context if needed."
        )


class MemorySearchTool(BaseTool):
    spec = ToolSpec(
        name="memory_search",
        description="Search local memory store for relevant context.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )

    def run(self, query: str, **kwargs) -> str:
        try:
            from jarvis.memory.store import MemoryStore

            store = MemoryStore()
            results = store.search(query, top_k=5)
            if not results:
                return "No relevant memories found."
            return "\n\n".join([f"- {r.content} (score approx)" for r in results])
        except Exception as e:
            return f"Memory search error: {e}"


class MemoryWriteTool(BaseTool):
    spec = ToolSpec(
        name="memory_write",
        description="Write a fact to long-term memory.",
        parameters={
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
    )

    def run(self, content: str, **kwargs) -> str:
        try:
            from jarvis.memory.store import MemoryStore

            store = MemoryStore()
            entry = store.add(content)
            return f"Saved to memory: {entry.id}"
        except Exception as e:
            return f"Memory write error: {e}"


class CalendarTool(BaseTool):
    spec = ToolSpec(
        name="calendar",
        description="List today's mock calendar events. Connect real calendar via jarvis connect.",
        parameters={
            "type": "object",
            "properties": {},
        },
    )

    def run(self, **kwargs) -> str:
        return (
            "[MOCK CALENDAR]\n"
            "09:00 Team standup\n"
            "11:00 Deep work block\n"
            "14:00 Client meeting — prepare brief\n"
            "Connect real Google Calendar with: jarvis connect gdrive"
        )


class GmailTool(BaseTool):
    spec = ToolSpec(
        name="gmail",
        description="Search mock Gmail. Connect real Gmail via jarvis connect.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )

    def run(self, query: str = "", **kwargs) -> str:
        return (
            f"[MOCK GMAIL search: {query}]\n"
            "No real emails — connect Gmail with: jarvis connect gdrive\n"
            "Mock: 3 unread — Project update, Meeting invite, Newsletter"
        )
