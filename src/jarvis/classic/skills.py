"""
classic/skills.py — the actions behind the classic intents.

Each function returns a plain sentence, because that sentence is both what the
HUD prints and what a text-to-speech voice reads. Every optional dependency is
imported *inside* the function that needs it: on a fresh checkout with none of
them installed, `jarvis classic "tell me a joke"` still works and only the
commands that genuinely need a library say so.

Differences from upstream KKshitiz/J.A.R.V.I.S worth knowing:

  weather   Upstream used pyowm with an OpenWeatherMap key committed in the
            source file. That key is not reused here (it is someone else's,
            and it is long dead). This uses Open-Meteo, which needs no key, so
            the command works on a clean install. Set OPENWEATHER_API_KEY to
            use OpenWeatherMap instead.
  wolfram   Key comes from WOLFRAM_APP_ID.
  notes     Written under JARVIS_HOME/notes, not a Windows-only absolute path,
            and no `notepad.exe` is spawned.
  power     Never executed directly — see router.py, which routes it through
            jarvis.core.confirm.
"""

from __future__ import annotations

import json
import os
import platform
import random
import shutil
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from jarvis.core.config import get_home

USER_AGENT = "jarvis-classic/1.0 (+https://github.com/eugenshila/JARVIS)"
HTTP_TIMEOUT = 8.0


def pick(options: list[str]) -> str:
    """Upstream's `randomize()` — one of several equivalent phrasings."""
    return random.choice(options) if options else ""


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
        return json.load(response)


# --------------------------------------------------------------------------
# greeting / time
# --------------------------------------------------------------------------

def greet(now: datetime | None = None) -> str:
    """Port of greet_startup.greet(), with the upstream minute-format bug fixed."""
    now = now or datetime.now()
    hour = now.hour
    if hour < 12:
        part = "Good morning, sir."
    elif hour < 18:
        part = "Good afternoon, sir."
    else:
        part = "Good evening, sir."
    return f"{part} It's {now.strftime('%I:%M %p').lstrip('0')} now."


