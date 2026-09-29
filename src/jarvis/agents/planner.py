"""
agents/planner.py — turn a goal into a short, validated, executable plan.

WHY A PLANNER AT ALL
    A ReAct loop decides one step at a time, which is fine for "what's the
    weather" and bad for "research X, write it up, and save it to my desktop":
    the model re-derives the whole task on every turn, and nothing can show the
    user what is about to happen before it happens.

THE TOOL CATALOGUE IS GENERATED, NOT WRITTEN
    The obvious way to build the prompt is to type the tool list into it. That
    is what the assistants this design came from do, and their prompt has
    already drifted out of sync with their code — it documents parameters that
    no longer exist and omits tools that do.

    Here the catalogue is rendered from the live ``ToolSpec`` JSON schemas
    (:func:`tool_catalogue`), so a tool's parameters can never be described
    wrongly and a newly discovered tool is plannable the moment it is added.
    Plans are then validated against those same specs before anything runs:
    unknown tools and unknown or missing required arguments are rejected with
    a specific message the model can repair.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from jarvis.core.types import Message, Role
from jarvis.tools.registry import get_tool, list_tools, tool_record

MAX_STEPS = 6


@dataclass
class Step:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    purpose: str = ""

    def describe(self) -> str:
        args = ", ".join(f"{k}={v!r}" for k, v in self.arguments.items())
        return f"{self.tool}({args})" + (f" — {self.purpose}" if self.purpose else "")

    def to_dict(self) -> dict[str, Any]:
        return {"tool": self.tool, "arguments": self.arguments, "purpose": self.purpose}


@dataclass
class Plan:
    goal: str
    steps: list[Step] = field(default_factory=list)
    reasoning: str = ""
    errors: list[str] = field(default_factory=list)
    raw: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.steps) and not self.errors

    @property
    def needs_approval(self) -> bool:
        """True if any step touches a tool marked ``requires_approval``."""
        for step in self.steps:
            record = tool_record(step.tool)
            if record is not None and record.requires_approval:
                return True
        return False

    def describe(self) -> str:
        if not self.steps:
            return "No plan."
        lines = [f"Plan for: {self.goal}"]
        lines += [f"  {i}. {s.describe()}" for i, s in enumerate(self.steps, 1)]
        if self.errors:
            lines.append(f"  (rejected: {'; '.join(self.errors)})")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "reasoning": self.reasoning,
            "errors": self.errors,
            "needs_approval": self.needs_approval,
        }


# ── The catalogue ─────────────────────────────────────────────────────────────


def tool_catalogue(names: list[str] | None = None) -> str:
    """Render the live tool specs as prompt text. Never hand-written."""
    names = names if names is not None else list_tools()
    blocks: list[str] = []
    for name in sorted(names):
        record = tool_record(name)
        if record is None or not record.valid:
            continue
        tool = get_tool(name)
        if tool is None:
            continue
        spec = tool.spec
        schema = spec.parameters or {}
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
        required = set(schema.get("required", []) if isinstance(schema, dict) else [])

        lines = [f"{spec.name}", f"  {spec.description.strip()}"]
        if record.requires_approval:
            lines.append("  [needs the user's confirmation before it runs]")
        for arg, meta in properties.items():
            meta = meta if isinstance(meta, dict) else {}
            bits = [str(meta.get("type", "any"))]
            if arg in required:
                bits.append("required")
            if meta.get("enum"):
                bits.append("one of: " + ", ".join(str(e) for e in meta["enum"]))
            desc = str(meta.get("description", "")).strip()
            lines.append(f"    - {arg} ({', '.join(bits)})" + (f": {desc}" if desc else ""))
        if not properties:
            lines.append("    - (no arguments)")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


_PROMPT = """You are the planning module of JARVIS.

Break the user's goal into the SHORTEST sequence of tool calls that achieves
it. Rules:

- Use ONLY the tools listed below, with ONLY the arguments they declare.
- Maximum {max_steps} steps. Fewer is better. One step is fine.
- Each step must stand alone: do NOT write parameters that reference the
  output of an earlier step. If a step needs an earlier result, say so in its
  "purpose" and let the executor pass it through.
- If the goal needs no tools at all, return an empty "steps" list and explain
  in "reasoning".

AVAILABLE TOOLS
{catalogue}

Return ONLY valid JSON, no prose and no code fences:
{{"reasoning": "one or two sentences",
  "steps": [{{"tool": "tool_name", "arguments": {{}}, "purpose": "why this step"}}]}}"""


def _extract_json(text: str) -> dict[str, Any] | None:
    cleaned = re.sub(r"^```(?:json)?|```$", "", str(text).strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


# ── Validation ────────────────────────────────────────────────────────────────


def validate_step(tool_name: str, arguments: dict[str, Any]) -> tuple[Step | None, str]:
    """Check one step against the live spec. Returns ``(step, error)``."""
    record = tool_record(tool_name)
    if record is None:
        return None, f"unknown tool {tool_name!r}"
    if not record.valid:
        return None, f"tool {tool_name!r} failed to load: {record.error}"
    tool = get_tool(record.name)
    if tool is None:
        return None, f"tool {tool_name!r} is disabled"

    schema = tool.spec.parameters or {}
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = schema.get("required", []) if isinstance(schema, dict) else []
    arguments = arguments if isinstance(arguments, dict) else {}

    if properties:
        unknown = [k for k in arguments if k not in properties]
        if unknown:
            return None, (
                f"{tool_name} has no argument(s) {', '.join(sorted(unknown))}; "
                f"valid: {', '.join(sorted(properties)) or 'none'}"
            )
    missing = [k for k in required if k not in arguments]
    if missing:
        return None, f"{tool_name} is missing required argument(s) {', '.join(missing)}"
    return Step(tool=record.name, arguments=arguments), ""


def plan(
    goal: str,
    engine: Any = None,
    tools: list[str] | None = None,
    max_steps: int = MAX_STEPS,
) -> Plan:
    """Ask the model for a plan, then validate every step against the specs."""
    result = Plan(goal=goal)

    if engine is None:
        try:
            from jarvis.engine.ladder import SMART, for_purpose

            engine = for_purpose(SMART)
        except Exception as exc:
            result.errors.append(f"no planning engine available: {exc}")
            return result

    prompt = _PROMPT.format(max_steps=max_steps, catalogue=tool_catalogue(tools))
    try:
        response = engine.generate(
            [
                Message(role=Role.SYSTEM, content=prompt),
                Message(role=Role.USER, content=f"GOAL: {goal}"),
            ]
        )
        result.raw = response.content
    except Exception as exc:
        result.errors.append(f"planner call failed: {exc}")
        return result

    parsed = _extract_json(result.raw)
    if parsed is None:
        result.errors.append("planner did not return valid JSON")
        return result

    result.reasoning = str(parsed.get("reasoning", ""))[:500]
    raw_steps = parsed.get("steps", [])
    if not isinstance(raw_steps, list):
        result.errors.append("'steps' was not a list")
        return result

    for index, raw in enumerate(raw_steps[:max_steps], 1):
        if not isinstance(raw, dict):
            result.errors.append(f"step {index} was not an object")
            continue
        step, error = validate_step(str(raw.get("tool", "")), raw.get("arguments", {}))
        if step is None:
            result.errors.append(f"step {index}: {error}")
            continue
        step.purpose = str(raw.get("purpose", ""))[:200]
        result.steps.append(step)

    return result
