"""Windows hands-free JARVIS companion: local wake word, double-clap wake and voice control."""
from __future__ import annotations
import argparse,json,os,sys,time,urllib.request
from collections import deque
from pathlib import Path
from jarvis.voice import available_voice, speak, write_voice_status

HUD_URL=os.environ.get("JARVIS_HUD_URL","http://127.0.0.1:8765")
STARTUP_NAME="JARVIS-HUD.bat"
WAKE_WORDS=("hey jarvis","jarvis","hi jarvis","okay jarvis")
SLEEP_PHRASES=("that's it jarvis","thank you jarvis","standby","go to sleep","stop listening")
EXIT_PHRASES=("shut down jarvis","goodbye jarvis","jarvis power off")

class DoubleClap:
    def __init__(self,threshold:float=0.18): self.threshold=threshold; self.first_clap=0.0; self.active_since=0.0
    def feed(self,peak:float,now:float)->bool:
        if peak>=self.threshold:
            if not self.active_since:self.active_since=now
            if now-self.active_since>0.18:self.first_clap=0.0
            return False
        if self.active_since:
            duration=now-self.active_since; self.active_since=0.0
            if 0.02<=duration<=0.18:
                if self.first_clap and 0.22<=now-self.first_clap<=1.1:self.first_clap=0.0; return True
                self.first_clap=now
        if self.first_clap and now-self.first_clap>1.1:self.first_clap=0.0
        return False

def startup_path()->Path:
    appdata=os.environ.get("APPDATA")
    if sys.platform!="win32" or not appdata: raise RuntimeError("Windows user sign-in startup is required.")
    return Path(appdata)/"Microsoft"/"Windows"/"Start Menu"/"Programs"/"Startup"/STARTUP_NAME

def install_startup(launcher:Path)->Path:
    if not launcher.is_file(): raise FileNotFoundError(launcher)
    destination=startup_path(); destination.parent.mkdir(parents=True,exist_ok=True); destination.write_text(f'@echo off\r\ncall "{launcher.resolve()}"\r\n',encoding="utf-8"); return destination

def _whisper_model_name() -> str:
    configured = os.environ.get("JARVIS_WHISPER_MODEL")
    if configured:
        return configured
    # CI places a small offline model beside the frozen executable. Without
    # it faster-whisper tries to download on first launch, which made voice
    # appear dead on machines with no Hugging Face access.
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        bundled = Path(bundled_root) / "whisper-model"
        if (bundled / "model.bin").is_file():
            return str(bundled)
    return "base.en"


def _transcribe(model,samples,np)->str:
    if float(np.max(np.abs(samples)))<float(os.environ.get("JARVIS_AUDIO_THRESHOLD","0.012")): return ""
    segments,_=model.transcribe(samples,language="en",vad_filter=True,condition_on_previous_text=False)
    return " ".join(s.text.strip() for s in segments).strip()

