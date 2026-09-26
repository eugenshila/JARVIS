"""Voice I/O — STT (Whisper) + TTS (Kokoro/pyttsx3) + Wake Word.

Works offline with mock fallback.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Callable

# Try imports, fallback to mock
try:
    import sounddevice as sd  # type: ignore
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    import soundfile as sf  # type: ignore
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False


class VoiceIO:
    """Handles voice input/output with offline fallbacks."""

    def __init__(self):
        self.stt_engine = self._detect_stt()
        self.tts_engine = self._detect_tts()
        print(f"VoiceIO: STT={self.stt_engine}, TTS={self.tts_engine}, sounddevice={HAS_SOUNDDEVICE}")

    def _detect_stt(self) -> str:
        # Check for faster-whisper (offline, local)
        try:
            import faster_whisper  # type: ignore
            return "faster-whisper (offline local)"
        except ImportError:
            pass
        # Check for whisper
        try:
            import whisper  # type: ignore
            return "whisper (offline)"
        except ImportError:
            pass
        # Check for SpeechRecognition
        try:
            import speech_recognition  # type: ignore
            return "speech_recognition"
        except ImportError:
            pass
        return "mock (type to talk)"

    def _detect_tts(self) -> str:
        try:
            import kokoro  # type: ignore
            return "kokoro (neural, offline)"
        except ImportError:
            pass
        try:
            import pyttsx3  # type: ignore
            return "pyttsx3 (offline)"
        except ImportError:
            pass
        # Check if espeak available
        import shutil
        if shutil.which("espeak") or shutil.which("espeak-ng"):
            return "espeak (offline)"
        return "mock (text only)"

    def listen(self, timeout: float = 5.0, phrase_time_limit: float = 5.0) -> str:
        """Listen for voice input, return text. Falls back to typed input if no mic."""
        if self.stt_engine.startswith("mock"):
            # Fallback to typed input
            try:
                return input("🎤 You (type, since no STT): ").strip()
            except (EOFError, KeyboardInterrupt):
                return ""

        # Try faster-whisper with sounddevice
        if HAS_SOUNDDEVICE and "faster-whisper" in self.stt_engine:
            try:
                return self._listen_faster_whisper(timeout, phrase_time_limit)
            except Exception as e:
                print(f"STT failed: {e}, falling back to typing")
                return input("🎤 You (type): ").strip()

        # Fallback to typing
        return input("🎤 You (type): ").strip()

    def _listen_faster_whisper(self, timeout: float, phrase_time_limit: float) -> str:
        """Record and transcribe with faster-whisper."""
        import numpy as np
        from faster_whisper import WhisperModel  # type: ignore

        print(f"🎤 Listening for {phrase_time_limit}s... (speak now)")
        
        # Record
        samplerate = 16000
        duration = phrase_time_limit
        try:
            audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32')
            sd.wait()
        except Exception as e:
            print(f"Recording failed: {e}")
            raise

        # Simple VAD: check if audio has energy
        energy = float((audio ** 2).mean() ** 0.5)
        if energy < 0.001:
            print("No speech detected (too quiet)")
            return ""

        # Transcribe
        try:
            model = WhisperModel("base", device="cpu", compute_type="int8")
            # Save temp wav
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            if HAS_SOUNDFILE:
                sf.write(temp_path, audio, samplerate)
            else:
                # Fallback: use scipy if available
                try:
                    from scipy.io import wavfile
                    wavfile.write(temp_path, samplerate, (audio * 32767).astype('int16'))
                except ImportError:
                    raise RuntimeError("Need soundfile or scipy to save wav")

            segments, info = model.transcribe(temp_path, beam_size=5)
            text = " ".join([seg.text for seg in segments]).strip()
            Path(temp_path).unlink(missing_ok=True)
            print(f"  Heard: {text}")
            return text
        except Exception as e:
            print(f"Transcription failed: {e}")
            raise

    def speak(self, text: str, voice: str | None = None):
        """Speak text via TTS, fallback to printing."""
        # Always print for visibility
        print(f"🔊 JARVIS: {text}")

        if self.tts_engine.startswith("mock"):
            return

        # Try kokoro
        if "kokoro" in self.tts_engine:
            try:
                self._speak_kokoro(text)
                return
            except Exception as e:
                print(f"Kokoro TTS failed: {e}")

        # Try pyttsx3
        if "pyttsx3" in self.tts_engine:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 180)
                engine.say(text)
                engine.runAndWait()
                return
            except Exception as e:
                print(f"pyttsx3 failed: {e}")

        # Try espeak
        if "espeak" in self.tts_engine:
            try:
                import subprocess
                subprocess.run(["espeak", text], timeout=10)
                return
            except Exception:
                try:
                    import subprocess
                    subprocess.run(["espeak-ng", text], timeout=10)
                    return
                except Exception as e:
                    print(f"espeak failed: {e}")

    def _speak_kokoro(self, text: str):
        """Speak with Kokoro neural TTS (offline, high quality)."""
        try:
            from kokoro import KPipeline  # type: ignore
            import sounddevice as sd
            import numpy as np

            # Kokoro pipeline
            pipeline = KPipeline(lang_code='a')  # American English
            # Generate
            generator = pipeline(text, voice='af_heart', speed=1.0)
            for i, (gs, ps, audio) in enumerate(generator):
                # Play
                sd.play(audio, samplerate=24000)
                sd.wait()
                break  # Only first chunk for simplicity
        except Exception as e:
            raise RuntimeError(f"Kokoro failed: {e}")

    def play_wav(self, path: str):
        """Play a wav file."""
        if not HAS_SOUNDDEVICE or not HAS_SOUNDFILE:
            print(f"Would play: {path} (install sounddevice+soundfile for audio)")
            return
        try:
            data, fs = sf.read(path)
            sd.play(data, fs)
            sd.wait()
        except Exception as e:
            print(f"Play failed: {e}")


def interactive_voice_loop(agent, wake_word: str = "jarvis", tts: bool = True):
    """Run interactive voice loop like Iron Man.

    - Listens for wake word or any speech
    - Runs agent
    - Speaks response
    """
    vio = VoiceIO()
    print("")
    print("="*60)
    print("JARVIS Iron Man Mode — Interactive Voice")
    print("="*60)
    print(f"STT: {vio.stt_engine}")
    print(f"TTS: {vio.tts_engine}")
    print(f"Wake word: '{wake_word}' (or just speak)")
    print("Say 'exit' or 'goodbye' to quit, or Ctrl+C")
    print("")

    # Greeting
    try:
        greeting = agent.get_greeting() if hasattr(agent, 'get_greeting') else "Hello Sir, JARVIS online."
    except Exception:
        greeting = "Hello Sir, JARVIS online."
    
    print(f"JARVIS: {greeting}")
    if tts:
        vio.speak(greeting)

    while True:
        try:
            # Listen
            user_text = vio.listen(timeout=10, phrase_time_limit=6)
            if not user_text:
                continue

            lower = user_text.lower().strip()
            if lower in ("exit", "quit", "goodbye", "bye jarvis", "shutdown"):
                farewell = "Shutting down, Sir. Always a pleasure."
                print(f"JARVIS: {farewell}")
                if tts:
                    vio.speak(farewell)
                break

            # Check wake word (if present, strip it)
            if wake_word.lower() in lower:
                # Remove wake word for cleaner prompt
                user_text = lower.replace(wake_word.lower(), "").strip()
                if not user_text:
                    user_text = "Yes Sir?"
            
            if not user_text:
                continue

            print(f"\nYou: {user_text}")
            
            # Run agent
            try:
                resp = agent.run(user_text, context="")
                print(f"\nJARVIS: {resp.content}\n")
                if tts:
                    # For TTS, strip markdown and keep concise
                    tts_text = resp.content[:500]  # Limit for TTS
                    # Remove code blocks for speech
                    import re
                    tts_text = re.sub(r"```.*?```", " ", tts_text, flags=re.DOTALL)
                    tts_text = re.sub(r"`.*?`", " ", tts_text)
                    tts_text = tts_text.replace("*", "").replace("#", "")
                    vio.speak(tts_text[:400])
            except Exception as e:
                err = f"Sorry Sir, I encountered an error: {e}"
                print(err)
                if tts:
                    vio.speak(err)

        except KeyboardInterrupt:
            print("\n\nJARVIS: Interrupted, Sir. Shutting down.")
            break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(1)
