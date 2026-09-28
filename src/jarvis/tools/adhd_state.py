"""ADHD support-state assessment tools.

This module intentionally does **not** diagnose ADHD or assign a medical
severity.  It turns a short daily check-in into an operational support mode
that JARVIS can use for planning, focus length, and guardrails.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis.core.config import get_home
from jarvis.tools.base import BaseTool, ToolSpec


VALID_MEDICATION = {"unknown", "not_applicable", "taken", "skipped"}


def _adhd_dir() -> Path:
    path = get_home() / "adhd"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clamp_int(value: Any, minimum: int = 1, maximum: int = 10, default: int = 5) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _clamp_float(value: Any, minimum: float = 0.0, maximum: float = 24.0, default: float = 7.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def classify_support_state(
    energy: int,
    focus: int,
    stress: int,
    sleep_hours: float,
    mood: str = "",
    medication: str = "unknown",
) -> dict[str, Any]:
    """Classify the user's current support state.

    The returned ``support_load`` is an operational score (0-10) for how much
    scaffolding the day needs. It is not an ADHD diagnosis or clinical rating.
    """

    energy = _clamp_int(energy)
    focus = _clamp_int(focus)
    stress = _clamp_int(stress)
    sleep_hours = _clamp_float(sleep_hours)
    medication = medication if medication in VALID_MEDICATION else "unknown"
    mood_l = (mood or "").lower()

    mood_load = 0.0
    if any(word in mood_l for word in ["anxious", "panic", "overwhelm", "stressed", "angry"]):
        mood_load += 1.0
    if any(word in mood_l for word in ["flat", "sad", "tired", "numb", "burnout"]):
        mood_load += 0.7
    if any(word in mood_l for word in ["buzzing", "restless", "wired"]):
        mood_load += 0.5

    sleep_penalty = max(0.0, 7.0 - sleep_hours) * 0.55
    medication_penalty = 0.8 if medication == "skipped" else 0.0

    support_load = (
        (10 - energy) * 0.22
        + (10 - focus) * 0.26
        + stress * 0.28
        + sleep_penalty
        + mood_load
        + medication_penalty
    )
    support_load = max(0.0, min(10.0, support_load))

    if stress >= 8 or "overwhelm" in mood_l or "panic" in mood_l:
        mode = "Overwhelm SOS"
        icon = "🆘"
        focus_pattern = "2-minute grounding → one tiny next action"
        actions = [
            "Feet on floor, four slow breaths, name three things you can see.",
            "Shrink the world: pick one action that makes today 10% better.",
            "If you cannot choose, start with water, then write one next step.",
        ]
    elif energy <= 3 and focus <= 3:
        mode = "Low Battery"
        icon = "🔋"
        focus_pattern = "10-15 minute gentle sprints, high recovery"
        actions = [
            "Do not force hard MITs yet; protect energy first.",
            "Use tiny admin, hydration, food, light movement, or rest.",
            "Ask JARVIS to break one task into a 2-minute start.",
        ]
    elif energy <= 3 and focus >= 6:
        mode = "Wired but Tired"
        icon = "🧠"
        focus_pattern = "Planning and organizing, not heavy execution"
        actions = [
            "Brain dump, sort notes, plan tomorrow, or do low-physical tasks.",
            "Avoid starting a large execution task unless it is truly urgent.",
            "Set a shutdown alarm; tired focus can become a rabbit hole.",
        ]
    elif energy >= 7 and focus <= 4:
        mode = "Buzzing / Restless"
        icon = "⚡"
        focus_pattern = "Move first → 15 minute physical or voice-led sprint"
        actions = [
            "Walk, stretch, or do a physical reset before desk work.",
            "Use voice capture while moving so thoughts do not vanish.",
            "Start with visible tasks: tidy, errands, filing, setup.",
        ]
    elif energy >= 7 and focus >= 7:
        mode = "Hyperfocus Risk"
        icon = "🚀"
        focus_pattern = "45 minute block with hard break alarms"
        actions = [
            "Use the momentum on MIT 1 now.",
            "Set alarms for water, food, bathroom, and stopping.",
            "Define done before starting so hyperfocus has an exit ramp.",
        ]
    elif focus <= 4 and stress >= 6:
        mode = "Scattered Guardrails"
        icon = "🧩"
        focus_pattern = "15-25 minute block with external structure"
        actions = [
            "Use a body double or visible timer.",
            "Park distractions in a list instead of chasing them.",
            "Keep only one tab/app/task open if possible.",
        ]
    else:
        mode = "Steady"
        icon = "⚖️"
        focus_pattern = "25/5 Pomodoro works well"
        actions = [
            "Pick MIT 1 and work for one Pomodoro.",
            "Keep the day capped at three priorities.",
            "Log one tiny win when the block ends.",
        ]

    if support_load >= 7.5:
        support_level = "High support needed today"
    elif support_load >= 5.0:
        support_level = "Moderate support needed today"
    else:
        support_level = "Light support is enough today"

    return {
        "mode": mode,
        "icon": icon,
        "support_load": round(support_load, 1),
        "support_level": support_level,
        "focus_pattern": focus_pattern,
        "actions": actions,
    }


class ADHDStateTool(BaseTool):
    spec = ToolSpec(
        name="adhd_state",
        description=(
            "Daily ADHD support-state check-in. Not a diagnosis: estimates the current "
            "support mode from energy, focus, stress, sleep, mood, and optional medication status."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["assess", "status", "profile"],
                    "description": "assess daily state, show status/history, or save onboarding profile",
                    "default": "assess",
                },
                "energy": {"type": "integer", "description": "Energy 1-10", "default": 5},
                "focus": {"type": "integer", "description": "Focus 1-10", "default": 5},
                "stress": {"type": "integer", "description": "Stress/overwhelm 1-10", "default": 5},
                "sleep_hours": {"type": "number", "description": "Last night's sleep hours", "default": 7},
                "mood": {"type": "string", "description": "Mood words such as calm, anxious, buzzing", "default": ""},
                "medication": {
                    "type": "string",
                    "enum": ["unknown", "not_applicable", "taken", "skipped"],
                    "description": "Optional medication state; use not_applicable if none",
                    "default": "unknown",
                },
                "notes": {"type": "string", "description": "Optional note", "default": ""},
                "preferred_focus": {"type": "string", "description": "Onboarding: preferred focus length/pattern", "default": ""},
                "support_needs": {"type": "string", "description": "Onboarding: what support helps you", "default": ""},
            },
            "required": [],
        },
    )

    def run(
        self,
        action: str = "assess",
        energy: int = 5,
        focus: int = 5,
        stress: int = 5,
        sleep_hours: float = 7,
        mood: str = "",
        medication: str = "unknown",
        notes: str = "",
        preferred_focus: str = "",
        support_needs: str = "",
        **kwargs: Any,
    ) -> str:
        action = (action or "assess").lower()
        if action == "status":
            return self._status()
        if action == "profile":
            return self._profile(preferred_focus=preferred_focus, support_needs=support_needs, notes=notes)
        return self._assess(
            energy=energy,
            focus=focus,
            stress=stress,
            sleep_hours=sleep_hours,
            mood=mood,
            medication=medication,
            notes=notes,
        )

    def _assess(self, energy: int, focus: int, stress: int, sleep_hours: float, mood: str, medication: str, notes: str) -> str:
        energy = _clamp_int(energy)
        focus = _clamp_int(focus)
        stress = _clamp_int(stress)
        sleep_hours = _clamp_float(sleep_hours)
        medication = medication if medication in VALID_MEDICATION else "unknown"
        state = classify_support_state(energy, focus, stress, sleep_hours, mood, medication)

        entry = {
            "time": datetime.now().isoformat(),
            "energy": energy,
            "focus": focus,
            "stress": stress,
            "sleep_hours": sleep_hours,
            "mood": mood,
            "medication": medication,
            "notes": notes,
            **state,
        }
        log_path = _adhd_dir() / "state_log.json"
        logs: list[dict[str, Any]] = []
        if log_path.exists():
            try:
                parsed = json.loads(log_path.read_text(encoding="utf-8"))
                if isinstance(parsed, list):
                    logs = parsed
            except Exception:
                logs = []
        logs.append(entry)
        log_path.write_text(json.dumps(logs[-180:], indent=2), encoding="utf-8")

        out = [
            f"{state['icon']} **ADHD Support State — {state['mode']}**",
            "",
            "This is **not a medical ADHD diagnosis or severity score**. It is today's operating mode so JARVIS can choose the right scaffolding.",
            "",
            f"Energy {energy}/10 | Focus {focus}/10 | Stress {stress}/10 | Sleep {sleep_hours:g}h | Mood: {mood or 'not set'}",
            f"Support load: {state['support_load']}/10 — {state['support_level']}",
            f"Recommended focus pattern: {state['focus_pattern']}",
            "",
            "**JARVIS should do now:**",
        ]
        out.extend(f"  • {item}" for item in state["actions"])
        if notes:
            out.extend(["", f"Note saved: {notes}"])
        out.extend([
            "",
            "Next: say `plan my day` or set your three MITs. I will use this state to keep the plan humane, Sir.",
        ])
        return "\n".join(out)

    def _status(self) -> str:
        log_path = _adhd_dir() / "state_log.json"
        if not log_path.exists():
            return (
                "No ADHD support-state checks logged yet, Sir. "
                "Run `jarvis adhd-state --energy 5 --focus 5 --stress 5` or use the HUD daily check-in."
            )
        try:
            logs = json.loads(log_path.read_text(encoding="utf-8"))
            if not isinstance(logs, list) or not logs:
                raise ValueError("empty")
        except Exception:
            return "ADHD state log exists but could not be read. We can start fresh with a new check-in."

        latest = logs[-1]
        recent = logs[-7:]
        avg_load = sum(float(item.get("support_load", 0)) for item in recent) / len(recent)
        mode_counts: dict[str, int] = {}
        for item in recent:
            mode = str(item.get("mode", "Unknown"))
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
        common_mode = max(mode_counts, key=mode_counts.get)

        out = [
            "🧭 **ADHD Support-State Status**",
            "",
            f"Latest: {latest.get('icon','')} {latest.get('mode','Unknown')} at {str(latest.get('time',''))[:16].replace('T', ' ')}",
            f"Latest support load: {latest.get('support_load', 'n/a')}/10 — {latest.get('support_level', '')}",
            f"7-check average load: {avg_load:.1f}/10",
            f"Most common recent mode: {common_mode}",
            "",
            "Recent checks:",
        ]
        for item in recent[-5:]:
            out.append(
                f"  • {str(item.get('time',''))[:10]} — {item.get('icon','')} {item.get('mode','Unknown')} "
                f"(E{item.get('energy','?')} F{item.get('focus','?')} S{item.get('stress','?')})"
            )
        out.extend([
            "",
            "Again: this is an operating-mode log, not a clinical rating. The goal is better support, not a label.",
        ])
        return "\n".join(out)

    def _profile(self, preferred_focus: str = "", support_needs: str = "", notes: str = "") -> str:
        profile_path = _adhd_dir() / "profile.json"
        profile = {
            "updated": datetime.now().isoformat(),
            "preferred_focus": preferred_focus,
            "support_needs": support_needs,
            "notes": notes,
            "medical_disclaimer": "JARVIS does not diagnose ADHD; this profile stores user preferences for support.",
        }
        if profile_path.exists():
            try:
                old = json.loads(profile_path.read_text(encoding="utf-8"))
                if isinstance(old, dict):
                    old.update({k: v for k, v in profile.items() if v or k in ("updated", "medical_disclaimer")})
                    profile = old
            except Exception:
                pass
        profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return (
            "ADHD support profile saved, Sir. I will use it for planning and focus guardrails.\n\n"
            f"Preferred focus: {profile.get('preferred_focus') or 'not set'}\n"
            f"Support needs: {profile.get('support_needs') or 'not set'}\n"
            "\nNoted: this is preference data, not a diagnosis."
        )
