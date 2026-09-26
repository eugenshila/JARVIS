"""Vision tool — see via camera or image files, using LLaVA (Ollama) or OpenAI vision.

Works offline with Ollama llava model.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from jarvis.tools.base import BaseTool, ToolSpec


class VisionTool(BaseTool):
    spec = ToolSpec(
        name="vision",
        description="See and describe an image — from file path, URL, or camera. Uses Ollama llava (offline) or OpenAI vision if API key set. For Iron Man-style visual understanding.",
        parameters={
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Path to image file, or 'camera' for webcam snapshot, or URL"},
                "prompt": {"type": "string", "description": "What to look for in image", "default": "Describe what you see in detail"},
            },
            "required": ["image_path"],
        },
    )

    def run(self, image_path: str, prompt: str = "Describe what you see in detail", **kwargs) -> str:
        # Handle camera
        if image_path.lower() == "camera":
            return self._capture_and_describe(prompt)

        # Check if file exists
        p = Path(image_path).expanduser()
        if p.exists():
            return self._describe_file(p, prompt)

        # Check if URL
        if image_path.startswith("http://") or image_path.startswith("https://"):
            return self._describe_url(image_path, prompt)

        return f"Image not found: {image_path}. Use file path, 'camera', or URL. For camera, need opencv or Pillow."

    def _describe_file(self, path: Path, prompt: str) -> str:
        # Try Ollama llava first (offline)
        if self._ollama_available():
            try:
                return self._describe_with_ollama(path, prompt)
            except Exception as e:
                print(f"Ollama vision failed: {e}")

        # Try OpenAI vision if key set
        if os.environ.get("OPENAI_API_KEY"):
            try:
                return self._describe_with_openai(path, prompt)
            except Exception as e:
                print(f"OpenAI vision failed: {e}")

        # Fallback: basic image info
        try:
            from PIL import Image
            img = Image.open(path)
            return f"[Mock Vision] Image: {path.name}, Size: {img.size}, Mode: {img.mode}\nPrompt: {prompt}\n\nTo enable real vision:\n1. Ollama (offline): ollama pull llava && use with --engine ollama\n2. OpenAI: set OPENAI_API_KEY and use vision model gpt-4o-mini\n\nFor now, I can see basic metadata only."
        except ImportError:
            return f"[Mock Vision] Image file {path.name} exists ({path.stat().st_size} bytes). Install Pillow for metadata, or ollama pull llava for real vision. Prompt: {prompt}"
        except Exception as e:
            return f"Vision error: {e}"

    def _ollama_available(self) -> bool:
        import urllib.request
        import urllib.error
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as resp:
                import json
                data = json.loads(resp.read().decode())
                models = [m["name"] for m in data.get("models", [])]
                return any("llava" in m for m in models)
        except Exception:
            return False

    def _describe_with_ollama(self, path: Path, prompt: str) -> str:
        import urllib.request
        import json

        # Read image as base64
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        # Ollama API
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llava",
            "prompt": prompt,
            "images": [b64],
            "stream": False,
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return f"[Ollama LLaVA Vision]\n{result.get('response','')}"

    def _describe_with_openai(self, path: Path, prompt: str) -> str:
        import json
        import urllib.request

        # Read as base64
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        # Determine mime
        mime = "image/jpeg"
        if path.suffix.lower() == ".png":
            mime = "image/png"
        elif path.suffix.lower() == ".webp":
            mime = "image/webp"

        url = os.environ.get("JARVIS_API_URL", "https://api.openai.com/v1/chat/completions")
        model = os.environ.get("JARVIS_MODEL", "gpt-4o-mini")

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                    ]
                }
            ],
            "max_tokens": 500,
        }

        key = os.environ.get("OPENAI_API_KEY", "")
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            content = result["choices"][0]["message"]["content"]
            return f"[OpenAI Vision {model}]\n{content}"

    def _capture_and_describe(self, prompt: str) -> str:
        """Capture from webcam and describe."""
        try:
            import cv2  # type: ignore
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "Camera not available (cv2.VideoCapture failed)"
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return "Failed to capture from camera"

            # Save temp file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                temp_path = f.name
            cv2.imwrite(temp_path, frame)
            result = self._describe_file(Path(temp_path), prompt)
            Path(temp_path).unlink(missing_ok=True)
            return f"[Camera Capture]\n{result}"
        except ImportError:
            try:
                # Try Pillow + ImageGrab (Windows/macOS)
                from PIL import ImageGrab
                img = ImageGrab.grab()
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                    temp_path = f.name
                img.save(temp_path)
                result = self._describe_file(Path(temp_path), prompt)
                Path(temp_path).unlink(missing_ok=True)
                return f"[Screen Capture]\n{result}"
            except Exception as e:
                return f"Camera capture not available (need opencv-python or Pillow): {e}"
        except Exception as e:
            return f"Camera error: {e}"

    def _describe_url(self, url: str, prompt: str) -> str:
        # For URL, we can try OpenAI vision if key, else mock
        if os.environ.get("OPENAI_API_KEY"):
            try:
                import json
                import urllib.request
                api_url = os.environ.get("JARVIS_API_URL", "https://api.openai.com/v1/chat/completions")
                model = os.environ.get("JARVIS_MODEL", "gpt-4o-mini")
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": url}}
                            ]
                        }
                    ],
                    "max_tokens": 500,
                }
                key = os.environ.get("OPENAI_API_KEY", "")
                req = urllib.request.Request(
                    api_url,
                    data=json.dumps(payload).encode(),
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode())
                    content = result["choices"][0]["message"]["content"]
                    return f"[OpenAI Vision URL]\n{content}"
            except Exception as e:
                return f"URL vision failed: {e}"

        return f"[Mock Vision] URL: {url}\nPrompt: {prompt}\nTo enable real URL vision, set OPENAI_API_KEY."
