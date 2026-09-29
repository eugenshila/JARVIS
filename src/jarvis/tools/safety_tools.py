"""Tools that expose the undo stack and the confirmation gate to the model.

The model can *undo* (that is the whole point — "undo" has to be sayable) and
it can *see* what is waiting for confirmation. It deliberately cannot resolve a
confirmation: only the interface can, via :func:`jarvis.core.confirm.resolve`.
"""

from __future__ import annotations

from jarvis.core import confirm as confirm_gate
from jarvis.core import undo as undo_stack
from jarvis.tools.base import BaseTool, ToolSpec


class UndoTool(BaseTool):
    """Reverse the last reversible action, or describe what can be reversed."""

    spec = ToolSpec(
        name="undo",
        description=(
            "Undo the most recent reversible action JARVIS performed (file write, "
            "setting change, and so on), or list what can still be undone. Use when "
            "the user says 'undo', 'revert that', 'put it back', or 'no, not that'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["undo", "list"],
                    "description": "'undo' reverses the last action; 'list' only reports.",
                    "default": "undo",
                }
            },
            "required": [],
        },
    )

    def run(self, action: str = "undo", **kwargs) -> str:
        if str(action).strip().lower() == "list":
            entries = undo_stack.history()
            if not entries:
                return "Nothing is currently undoable, sir."
            lines = [f"{len(entries)} reversible action(s), most recent first:"]
            lines += [f"  {i}. {e['label']}" for i, e in enumerate(entries, 1)]
            return "\n".join(lines)
        return undo_stack.undo_last()


class PendingConfirmationsTool(BaseTool):
    """Report what is waiting on a human CONFIRM."""

    spec = ToolSpec(
        name="pending_confirmations",
        description=(
            "List the irreversible actions waiting for the user to press CONFIRM. "
            "Use when the user asks 'what are you waiting for?' or 'did that run?'. "
            "This tool cannot approve anything — only the user can."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
    )

    def run(self, **kwargs) -> str:
        items = confirm_gate.pending()
        if not items:
            return "Nothing is waiting on your confirmation, sir."
        lines = [f"{len(items)} action(s) awaiting your confirmation:"]
        for item in items:
            lines.append(
                f"  • {item['title']} — {item['detail']} "
                f"(expires in {int(item['expires_in'])}s)"
            )
        lines.append("Press CONFIRM or CANCEL in the interface.")
        return "\n".join(lines)
