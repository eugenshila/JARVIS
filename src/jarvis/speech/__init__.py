"""Speech placeholder — STT/TTS hooks."""

def list_voices():
    return ["mock"]

def tts(text: str) -> str:
    return f"[TTS mock] Would speak: {text[:100]}..."