def current_time(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"It's {now.strftime('%I:%M %p').lstrip('0')}, sir."


# --------------------------------------------------------------------------
# hardware — port of check_hardware.py
# --------------------------------------------------------------------------

def _psutil():
    try:
        import psutil  # type: ignore

        return psutil
    except ImportError:
        return None


def cpu_usage(per_core: bool = False) -> str:
    psutil = _psutil()
    if psutil is None:
        load = os.getloadavg()[0] if hasattr(os, "getloadavg") else None
        if load is None:
            return "I cannot read the processor without psutil installed, sir. Try: pip install psutil"
        return f"Load average over the last minute is {load:.2f}, sir. Install psutil for exact CPU percentages."
    if per_core:
        cores = psutil.cpu_percent(interval=1, percpu=True)
        listed = ", ".join(str(core) for core in cores)
        return f"The usages of cpu cores are {listed} percent respectively."
    return f"CPU usage is {psutil.cpu_percent(interval=1)} percent."


def ram_usage() -> str:
    psutil = _psutil()
    if psutil is None:
        return "I cannot read system memory without psutil installed, sir. Try: pip install psutil"
    memory = psutil.virtual_memory()
    verdict = " System overload detected." if memory.percent > 85 else " No overload detected."
    return f"System memory usage is {memory.percent} percent.{verdict}"


def battery_status() -> str:
    psutil = _psutil()
    if psutil is None:
        return "I cannot read the battery without psutil installed, sir. Try: pip install psutil"
    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if battery is None:
        return "No battery detected, sir. This machine appears to run on mains power."
    say = f"{battery.percent} percent power left. "
    if battery.percent < 30 and not battery.power_plugged:
        say += "Running on emergency backup power, sir."
    elif not battery.power_plugged and battery.secsleft and battery.secsleft > 0:
        say += f"Approximately {int(battery.secsleft / 60)} minutes remaining."
    elif battery.power_plugged:
        say += "Plugged in, charging."
    return say


# --------------------------------------------------------------------------
# jokes — port of tell_joke.py
# --------------------------------------------------------------------------

_FALLBACK_JOKES = [
    "A programmer's wife asks him to go to the store for a loaf of bread, and if they have eggs, get a dozen. He came back with twelve loaves of bread.",
    "There are only 10 kinds of people in this world: those who know binary and those who don't.",
    "Why do Java developers wear glasses? Because they don't C sharp.",
    "I would tell you a UDP joke, but you might not get it.",
    "A SQL query walks into a bar, walks up to two tables and asks, can I join you?",
]


def joke() -> str:
    try:
        from pyjokes import get_joke  # type: ignore

        return get_joke()
    except Exception:
        return pick(_FALLBACK_JOKES)


# --------------------------------------------------------------------------
# weather — replacement for get_weather.py
# --------------------------------------------------------------------------

def weather(city: str) -> str:
    city = (city or "").strip()
    if not city:
        return "Which city, sir?"

    key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    try:
        if key:
            url = (
                "https://api.openweathermap.org/data/2.5/weather?q="
                f"{urllib.parse.quote(city)}&units=metric&appid={urllib.parse.quote(key)}"
            )
            data = _get_json(url)
            main = data["main"]
            return (
                f"Weather status in {city} is {main['temp']} celsius and the sky is "
                f"{data['weather'][0]['description']}. The average wind speed is "
                f"{data.get('wind', {}).get('speed', 0)} metres per second and the humidity "
                f"is {main['humidity']} percent."
            )

        geo = _get_json(
            "https://geocoding-api.open-meteo.com/v1/search?count=1&name="
            + urllib.parse.quote(city)
        )
        results = geo.get("results") or []
        if not results:
            return f"Weather status in {city} is unavailable, sir. I could not find that place."
        place = results[0]
        data = _get_json(
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={place['latitude']}&longitude={place['longitude']}"
            "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
        )
        current = data["current"]
        return (
            f"Weather status in {place.get('name', city)} is "
            f"{current['temperature_2m']} celsius and the sky is "
            f"{_weather_code(current.get('weather_code'))}. The average wind speed is "
            f"{current['wind_speed_10m']} kilometres per hour and the humidity is "
            f"{current['relative_humidity_2m']} percent."
        )
    except Exception:
        return f"Weather status in {city} is unavailable, sir."


_WMO = {
    0: "clear", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "foggy", 48: "foggy",
    51: "drizzling", 53: "drizzling", 55: "drizzling", 61: "rainy", 63: "rainy", 65: "heavy rain",
    71: "snowy", 73: "snowy", 75: "heavy snow", 80: "showery", 81: "showery", 82: "violent showers",
    95: "thundery", 96: "thundery", 99: "thundery",
}


def _weather_code(code: object) -> str:
    try:
        return _WMO.get(int(code), "unremarkable")  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "unremarkable"


# --------------------------------------------------------------------------
# notes — port of take_notes.py
# --------------------------------------------------------------------------

def notes_dir() -> Path:
    path = get_home() / "notes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_note(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "There was nothing to write down, sir."
    stamp = datetime.now().isoformat(timespec="seconds").replace(":", "-")
    path = notes_dir() / f"{stamp}-note.txt"
    path.write_text(text, encoding="utf-8")
    return f"Noted, sir. Saved to {path}"


def list_notes(limit: int = 10) -> str:
    files = sorted(notes_dir().glob("*-note.txt"), reverse=True)[:limit]
    if not files:
        return "There are no notes yet, sir."
    lines = [f"- {f.stem[:19]}: {f.read_text(encoding='utf-8', errors='replace')[:80]}" for f in files]
    return "Your latest notes, sir:\n" + "\n".join(lines)


# --------------------------------------------------------------------------
# screenshot — port of take_screenshot.py, on this repo's capture layer
# --------------------------------------------------------------------------

def screenshot(name: str = "") -> str:
    try:
        from jarvis.core import capture

        shot = capture.capture_screen()
        destination = Path(shot.path)
        cleaned = "".join(ch for ch in (name or "") if ch.isalnum() or ch in "-_ ").strip()
        if cleaned:
            renamed = destination.with_name(f"{cleaned}{destination.suffix}")
            destination = Path(shutil.move(str(destination), str(renamed)))
        return f"{pick(['Capturing screen for reference', 'Screen saved', 'Stored it in my database'])}, sir. {destination}"
    except Exception as exc:
        return f"I could not capture the screen, sir: {exc}"


# --------------------------------------------------------------------------
# wolfram — port of wolfram.py
# --------------------------------------------------------------------------

def wolfram(question: str) -> str | None:
    """Short answer from Wolfram Alpha, or None when it has nothing / no key."""
    app_id = os.environ.get("WOLFRAM_APP_ID", "").strip()
    if not app_id or not question.strip():
        return None
    try:
        url = (
            "https://api.wolframalpha.com/v1/result?i="
            f"{urllib.parse.quote(question)}&appid={urllib.parse.quote(app_id)}"
        )
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            answer = response.read().decode("utf-8", errors="replace").strip()
        return answer or None
    except Exception:
        return None


# --------------------------------------------------------------------------
# browser — port of webbrowser_functions.py
# --------------------------------------------------------------------------

def _open_url(url: str) -> bool:
    """Open a URL in the user's browser. False when there is no desktop to open it on."""
    if os.environ.get("JARVIS_NO_BROWSER"):
        return False
    try:
        import webbrowser

        return webbrowser.open(url)
    except Exception:
        return False


def search(engine: str, query: str) -> tuple[str, str]:
    """Return (url, spoken sentence). The caller decides whether to open it."""
    q = urllib.parse.quote(query.strip())
    urls = {
        "google": f"https://www.google.com/search?q={q}",
        "wikipedia": f"https://en.wikipedia.org/wiki/{q}",
        "youtube": f"https://www.youtube.com/results?search_query={q}",
    }
    url = urls.get(engine, urls["google"])
    opened = _open_url(url)
    where = "Opening" if opened else "Here is"
    return url, f"{where} {engine} for {query.strip()}, sir. {url}"


def open_site(url: str) -> tuple[str, str]:
    opened = _open_url(url)
    return url, (f"Opening {url}, sir." if opened else f"Link ready, sir: {url}")


# --------------------------------------------------------------------------
# translate — port of translate.py (googletrans is unmaintained; use MyMemory)
# --------------------------------------------------------------------------

def translate(text: str, dest: str = "en", src: str = "auto") -> str:
    text = (text or "").strip()
    if not text:
        return "What would you like me to translate, sir?"
    try:
        pair = f"{'autodetect' if src == 'auto' else src}|{dest}"
        data = _get_json(
            "https://api.mymemory.translated.net/get?q="
            f"{urllib.parse.quote(text)}&langpair={urllib.parse.quote(pair)}"
        )
        translated = (data.get("responseData") or {}).get("translatedText")
        if not translated:
            return "The translation service returned nothing, sir."
        return f"In {dest}: {translated}"
    except Exception:
        return "The translation service is unreachable, sir."


# --------------------------------------------------------------------------
# music — port of playmusic.py, without pygame
# --------------------------------------------------------------------------

MUSIC_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}


