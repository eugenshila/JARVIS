"""Optional Windows HUD companion: spoken greeting and double-clap activation.

This process runs in the signed-in user's session. It never sends microphone
audio to the backend. A double clap opens the local HUD; chat voice input still
uses the browser's microphone button.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

HUD_URL = os.environ.get("JARVIS_HUD_URL", "http://127.0.0.1:8765")
STARTUP_NAME = "JARVIS-HUD.bat"


class DoubleClap:
    def __init__(self, threshold: float = 0.18):
        self.threshold = threshold
        self.last_peak = 0.0
        self.first_clap = 0.0
        self.active_since = 0.0
        self.quiet_since = 0.0

    def feed(self, peak: float, now: float) -> bool:
        """Return true on two short, separated transients within 1.1 seconds."""
        if peak >= self.threshold:
            if not self.active_since:
                self.active_since = now
            if now - self.active_since > 0.18:
                self.first_clap = 0.0  # sustained noise or speech
            self.quiet_since = 0.0
            return False

        if self.active_since:
            duration = now - self.active_since
            self.active_since = 0.0
            if 0.02 <= duration <= 0.18:
                if self.first_clap and 0.22 <= now - self.first_clap <= 1.1:
                    self.first_clap = 0.0
                    return True
                self.first_clap = now
        if self.first_clap and now - self.first_clap > 1.1:
            self.first_clap = 0.0
        return False


def speak(text: str) -> None:
    if sys.platform != "win32":
        return
    # Uses an installed Windows SAPI voice; it does not copy an actor's voice.
    escaped = text.replace("'", "''")
    script = ("Add-Type -AssemblyName System.Speech; "
              "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              "$v=$s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'en-GB' } | Select-Object -First 1; "
              "if($v){$s.SelectVoice($v.VoiceInfo.Name)}; "
              f"$s.Speak('{escaped}')")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", script], timeout=25, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        pass


def startup_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if sys.platform != "win32" or not appdata:
        raise RuntimeError("Windows user sign-in startup is required.")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / STARTUP_NAME


def install_startup(launcher: Path) -> Path:
    if not launcher.is_file():
        raise FileNotFoundError(launcher)
    destination = startup_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f'@echo off\r\ncall "{launcher.resolve()}"\r\n', encoding="utf-8")
    return destination


def listen_for_hands_free() -> None:
    try:
        import sounddevice as sd
        import numpy as np
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Install voice support: pip install faster-whisper sounddevice numpy") from exc

    threshold = float(os.environ.get("JARVIS_CLAP_THRESHOLD", "0.18"))
    detector = DoubleClap(threshold)
    model = WhisperModel(
        os.environ.get("JARVIS_WHISPER_MODEL", "base.en"),
        device=os.environ.get("JARVIS_WHISPER_DEVICE", "cpu"),
        compute_type=os.environ.get("JARVIS_WHISPER_COMPUTE", "int8"),
    )
    speak("JARVIS online. Hands-free voice control is ready, Sir.")
    with sd.InputStream(channels=1, samplerate=16000, blocksize=800) as microphone:
        while True:
            samples, overflowed = microphone.read(800)
            if overflowed:
                continue
            peak = max(abs(float(value[0])) for value in samples)
            if not detector.feed(peak, time.monotonic()):
                continue
            speak("Yes, Sir.")
            time.sleep(0.6)
            try:
                duration = float(os.environ.get("JARVIS_LISTEN_SECONDS", "8"))
                audio = sd.rec(int(max(2, min(duration, 20)) * 16000), samplerate=16000,
                               channels=1, dtype="float32")
                sd.wait()
                samples = np.asarray(audio[:, 0], dtype=np.float32)
                if float(np.max(np.abs(samples))) < 0.012:
                    speak("I didn't catch that, Sir.")
                    continue
                segments, _ = model.transcribe(samples, language="en", vad_filter=True)
                command = " ".join(s.text.strip() for s in segments).strip()
                if not command:
                    speak("I didn't catch that, Sir.")
                    continue
                payload = json.dumps({"messages": [{"role": "user", "content": command}]}).encode("utf-8")
                request = urllib.request.Request(
                    f"{HUD_URL.rstrip('/')}/hud/chat", data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=120) as response:
                    answer = str(json.load(response).get("content", "")).strip()
                print(f"You: {command}\nJARVIS: {answer}", flush=True)
                speak(answer)
            except Exception as exc:
                print(f"Voice error: {exc}", file=sys.stderr, flush=True)
                speak("I encountered a local voice system error, Sir.")


def listen_for_claps() -> None:
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError("Microphone support missing. Install with: python -m pip install sounddevice") from exc

    threshold = float(os.environ.get("JARVIS_CLAP_THRESHOLD", "0.18"))
    detector = DoubleClap(threshold)
    print(f"JARVIS double-clap wake is listening (threshold {threshold:.2f}). Press Ctrl+C to stop.", flush=True)
    with sd.InputStream(channels=1, samplerate=16000, blocksize=800) as microphone:
        while True:
            samples, overflowed = microphone.read(800)
            if overflowed:
                continue
            peak = max(abs(float(value[0])) for value in samples)
            if detector.feed(peak, time.monotonic()):
                print("Double clap detected. Opening JARVIS HUD.", flush=True)
                webbrowser.open(HUD_URL)
                speak("At your service, Eugene.")
                time.sleep(2)  # Ignore the computer's own greeting.


def main() -> None:
    parser = argparse.ArgumentParser(description="JARVIS HUD Windows companion")
    parser.add_argument("--install-startup", type=Path, metavar="LAUNCHER")
    parser.add_argument("--remove-startup", action="store_true")
    parser.add_argument("--greet", action="store_true")
    parser.add_argument("--clap", action="store_true")
    parser.add_argument("--hands-free", action="store_true")
    args = parser.parse_args()
    if args.install_startup:
        print(f"JARVIS will launch after Windows sign-in: {install_startup(args.install_startup)}")
    elif args.remove_startup:
        startup_path().unlink(missing_ok=True)
        print("JARVIS HUD sign-in startup removed.")
    else:
        if args.greet:
            speak("JARVIS online. Good day, Eugene. Local systems are ready.")
        if args.hands_free:
            listen_for_hands_free()
        elif args.clap:
            listen_for_claps()


if __name__ == "__main__":
    main()
