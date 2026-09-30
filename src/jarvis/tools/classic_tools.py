"""
tools/classic_tools.py — the classic assistant as one agent tool.

An agent should not need to know that "battery status", "weather in Oslo" and
"tell me a joke" are three different subsystems. It calls ``classic_command``
with whatever the user said and gets back a sentence, exactly as the 2020
voice loop would have answered it.

Discovery picks this module up automatically (see jarvis/tools/discovery.py),
so there is no registry edit to forget.
"""

from __future__ import annotations

from jarvis.classic.router import COMMANDS, ClassicRouter
from jarvis.tools.base import BaseTool, ToolSpec


class ClassicCommandTool(BaseTool):
    spec = ToolSpec(
        name="classic_command",
        description=(
            "Run a classic JARVIS voice-assistant command (ported from "
            "KKshitiz/J.A.R.V.I.S): weather, jokes, notes, screenshots, CPU/RAM/battery "
            "stats, web and Wikipedia/YouTube search, translation, music, image OCR, "
            "power options. Pass the user's phrasing through unchanged, e.g. "
            "'weather in Berlin' or 'take a screenshot'. Send 'help' to list commands."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The spoken or typed command, verbatim.",
                }
            },
            "required": ["command"],
        },
    )

    def __init__(self) -> None:
        # One router per tool instance keeps follow-up questions ("which
        # city, sir?") coherent within a conversation.
        self._router = ClassicRouter()

    def run(self, command: str = "", **kwargs) -> str:
        if not command.strip():
            return "Usage: classic_command(command='weather in Berlin'). Send 'help' for the full list."
        reply = self._router.handle(command)
        if reply.confirm_token:
            return (
                f"{reply.speech}\n[awaiting human confirmation: token {reply.confirm_token}]"
            )
        return reply.speech


class ClassicCommandListTool(BaseTool):
    spec = ToolSpec(
        name="classic_commands",
        description="List the classic JARVIS commands available, with example phrasings.",
        parameters={"type": "object", "properties": {}},
    )

    def run(self, **kwargs) -> str:
        return "\n".join(f"{c['intent']}: \"{c['example']}\" — {c['description']}" for c in COMMANDS)
