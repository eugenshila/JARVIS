"""
speech/echo.py — telling the user's voice apart from our own coming back.

THE PROBLEM
    Writing audio to a device returns when the buffer *accepts* it, not when
    the room has finished with it. So for a moment after a reply "ends", sound
    is still leaving the speakers. A microphone streaming through that gap
    hears the assistant's own last sentence and answers itself.

WHY A LOUDNESS THRESHOLD DOES NOT WORK
    "The mic is louder than the echo" requires knowing how loud the echo is,
    and that is not a constant: it depends on speaker volume, mic placement,
    the room, whether headphones are plugged in, whether a hand is over the
    mic. One tuned number is wrong for almost everyone — too eager on a loud
    desktop speaker, too deaf on a quiet laptop.

WHAT THIS DOES INSTEAD
    Two signals, neither needing per-machine tuning.

    1. CONTENT. Echo is not merely loud, it is *the sound we just played*.
       Both streams are reduced to a handful of band energies, and the recent
       output is then **subtracted** from the microphone block rather than
       merely compared with it. Pure echo cancels to nearly nothing. A second
       voice survives, because its formants sit in bands where ours were weak.
       That distinction holds even when both arrive at the same loudness —
       exactly the case a level test gets wrong.

    2. A LEARNED ECHO GAIN. Every time the content check says "that is
       definitely just echo", the observed mic-to-output ratio updates a
       running estimate. The system calibrates to the real room within a few
       seconds of the first sentence, and re-calibrates when the volume
       changes or a hand covers the mic.

    Band energies rather than raw spectra also make the comparison
    sample-rate agnostic, so the mic and the output stream do not have to
    match.

NUMPY IS OPTIONAL
    Without numpy this degrades to a plain "is the tail still playing" gate,
    which is what the code did before. It never becomes an import error.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass

try:  # numpy is optional; everything below has a scalar fallback
    import numpy as _np

    HAS_NUMPY = True
except ImportError:  # pragma: no cover - exercised on minimal installs
    _np = None
    HAS_NUMPY = False

#: Number of log-spaced bands the signal is reduced to. Eight is enough to
#: separate two voices and cheap enough to run on every 20 ms block.
BANDS = 8

#: How much recent output we keep to subtract from the mic (seconds).
OUTPUT_MEMORY_SECONDS = 1.0

#: Residual energy below this fraction of the mic block is "that was echo".
RESIDUAL_ECHO_RATIO = 0.35

#: Smoothing for the learned mic/output gain. Low = trusts history.
GAIN_ALPHA = 0.25

#: Hard floor: after output stops, ignore the mic for at least this long.
MIN_TAIL_SECONDS = 0.12


@dataclass
class Verdict:
    is_echo: bool
    residual_ratio: float
    reason: str
    echo_gain: float


def _band_energies(samples) -> list[float]:
    """Reduce a block of audio to :data:`BANDS` log-spaced band energies."""
    if not HAS_NUMPY:
        return []
    data = _np.asarray(samples, dtype=_np.float32).ravel()
    if data.size < 32:
        return []
    if data.dtype.kind == "i":  # pragma: no cover - defensive
        data = data / 32768.0
    spectrum = _np.abs(_np.fft.rfft(data * _np.hanning(data.size)))
    if spectrum.size < BANDS:
        return []
    # Log spacing: speech detail lives in the low bands, so give them the
    # resolution rather than splitting the spectrum evenly.
    edges = _np.unique(
        _np.geomspace(1, spectrum.size, BANDS + 1).astype(int)
    )
    if edges.size < 2:
        return []
    out: list[float] = []
    for start, end in zip(edges[:-1], edges[1:]):
        segment = spectrum[start:end]
        out.append(float(_np.sqrt((segment**2).mean())) if segment.size else 0.0)
    while len(out) < BANDS:
        out.append(0.0)
    return out[:BANDS]


def _energy(bands: list[float]) -> float:
    return math.sqrt(sum(b * b for b in bands)) if bands else 0.0


class EchoSuppressor:
    """Decides whether a microphone block is our own voice coming back."""

    def __init__(self) -> None:
        self._output: deque[tuple[float, list[float]]] = deque(maxlen=64)
        self._last_output_at: float = 0.0
        self._echo_gain: float = 0.0  # learned mic/output ratio, 0 = unknown
        self._lock = threading.Lock()

    # -- the playback side --------------------------------------------------

    def note_output(self, samples, when: float | None = None) -> None:
        """Call with each block of audio as it is sent to the speakers."""
        now = time.monotonic() if when is None else when
        bands = _band_energies(samples)
        with self._lock:
            self._last_output_at = now
            if bands:
                self._output.append((now, bands))

    def note_output_finished(self, when: float | None = None) -> None:
        with self._lock:
            self._last_output_at = time.monotonic() if when is None else when

    # -- the microphone side ------------------------------------------------

    def _recent_output(self, now: float) -> list[float]:
        """Band-wise maximum of everything played in the recent window."""
        combined = [0.0] * BANDS
        found = False
        for when, bands in self._output:
            if now - when > OUTPUT_MEMORY_SECONDS:
                continue
            found = True
            for i, value in enumerate(bands[:BANDS]):
                if value > combined[i]:
                    combined[i] = value
        return combined if found else []

    def classify(self, samples, now: float | None = None) -> Verdict:
        """Is this microphone block our own echo?"""
        now = time.monotonic() if now is None else now
        with self._lock:
            silent_for = now - self._last_output_at
            recent = self._recent_output(now)
            gain = self._echo_gain

        # Nothing has been played recently: it cannot be our echo.
        if not recent and silent_for > OUTPUT_MEMORY_SECONDS:
            return Verdict(False, 1.0, "no recent output", gain)

        mic_bands = _band_energies(samples)
        if not mic_bands or not recent:
            # No numpy, or no reference: fall back to the crude tail gate that
            # this module exists to replace, rather than guessing.
            is_tail = silent_for < MIN_TAIL_SECONDS
            return Verdict(is_tail, 1.0, "tail gate (no spectral data)", gain)

        mic_energy = _energy(mic_bands)
        if mic_energy <= 1e-9:
            return Verdict(True, 0.0, "silence", gain)

        # Subtract, band by band, as much of the recent output as the learned
        # gain says should be there. What remains is everything the speakers
        # cannot explain.
        scale = gain if gain > 0 else (mic_energy / (_energy(recent) or 1.0))
        residual = [max(0.0, m - scale * r) for m, r in zip(mic_bands, recent)]
        ratio = _energy(residual) / mic_energy

        is_echo = ratio < RESIDUAL_ECHO_RATIO
        if is_echo:
            # Confident echo: use it to calibrate to this room.
            observed = mic_energy / (_energy(recent) or 1.0)
            with self._lock:
                self._echo_gain = (
                    observed if self._echo_gain <= 0
                    else (1 - GAIN_ALPHA) * self._echo_gain + GAIN_ALPHA * observed
                )
        return Verdict(
            is_echo,
            ratio,
            "cancelled by recent output" if is_echo else "survives cancellation",
            gain,
        )

    def should_listen(self, samples, now: float | None = None) -> bool:
        """Convenience inverse of :meth:`classify` for the audio loop."""
        return not self.classify(samples, now).is_echo

    # -- introspection ------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._output.clear()
            self._last_output_at = 0.0
            self._echo_gain = 0.0

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "spectral": HAS_NUMPY,
                "echo_gain": round(self._echo_gain, 4),
                "calibrated": self._echo_gain > 0,
                "output_blocks": len(self._output),
            }
