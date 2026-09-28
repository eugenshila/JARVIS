"""JARVIS voice output for Windows.

Uses an installed British male Windows SAPI voice (prefers George, then Ryan).
It intentionally provides a JARVIS-inspired British assistant sound rather than
attempting to reproduce any actor's exact voice.
"""
from __future__ import annotations
import os, subprocess, threading

def _powershell_speak(text: str) -> None:
    clean = (text or "").replace("'", "''")
    rate = int(os.environ.get("JARVIS_VOICE_RATE", "-1"))
    volume = int(os.environ.get("JARVIS_VOICE_VOLUME", "100"))
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$voices=$s.GetInstalledVoices(); "
        "$preferred=@('Microsoft George','George','Microsoft Ryan','Ryan','Microsoft David','David'); "
        "$chosen=$null; "
        "foreach($p in $preferred){$chosen=$voices | Where-Object {$_.VoiceInfo.Name -eq $p} | Select-Object -First 1; if($chosen){break}}; "
        "if($chosen){$s.SelectVoice($chosen.VoiceInfo.Name)}; "
        f"$s.Rate={rate}; $s.Volume={volume}; "
        f"$s.Speak('{clean}')"
    )
    subprocess.run(["powershell","-NoProfile","-Command",script],
                   timeout=60, check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def speak(text: str, asynchronous: bool = True) -> None:
    if os.name != "nt" or not text:
        return
    target = lambda: _powershell_speak(text[:2500])
    if asynchronous:
        threading.Thread(target=target, daemon=True).start()
    else:
        target()

def available_voice() -> str:
    if os.name != "nt":
        return "unavailable"
    try:
        import win32com.client
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        names = [v.GetDescription() for v in speaker.GetVoices()]
        for preferred in ("Microsoft George","George","Microsoft Ryan","Ryan"):
            for name in names:
                if preferred.lower() in name.lower():
                    return name
        return names[0] if names else "default"
    except Exception:
        return "default"
