"""
speech/wake.py — wake-word detection with two disciplines that matter.

    ZERO COST WHEN OFF. ``openwakeword`` (and numpy, and the ONNX runtime it
    drags in) is imported *inside* :meth:`WakeWordListener.start`, never at
    module import. A user who never enables the wake word pays nothing for it
    — no import time, no memory, no dependency.

    ZERO WORK ON THE AUDIO THREAD. The microphone callback must return in
    well under one block period or the capture stream glitches, and glitched
    audio ruins both recognition and any concurrent recording. So
    :meth:`feed` only does a non-blocking queue push; model inference happens
    on this module's own background thread. When the queue is full, the
    OLDEST block is dropped rather than blocking the caller — a wake word is
    detected on the newest audio, and falling behind is better than stuttering
    the stream.

Audio fed here never leaves the machine. The only network access is the
one-time model download the user explicitly triggers.
"""

from __future__ import annotations

import importlib.util
import queue
import threading
from collections.abc import Callable

#: Pretrained openwakeword phrase.
DEFAULT_MODEL = "hey_jarvis"

#: Detection score in [0, 1] above which we call it a hit.
DEFAULT_THRESHOLD = 0.5

#: openwakeword expects 16 kHz int16 mono.
SAMPLE_RATE = 16000

#: About a second of audio. Deep enough to ride out a scheduling hiccup,
#: shallow enough that a backlog cannot delay detection.
QUEUE_BLOCKS = 12


def is_installed() -> bool:
    """True if openwakeword is importable. Does not import it."""
    try:
        return importlib.util.find_spec("openwakeword") is not None
    except (ImportError, ValueError):
        return False


class WakeWordListener:
    """Feed it microphone blocks; it calls ``on_wake`` when it hears the word."""

    def __init__(
        self,
        on_wake: Callable[[str, float], None],
        model: str = DEFAULT_MODEL,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        self.on_wake = on_wake
        self.model_name = model
        self.threshold = float(threshold)
        self._queue: queue.Queue = queue.Queue(maxsize=QUEUE_BLOCKS)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._model = None
        self.dropped_blocks = 0
        self.detections = 0
        self.last_score = 0.0
        self.error = ""

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> bool:
        """Load the model and start the inference thread. Never raises."""
        if self._thread is not None and self._thread.is_alive():
            return True
        try:
            # Imported HERE, not at module scope: the whole point is that a
            # user who never turns this on never pays for it.
            from openwakeword.model import Model  # type: ignore

            self._model = Model(wakeword_models=[self.model_name], inference_framework="onnx")
        except ImportError:
            self.error = "openwakeword is not installed: pip install openwakeword"
            return False
        except Exception as exc:
            self.error = f"could not load wake-word model {self.model_name!r}: {exc}"
            return False

        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="jarvis-wakeword", daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
        self._thread = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -- the audio thread's only entry point --------------------------------

    def feed(self, block) -> None:
        """Called from the microphone callback. Must stay O(1) and never block.

        No inference, no allocation beyond the push, no lock that another
        thread can hold. If the consumer has fallen behind we discard the
        oldest block instead of waiting: recognising the wake word slightly
        late is survivable, stuttering the capture stream is not.
        """
        try:
            self._queue.put_nowait(block)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self.dropped_blocks += 1
                self._queue.put_nowait(block)
            except (queue.Empty, queue.Full):  # pragma: no cover - race only
                self.dropped_blocks += 1

    # -- the inference thread -----------------------------------------------

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                block = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                scores = self._model.predict(block)  # type: ignore[union-attr]
            except Exception as exc:
                self.error = f"wake-word inference failed: {exc}"
                continue
            if not isinstance(scores, dict):
                continue
            for name, score in scores.items():
                value = float(score)
                self.last_score = value
                if value >= self.threshold:
                    self.detections += 1
                    try:
                        self.on_wake(str(name), value)
                    except Exception:
                        pass  # a bad callback must not kill the listener
                    # Clear the backlog so one utterance cannot fire twice.
                    with self._queue.mutex:
                        self._queue.queue.clear()
                    break

    def status(self) -> dict[str, object]:
        return {
            "installed": is_installed(),
            "running": self.running,
            "model": self.model_name,
            "threshold": self.threshold,
            "detections": self.detections,
            "dropped_blocks": self.dropped_blocks,
            "last_score": round(self.last_score, 3),
            "error": self.error,
        }