def music_dir() -> Path:
    override = os.environ.get("JARVIS_MUSIC_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / "Music"


def list_music() -> list[Path]:
    directory = music_dir()
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.suffix.lower() in MUSIC_EXTENSIONS)


def play_music() -> str:
    tracks = list_music()
    if not tracks:
        return (
            f"I found no music in {music_dir()}, sir. "
            "Point JARVIS_MUSIC_DIR at your library and ask again."
        )
    track = random.choice(tracks)
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(str(track))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(track)])
        else:
            subprocess.Popen(["xdg-open", str(track)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        return f"I could not start playback, sir: {exc}"
    return f"Playing {track.name}, sir."


# --------------------------------------------------------------------------
# power — port of power_options.py, cross-platform
# --------------------------------------------------------------------------

def power_command(action: str, delay_seconds: int = 1) -> list[str]:
    """The command that would be run. Building it is separate from running it
    so the confirmation gate can show the user exactly what it is."""
    system = platform.system()
    if system == "Windows":
        flag = "/r" if action == "restart" else "/s"
        return ["shutdown", flag, "/t", str(delay_seconds)]
    if system == "Darwin":
        return ["sudo", "shutdown", "-r" if action == "restart" else "-h", "now"]
    return ["shutdown", "-r" if action == "restart" else "-h", f"+{max(delay_seconds // 60, 0)}"]


def run_power_command(action: str, delay_seconds: int = 1) -> str:
    command = power_command(action, delay_seconds)
    try:
        subprocess.Popen(command)
    except Exception as exc:
        return f"The system refused the {action} command, sir: {exc}"
    return f"{action.capitalize()} initiated, sir. It was a pleasure."


# --------------------------------------------------------------------------
# OCR — port of software_AI/computer-vision/text-extractor.py
# --------------------------------------------------------------------------

def extract_text(image_path: str) -> str:
    path = Path(image_path).expanduser()
    if not path.exists():
        return f"There is no image at {path}, sir."
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError:
        return (
            "Text extraction needs pytesseract and Pillow, sir, plus the Tesseract binary. "
            "Try: pip install pytesseract pillow"
        )
    try:
        text = pytesseract.image_to_string(Image.open(path)).strip()
    except Exception as exc:
        return f"I could not read that image, sir: {exc}"
    return text or "I found no readable text in that image, sir."
