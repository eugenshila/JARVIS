"""Wake word detection — always-listening like Iron Man JARVIS.

Uses openWakeWord (offline) or simple energy-based detection.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from jarvis.tools.base import BaseTool, ToolSpec


class WakeWordTool(BaseTool):
    spec = ToolSpec(
        name="wakeword",
        description="Always-listening wake word detection for 'jarvis' — like Iron Man. Uses openWakeWord offline, or energy detection fallback. Returns if wake word detected.",
        parameters={
            "type": "object",
            "properties": {
                "timeout": {"type": "integer", "description": "Listen timeout seconds", "default": 10},
                "wake_word": {"type": "string", "description": "Wake word to detect", "default": "jarvis"},
            },
            "required": [],
        },
    )

    def run(self, timeout: int = 10, wake_word: str = "jarvis", **kwargs) -> str:
        # Try openWakeWord (offline, precise)
        try:
            return self._detect_openwakeword(timeout, wake_word)
        except ImportError:
            pass
        except Exception as e:
            print(f"openWakeWord failed: {e}")

        # Fallback to simple energy + speech detection
        try:
            return self._detect_energy(timeout, wake_word)
        except Exception as e:
            return f"Wake word detection not available (need openwakeword or sounddevice): {e}. Install: pip install openwakeword sounddevice"

    def _detect_openwakeword(self, timeout: int, wake_word: str) -> str:
        try:
            import openwakeword  # type: ignore
            from openwakeword.model import Model  # type: ignore
            import sounddevice as sd  # type: ignore
            import numpy as np  # type: ignore

            print(f"Listening for wake word '{wake_word}' for {timeout}s (openWakeWord, offline)...")

            model = Model(wakeword_models=[f"{wake_word.lower()}_v0.1"], inference_framework="onnx")

            # Simple detection loop
            samplerate = 16000
            block_size = 1280  # 80ms

            detected = False
            start = time.time()

            def callback(indata, frames, time_info, status):
                nonlocal detected
                if status:
                    print(status)
                # Predict
                prediction = model.predict(indata[:, 0])
                # Check if wake word score > threshold
                for mdl, score in prediction.items():
                    if score > 0.5:
                        print(f"Wake word '{mdl}' detected! Score: {score}")
                        detected = True

            with sd.InputStream(callback=callback, channels=1, samplerate=samplerate, blocksize=block_size):
                while time.time() - start < timeout and not detected:
                    time.sleep(0.1)

            if detected:
                return f"Wake word '{wake_word}' detected, Sir. How may I assist?"
            else:
                return f"No wake word '{wake_word}' detected in {timeout}s"

        except ImportError as e:
            raise ImportError(f"openwakeword not installed: {e}. Run: pip install openwakeword") from e

    def _detect_energy(self, timeout: int, wake_word: str) -> str:
        """Simple energy-based detection + STT for wake word."""
        try:
            import sounddevice as sd
            import numpy as np

            print(f"Listening for '{wake_word}' via energy detection for {timeout}s...")

            samplerate = 16000
            duration = timeout

            # Record
            audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32')
            sd.wait()

            # Check energy
            energy = float((audio ** 2).mean() ** 0.5)
            if energy < 0.001:
                return f"No speech detected (energy {energy:.4f} too low)"

            # Try to transcribe with faster-whisper if available
            try:
                from faster_whisper import WhisperModel
                import tempfile
                import soundfile as sf

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = f.name
                sf.write(temp_path, audio, samplerate)

                model = WhisperModel("tiny", device="cpu", compute_type="int8")
                segments, _ = model.transcribe(temp_path, beam_size=1)
                text = " ".join([s.text for s in segments]).lower()
                Path(temp_path).unlink(missing_ok=True)

                if wake_word.lower() in text:
                    return f"Wake word '{wake_word}' detected in: '{text}'"
                else:
                    return f"Heard: '{text}' but no wake word '{wake_word}'"

            except ImportError:
                # No STT, just report energy
                return f"Speech detected (energy {energy:.4f}) but no STT to check wake word. Install faster-whisper: pip install faster-whisper"

        except ImportError as e:
            raise ImportError(f"sounddevice not installed: {e}") from e
        except Exception as e:
            return f"Energy detection failed: {e}"