def _send_command(command:str)->str:
    payload=json.dumps({"messages":[{"role":"user","content":command}]}).encode("utf-8")
    request=urllib.request.Request(f"{HUD_URL.rstrip('/')}/hud/chat",data=payload,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as response:return str(json.load(response).get("content","")).strip()

def _contains_wake_word(text:str)->tuple[bool,str]:
    normalized=" ".join(text.lower().split())
    for wake in WAKE_WORDS:
        if normalized==wake:return True,""
        if normalized.startswith(wake+" "):return True,normalized[len(wake):].strip(" ,:.-")
    return False,""

def _record_command(sd,np):
    sample_rate=16000; max_seconds=float(os.environ.get("JARVIS_LISTEN_SECONDS","10")); silence_seconds=float(os.environ.get("JARVIS_SILENCE_SECONDS","1.1")); threshold=float(os.environ.get("JARVIS_AUDIO_THRESHOLD","0.012"))
    blocks=[]; silent_for=0.0; started=time.monotonic()
    while time.monotonic()-started<max_seconds:
        block=sd.rec(int(sample_rate*0.1),samplerate=sample_rate,channels=1,dtype="float32"); sd.wait(); data=np.asarray(block[:,0],dtype=np.float32); blocks.append(data)
        level=float(np.sqrt(np.mean(np.square(data)))) if data.size else 0.0
        if level<threshold:
            silent_for+=0.1
            if silent_for>=silence_seconds and time.monotonic()-started>0.8: break
        else: silent_for=0.0
    return np.concatenate(blocks) if blocks else np.zeros(1,dtype=np.float32)

def _handle_command(command:str)->None:
    write_voice_status(state="processing",listening=False,transcript=command,response="")
    try:
        answer=_send_command(command); print(f"You: {command}\nJARVIS: {answer}",flush=True)
        write_voice_status(state="speaking",listening=False,transcript=command,response=answer,event_id=int(time.time_ns()//1_000_000)); speak(answer,asynchronous=False)
    except Exception as exc:
        print(f"Voice error: {exc}",file=sys.stderr,flush=True); write_voice_status(state="error",listening=False,transcript=command,response=str(exc),event_id=int(time.time_ns()//1_000_000)); speak("I encountered a local voice system error, Sir.",asynchronous=False)

def listen_for_hands_free()->None:
    write_voice_status(state="starting",listening=False,response="",transcript="",voice=available_voice(),error="")
    try:
        import numpy as np
        import sounddevice as sd
        from faster_whisper import WhisperModel
    except ImportError as exc:
        message="Voice dependencies are missing: " + str(exc)
        write_voice_status(state="error",listening=False,error=message,voice=available_voice())
        raise RuntimeError(message) from exc
    try:
        model=WhisperModel(_whisper_model_name(),device=os.environ.get("JARVIS_WHISPER_DEVICE","cpu"),compute_type=os.environ.get("JARVIS_WHISPER_COMPUTE","int8"))
    except Exception as exc:
        message=f"Whisper model could not start: {type(exc).__name__}: {exc}"
        write_voice_status(state="error",listening=False,error=message,voice=available_voice())
        raise RuntimeError(message) from exc
    sample_rate=16000; standby_samples=int(sample_rate*float(os.environ.get("JARVIS_WAKE_WINDOW_SECONDS","2.0"))); buffer=deque(maxlen=standby_samples); detector=DoubleClap(float(os.environ.get("JARVIS_CLAP_THRESHOLD","0.18")))
    write_voice_status(state="standby",listening=True,response="",transcript="",voice=available_voice(),error=""); speak("JARVIS online. Hands-free voice control is ready, Sir.",asynchronous=False)
    with sd.InputStream(channels=1,samplerate=sample_rate,blocksize=1600) as microphone:
        while True:
            samples,overflowed=microphone.read(1600)
            if overflowed: continue
            now=time.monotonic(); peak=float(np.max(np.abs(samples)))
            if detector.feed(peak,now):
                write_voice_status(state="active",listening=True,wake_reason="double-clap")
                microphone.stop()
                speak("Yes, Sir.",asynchronous=False)
                command=_transcribe(model,_record_command(sd,np),np)
                if command:_handle_command(command)
                microphone.start()
                write_voice_status(state="standby",listening=True); continue
            buffer.extend(np.asarray(samples[:,0],dtype=np.float32))
            if len(buffer)<standby_samples: continue
            text=_transcribe(model,np.asarray(buffer,dtype=np.float32),np); woke,inline_command=_contains_wake_word(text)
            if not woke: continue
            write_voice_status(state="active",listening=True,wake_reason="voice")
            microphone.stop()
            speak("Yes, Sir. I am listening.",asynchronous=False)
            command=inline_command or _transcribe(model,_record_command(sd,np),np)
            if not command:
                speak("I didn't catch that, Sir.",asynchronous=False)
                microphone.start()
                write_voice_status(state="standby",listening=True); continue
            lowered=command.lower()
            if any(p in lowered for p in EXIT_PHRASES):
                speak("Understood, Sir. Shutting down the voice listener.",asynchronous=False); write_voice_status(state="offline",listening=False); return
            if any(p in lowered for p in SLEEP_PHRASES):
                speak("Standby, Sir. Say Jarvis when you need me.",asynchronous=False)
                microphone.start()
                write_voice_status(state="standby",listening=True); continue
            _handle_command(command)
            microphone.start()
            write_voice_status(state="standby",listening=True)

def listen_for_claps()->None: listen_for_hands_free()

def main()->None:
    parser=argparse.ArgumentParser(description="JARVIS Windows companion"); parser.add_argument("--install-startup",type=Path,metavar="LAUNCHER"); parser.add_argument("--remove-startup",action="store_true"); parser.add_argument("--greet",action="store_true"); parser.add_argument("--clap",action="store_true"); parser.add_argument("--hands-free",action="store_true"); args=parser.parse_args()
    if args.install_startup: print(f"JARVIS will launch after Windows sign-in: {install_startup(args.install_startup)}")
    elif args.remove_startup: startup_path().unlink(missing_ok=True)
    elif args.greet:
        speak("JARVIS online. Good day, Eugene. Local systems are ready.",asynchronous=False)
        if args.hands_free: listen_for_hands_free()
    elif args.hands_free or args.clap: listen_for_hands_free()

if __name__=="__main__": main()
