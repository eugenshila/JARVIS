"""Tools for looking at the screen or through the camera.

The capture itself lives in :mod:`jarvis.core.capture` (budget, consent,
pruning); this only wires it to the tool registry and hands the resulting JPEG
to whatever vision model is configured.
"""

from __future__ import annotations

from jarvis.core import capture as capture_core
from jarvis.tools.base import BaseTool, ToolSpec


def _describe(image_path: str, prompt: str) -> str:
    try:
        from jarvis.tools.vision_tool import VisionTool
    except ImportError:
        return ""
    try:
        return VisionTool().run(image_path=image_path, prompt=prompt)
    except Exception as exc:
        return f"(captured, but could not analyse it: {exc})"


class ScreenCaptureTool(BaseTool):
    spec = ToolSpec(
        name="screen_capture",
        description=(
            "Look at what is currently on the user's screen and answer a question "
            "about it. Use when the user says 'what's on my screen', 'what does this "
            "error say', 'look at this', or refers to something visible that they "
            "have not pasted. Requires the user to have enabled screen capture."
        ),
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "What to look for",
                    "default": "Describe what is on the screen.",
                },
                "monitor": {
                    "type": "integer",
                    "description": "Monitor index; 0 means all monitors",
                    "default": 0,
                },
                "analyse": {
                    "type": "boolean",
                    "description": "Send the capture to a vision model (default true)",
                    "default": True,
                },
            },
            "required": [],
        },
        requires_approval=True,
    )

    def run(
        self,
        question: str = "Describe what is on the screen.",
        monitor: int = 0,
        analyse: bool = True,
        **kwargs,
    ) -> str:
        try:
            shot = capture_core.capture_screen(monitor=int(monitor))
        except capture_core.CaptureError as exc:
            return f"Error: {exc}"
        if not analyse:
            return shot.describe()
        description = _describe(str(shot.path), question)
        return description or f"{shot.describe()} (no vision model available to read it)"


class CameraCaptureTool(BaseTool):
    spec = ToolSpec(
        name="camera_capture",
        description=(
            "Take a single photo with the webcam and describe it. Use when the user "
            "asks 'what do you see', 'look at me', or holds something up to the "
            "camera. Requires the user to have enabled camera capture."
        ),
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "What to look for",
                    "default": "Describe what you see.",
                },
                "device": {"type": "integer", "description": "Camera index", "default": 0},
            },
            "required": [],
        },
        requires_approval=True,
    )

    def run(self, question: str = "Describe what you see.", device: int = 0, **kwargs) -> str:
        try:
            shot = capture_core.capture_camera(device=int(device))
        except capture_core.CaptureError as exc:
            return f"Error: {exc}"
        description = _describe(str(shot.path), question)
        return description or f"{shot.describe()} (no vision model available to read it)"


class CaptureSettingsTool(BaseTool):
    spec = ToolSpec(
        name="capture_settings",
        description=(
            "Report or change whether JARVIS may capture the screen and camera, and "
            "delete stored captures. Use when the user asks about privacy, or says "
            "'stop looking at my screen' / 'you can see my screen now'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "enable", "disable", "purge"],
                    "default": "status",
                }
            },
            "required": [],
        },
    )

    def run(self, action: str = "status", **kwargs) -> str:
        action = str(action).strip().lower()
        if action == "enable":
            capture_core.set_consent(True)
            return "Screen and camera capture enabled for this session, sir."
        if action == "disable":
            capture_core.set_consent(False)
            return "Capture disabled, sir. I cannot see your screen or camera."
        if action == "purge":
            removed = capture_core.prune(keep=0)
            return f"Deleted {removed} stored capture(s)."

        state = capture_core.status()
        return (
            f"Capture consent: {'granted' if state['consent'] else 'OFF'}\n"
            f"  screen available: {state['screen_available']}\n"
            f"  camera available: {state['camera_available']}\n"
            f"  budget: {state['budget']}\n"
            f"  stored captures: {state['stored']} in {state['captures_dir']}"
        )
