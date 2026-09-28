"""Local JARVIS voice output.

Primary path: Piper neural TTS with a user-supplied local voice model.
Fallback: Windows SAPI so the assistant remains usable when Piper is not installed.

The optional cinematic JARVIS voice model must be obtained and redistributed only
according to its own model-card/license terms.
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, threading, time
from pathlib import Path

_STATUS_DEFAULT={"state":"standby","listening":False,"speaking":False,"wake_word":"jarvis","transcript":"","response":"","event_id":0,"voice":"fallback"}

def _base_dir() -> Path:
    if os.environ.get("JARVIS_HOME"): return Path(os.environ["JARVIS_HOME"])
    if getattr(sys,"_MEIPASS",None): return Path(sys._MEIPASS)
    return Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path.cwd()

def voice_status_path() -> Path:
    directory=Path(os.environ.get("LOCALAPPDATA",Path.home()))/"JARVIS"; directory.mkdir(parents=True,exist_ok=True); return directory/"voice_status.json"

def read_voice_status() -> dict:
    try: return {**_STATUS_DEFAULT,**json.loads(voice_status_path().read_text(encoding="utf-8"))}
    except (OSError,ValueError,TypeError): return dict(_STATUS_DEFAULT)

def write_voice_status(**changes: object) -> None:
    status=read_voice_status(); status.update(changes); status["updated_at"]=time.time()
    try: voice_status_path().write_text(json.dumps(status),encoding="utf-8")
    except OSError: pass

def _piper_paths():
    base=_base_dir()
    exe_candidates=[os.environ.get("JARVIS_PIPER_EXE"),str(base/"piper"/"piper.exe"),str(base/"piper.exe"),shutil.which("piper")]
    model_candidates=[os.environ.get("JARVIS_VOICE_MODEL"),str(base/"voice"/"jarvis-medium.onnx"),str(base/"voice"/"jarvis.onnx")]
    config_candidates=[os.environ.get("JARVIS_VOICE_CONFIG"),str(base/"voice"/"jarvis-medium.onnx.json"),str(base/"voice"/"jarvis.onnx.json")]
    exe=next((Path(p) for p in exe_candidates if p and Path(p).is_file()),None)
    model=next((Path(p) for p in model_candidates if p and Path(p).is_file()),None)
    config=next((Path(p) for p in config_candidates if p and Path(p).is_file()),None)
    return exe,model,config

def piper_available() -> bool:
    exe,model,_=_piper_paths(); return exe is not None and model is not None

def _powershell_speak(text:str)->None:
    clean=(text or "").replace("'","''"); rate=int(os.environ.get("JARVIS_VOICE_RATE","-1")); volume=int(os.environ.get("JARVIS_VOICE_VOLUME","100"))
    script=("Add-Type -AssemblyName System.Speech; "
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$voices=$s.GetInstalledVoices(); "
            "$preferred=@('Microsoft George','George','Microsoft Ryan','Ryan','Microsoft David','David'); "
            "$chosen=$null; foreach($p in $preferred){$chosen=$voices | Where-Object {$_.VoiceInfo.Name -eq $p} | Select-Object -First 1; if($chosen){break}}; "
            "if($chosen){$s.SelectVoice($chosen.VoiceInfo.Name)}; "
            f"$s.Rate={rate}; $s.Volume={volume}; f"$s.Speak('{clean}')"")
    # PowerShell does not interpret the Python f-string above; build the final command explicitly.
    script=script.replace('f"$s.Speak(', '$s.Speak(').replace('')"+")','')')
    subprocess.run(["powershell","-NoProfile","-Command",script],timeout=60,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def _piper_speak(text:str)->None:
    exe,model,config=_piper_paths()
    if not exe or not model: raise FileNotFoundError("Piper executable or voice model is not installed")
    with tempfile.NamedTemporaryFile(prefix="jarvis_",suffix=".wav",delete=False) as tmp: output=Path(tmp.name)
    try:
        args=[str(exe),"--model",str(model)]
        if config: args += ["--config",str(config)]
        args += ["--output_file",str(output),"--sentence_silence","0.2"]
        result=subprocess.run(args,input=text.encode("utf-8"),capture_output=True,timeout=60,check=False,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0) if os.name=="nt" else 0)
        if result.returncode: raise RuntimeError(result.stderr.decode("utf-8",errors="replace")[:500])
        if os.name=="nt":
            import winsound; winsound.PlaySound(str(output),winsound.SND_FILENAME)
        else: raise RuntimeError("Piper playback currently requires Windows.")
    finally: output.unlink(missing_ok=True)

def speak(text:str,asynchronous:bool=True)->None:
    if os.name!="nt" or not text: return
    clean=text[:2500]
    def target():
        write_voice_status(speaking=True,voice="piper" if piper_available() else "windows-sapi")
        try:
            if piper_available(): _piper_speak(clean)
            else: _powershell_speak(clean)
        except Exception:
            try: _powershell_speak(clean)
            except Exception: pass
        finally: write_voice_status(speaking=False)
    if asynchronous: threading.Thread(target=target,daemon=True,name="jarvis-tts").start()
    else: target()

def available_voice()->str:
    if piper_available(): return "Piper neural voice"
    return "Windows SAPI fallback"
