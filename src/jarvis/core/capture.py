"""
core/capture.py — screen and camera grabs, on a strict byte budget.

THE BUDGET IS THE WHOLE DESIGN
    A raw 4K screenshot is ~8 MB of PNG. Base64-encoded into a request body
    that is ~11 MB, and a vision model will spend several seconds just
    receiving it — for a question like "what error is on my screen?" that a
    640x360 JPEG answers just as well. So every capture is downscaled to fit
    :data:`MAX_WIDTH` x :data:`MAX_HEIGHT` and re-encoded as JPEG at
    :data:`JPEG_QUALITY` before it goes anywhere. Typical result: 30-60 KB.

CONSENT IS EXPLICIT AND OFF BY DEFAULT
    Reading the screen means reading whatever happens to be on it: password
    managers, private messages, someone else's data. That is not something to
    enable implicitly because a model asked for it. Capture therefore requires
    ``JARVIS_ALLOW_CAPTURE=1`` (or a call to :func:`set_consent`), and every
    capture is written to ``~/.jarvis/captures`` so the user can see exactly
    what was taken and delete it.

DEPENDENCIES ARE OPTIONAL
    ``mss`` for the screen, ``opencv-python`` for the camera, ``pillow`` to
    downscale. All imported inside the functions that need them, all reported
    with an install hint when missing, none of them required to import this
    module.
"""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from pathlib import Path

#: Downscale target. 640x360 is enough for text on a screen to stay legible
#: while keeping the payload around 40 KB.
MAX_WIDTH = 640
MAX_HEIGHT = 360
JPEG_QUALITY = 55

#: Keep only the most recent grabs; a capture history is a privacy liability.
KEEP_LAST = 10

_consent_override: bool | None = None


class CaptureError(RuntimeError):
    """Capture could not happen — missing dependency, no consent, no device."""


@dataclass
class Capture:
    path: Path
    width: int
    height: int
    bytes_written: int
    source: str

    def as_base64(self) -> str:
        return base64.b64encode(self.path.read_bytes()).decode("ascii")

    def describe(self) -> str:
        kb = self.bytes_written / 1024
        return f"{self.source} capture {self.width}x{self.height}, {kb:.0f} KB -> {self.path}"


# ── consent ───────────────────────────────────────────────────────────────────


def set_consent(allowed: bool | None) -> None:
    """Grant or revoke capture permission for this process (None = use env)."""
    global _consent_override
    _consent_override = allowed


def has_consent() -> bool:
    if _consent_override is not None:
        return _consent_override
    return os.environ.get("JARVIS_ALLOW_CAPTURE", "").strip().lower() in ("1", "true", "yes", "on")


def _require_consent(kind: str) -> None:
    if not has_consent():
        raise CaptureError(
            f"{kind} capture is off. Reading your {kind} can expose passwords and private "
            "messages, so it is disabled until you turn it on: set JARVIS_ALLOW_CAPTURE=1 "
            "or run `jarvis capture --enable`."
        )


# ── encoding ──────────────────────────────────────────────────────────────────


def _downscale_and_save(image, destination: Path) -> tuple[int, int, int]:
    """Fit within the budget and write JPEG. ``image`` is a PIL Image."""
    image = image.convert("RGB")
    image.thumbnail((MAX_WIDTH, MAX_HEIGHT))
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return image.width, image.height, destination.stat().st_size


def _pillow():
    try:
        from PIL import Image  # type: ignore

        return Image
    except ImportError as exc:
        raise CaptureError("Capture needs pillow: pip install pillow") from exc


def _destination(prefix: str) -> Path:
    from jarvis.core.paths import captures_dir

    return captures_dir() / f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}.jpg"


def prune(keep: int = KEEP_LAST) -> int:
    """Delete all but the newest ``keep`` captures. Returns how many went."""
    from jarvis.core.paths import captures_dir

    files = sorted(captures_dir().glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0
    for stale in files[keep:]:
        try:
            stale.unlink()
            removed += 1
        except OSError:
            pass
    return removed


# ── the two sources ───────────────────────────────────────────────────────────


def capture_screen(monitor: int = 0) -> Capture:
    """Grab the screen (``monitor=0`` means all of them combined)."""
    _require_consent("screen")
    Image = _pillow()
    try:
        import mss  # type: ignore
    except ImportError as exc:
        raise CaptureError("Screen capture needs mss: pip install mss") from exc

    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            index = monitor if 0 <= monitor < len(monitors) else 0
            raw = sct.grab(monitors[index])
            image = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    except CaptureError:
        raise
    except Exception as exc:
        raise CaptureError(f"Could not read the screen: {exc}") from exc

    destination = _destination("screen")
    width, height, size = _downscale_and_save(image, destination)
    prune()
    return Capture(destination, width, height, size, "screen")


def capture_camera(device: int = 0, warmup_frames: int = 3) -> Capture:
    """Grab one frame from a webcam, then release the device immediately."""
    _require_consent("camera")
    Image = _pillow()
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise CaptureError("Camera capture needs opencv-python: pip install opencv-python") from exc

    cam = cv2.VideoCapture(device)
    try:
        if not cam.isOpened():
            raise CaptureError(f"No camera at index {device}.")
        frame = None
        # The first frames from most webcams are black or badly exposed while
        # auto-gain settles, so take a few and keep the last.
        for _ in range(max(1, warmup_frames)):
            ok, candidate = cam.read()
            if ok:
                frame = candidate
        if frame is None:
            raise CaptureError("Camera opened but returned no frame.")
        image = Image.fromarray(frame[:, :, ::-1])  # BGR -> RGB
    finally:
        try:
            cam.release()  # never hold the webcam light on after we are done
        except Exception:
            pass

    destination = _destination("camera")
    width, height, size = _downscale_and_save(image, destination)
    prune()
    return Capture(destination, width, height, size, "camera")


def status() -> dict[str, object]:
    """What is possible on this machine right now."""

    def _installed(name: str) -> bool:
        import importlib.util

        try:
            return importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            return False

    from jarvis.core.paths import captures_dir

    return {
        "consent": has_consent(),
        "screen_available": _installed("mss") and _installed("PIL"),
        "camera_available": _installed("cv2") and _installed("PIL"),
        "budget": f"{MAX_WIDTH}x{MAX_HEIGHT} JPEG q{JPEG_QUALITY}",
        "captures_dir": str(captures_dir()),
        "stored": len(list(captures_dir().glob("*.jpg"))),
    }
