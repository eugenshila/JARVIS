"""
Screen & webcam capture for JARVIS vision.

Provides the two capture entry points main.py uses — `_capture_screen()` and
`_capture_camera()` — plus their helpers (compression, camera auto-detection,
config access). main.py grabs a frame here on demand, then injects it into the
main Gemini Live session; there is no separate vision session here.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np

# ── Lazy imports for cv2 / mss / PIL ──────────────────────────────────────────
# main.py imports this module unconditionally at startup (it's where
# _capture_screen()/_capture_camera() live), so a top-level `import cv2` used
# to load OpenCV's native libraries into every JARVIS process on every launch
# — a real, measurable chunk of RAM paid for even in sessions that never touch
# the camera or screen share. Deferring to first actual use means vision
# support still "just works" (nothing else in the app needs to know these are
# lazy), but the cost is only paid by sessions that use it.
_cv2_mod: "object | None" = False   # False = not attempted yet, None = unavailable
_mss_mod: "object | None" = False
_pil_mod: "object | None" = False


def _cv2():
    global _cv2_mod
    if _cv2_mod is False:
        try:
            import cv2 as _cv2_import
            _cv2_mod = _cv2_import
        except ImportError:
            _cv2_mod = None
    return _cv2_mod


def _mss():
    global _mss_mod
    if _mss_mod is False:
        try:
            import mss as _mss_import
            import mss.tools  # noqa: F401 — attaches .tools to the mss module
            _mss_mod = _mss_import
        except ImportError:
            _mss_mod = None
    return _mss_mod


def _pil_image():
    global _pil_mod
    if _pil_mod is False:
        try:
            import PIL.Image as _pil_import
            _pil_mod = _pil_import
        except ImportError:
            _pil_mod = None
    return _pil_mod


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE        = _base_dir()
_CONFIG_PATH = _BASE / "config" / "api_keys.json"


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_config_key(key: str, value) -> None:
    try:
        cfg = _load_config()
        cfg[key] = value
        _CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"[Vision] ⚠️  Could not save config key '{key}': {e}")


def _get_os() -> str:
    return _load_config().get("os_system", "windows").lower()


_IMG_MAX_W = 1280
_IMG_MAX_H = 720
_JPEG_Q    = 82


def _compress(img_bytes: bytes, source_format: str = "PNG") -> tuple[bytes, str]:
    pil_image = _pil_image()
    if not pil_image:
        return img_bytes, f"image/{source_format.lower()}"

    try:
        img = pil_image.open(io.BytesIO(img_bytes)).convert("RGB")
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), pil_image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q, optimize=False)
        return buf.getvalue(), "image/jpeg"
    except Exception as e:
        print(f"[Vision] ⚠️  Image compress failed: {e}")
        return img_bytes, f"image/{source_format.lower()}"


def _capture_screen() -> tuple[bytes, str]:

    mss_mod = _mss()
    if not mss_mod:
        raise RuntimeError("mss is not installed. Run: pip install mss")

    with mss_mod.mss() as sct:
        monitors = sct.monitors          # [0] = all combined, [1..n] = real screens
        target   = monitors[1] if len(monitors) > 1 else monitors[0]
        shot     = sct.grab(target)
        png      = mss_mod.tools.to_png(shot.rgb, shot.size)

    return _compress(png, "PNG")


def _cv2_backend() -> int:
    """Return the best OpenCV camera backend for the current OS."""
    cv2 = _cv2()
    if not cv2:
        return 0
    os_name = _get_os()
    if os_name == "windows":
        return cv2.CAP_DSHOW
    if os_name == "mac":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY


def _probe_camera(index: int, backend: int, warmup: int = 5) -> bool:

    cv2 = _cv2()
    if not cv2:
        return False
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        cap.release()
        return False
    for _ in range(warmup):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        return False
    return bool(np.mean(frame) > 8)


def _detect_camera_index() -> int:

    backend = _cv2_backend()
    print("[Vision] 🔍 Auto-detecting camera...")
    for idx in range(6):
        if _probe_camera(idx, backend):
            print(f"[Vision] ✅ Camera found at index {idx}")
            _save_config_key("camera_index", idx)
            return idx
        print(f"[Vision] ⚠️  Camera index {idx}: no usable frame")

    print("[Vision] ⚠️  No camera found — defaulting to index 0")
    _save_config_key("camera_index", 0)
    return 0


def _get_camera_index() -> int:
    cfg = _load_config()
    if "camera_index" in cfg:
        return int(cfg["camera_index"])
    return _detect_camera_index()


def _capture_camera() -> tuple[bytes, str]:
    cv2 = _cv2()
    if not cv2:
        raise RuntimeError("OpenCV (cv2) is not installed. Run: pip install opencv-python")

    index   = _get_camera_index()
    backend = _cv2_backend()
    cap     = cv2.VideoCapture(index, backend)

    if not cap.isOpened():
        raise RuntimeError(f"Camera index {index} could not be opened.")

    for _ in range(10):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError("Camera returned no frame.")

    pil_image = _pil_image()
    if pil_image:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = pil_image.fromarray(rgb)
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), pil_image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q)
        return buf.getvalue(), "image/jpeg"

    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_Q])
    return buf.tobytes(), "image/jpeg"
