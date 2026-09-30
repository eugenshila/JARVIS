"""
classic/router.py — text in, JARVIS out.

Upstream's ``main.py`` interleaved three things in one ``matchCommand()``
ladder: matching an intent, asking a follow-up question over the microphone,
and performing the action. That works for exactly one interface (a blocking
voice loop on one machine) and cannot be tested without a microphone.

Here the ladder is a pure-ish function: a string goes in, a
:class:`ClassicReply` comes out. The follow-up questions upstream asked by
voice ("which city?", "what should I name it?") become either inline arguments
("weather in Berlin") or a reply carrying ``expects`` so the caller can prompt
for the missing piece — HUD, CLI and agent tool all use the same code path.

Irreversible actions never execute here. ``shutdown`` returns a reply with
``confirm_token`` set, produced by :mod:`jarvis.core.confirm`; a human presses
the button in the UI before anything happens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from jarvis.classic import phrases as P
from jarvis.classic import skills


@dataclass
class ClassicReply:
    """One answer from the classic assistant."""

    intent: str
    speech: str
    data: dict[str, Any] = field(default_factory=dict)
    #: Set when the reply is a question and the next user message is the answer
    #: (e.g. ``"weather"`` after "which city, sir?").
    expects: str | None = None
    #: Present when a human must approve before anything happens.
    confirm_token: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "speech": self.speech,
            "data": self.data,
            "expects": self.expects,
            "confirm_token": self.confirm_token,
        }


#: What the HUD lists as suggestion chips, and what `jarvis classic --list`
#: prints. Kept next to the router so a new intent cannot be added without the
#: interfaces noticing.
COMMANDS: list[dict[str, str]] = [
    {"intent": "check", "example": "are you there", "description": "Standby check"},
    {"intent": "greet", "example": "hello", "description": "Greeting"},
    {"intent": "time", "example": "what time is it", "description": "Local time"},
    {"intent": "weather", "example": "weather in London", "description": "Current conditions"},
    {"intent": "joke", "example": "tell me a joke", "description": "A programmer joke"},
    {"intent": "battery", "example": "battery status", "description": "Battery charge and runtime"},
    {"intent": "ram", "example": "ram usage", "description": "Memory pressure"},
    {"intent": "cpu", "example": "cpu usage", "description": "Processor load"},
    {"intent": "note", "example": "make a note buy milk", "description": "Save a note"},
    {"intent": "notes_list", "example": "read my notes", "description": "Recent notes"},
    {"intent": "screenshot", "example": "take a screenshot", "description": "Capture the screen"},
    {"intent": "music", "example": "play some music", "description": "Play from your music folder"},
    {"intent": "search", "example": "search google for arc reactor", "description": "Google, Wikipedia or YouTube"},
    {"intent": "open_site", "example": "open youtube", "description": "Open a known site"},
    {"intent": "translate", "example": "translate good morning to french", "description": "Translate a phrase"},
    {"intent": "ocr", "example": "read text from ~/news.png", "description": "Extract text from an image"},
    {"intent": "shutdown", "example": "shut down", "description": "Power off (asks first)"},
    {"intent": "restart", "example": "restart", "description": "Reboot (asks first)"},
    {"intent": "quit", "example": "goodbye", "description": "End the session"},
]

_LANGUAGES = {
    "english": "en", "french": "fr", "spanish": "es", "german": "de", "italian": "it",
    "portuguese": "pt", "dutch": "nl", "russian": "ru", "ukrainian": "uk", "polish": "pl",
    "hindi": "hi", "japanese": "ja", "korean": "ko", "chinese": "zh", "arabic": "ar",
    "turkish": "tr", "swedish": "sv", "norwegian": "no", "danish": "da", "finnish": "fi",
    "czech": "cs", "greek": "el", "hebrew": "he", "romanian": "ro", "hungarian": "hu",
}


def normalize(text: str) -> str:
    """Lowercase, strip punctuation and the wake word — upstream did the last
    part with a bare ``replace("jarvis", "")``, which also mangled the word in
    the middle of a sentence."""
    cleaned = (text or "").strip().lower()
    cleaned = re.sub(r"[^\w\s%+/.:@-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    for wake in sorted(P.WAKE_WORDS, key=len, reverse=True):
        if cleaned.startswith(wake):
            cleaned = cleaned[len(wake):].strip(" ,.")
            break
    return cleaned


def _matches(command: str, intents: list[str]) -> bool:
    return command in intents or any(command.startswith(f"{i} ") for i in intents)


def _after(command: str, intents: list[str]) -> str:
    """The remainder of the sentence after whichever intent phrase matched."""
    for intent in sorted(intents, key=len, reverse=True):
        if command == intent:
            return ""
        if command.startswith(f"{intent} "):
            return command[len(intent):].strip()
    return command


class ClassicRouter:
    """Stateful only in the small way the original was: it remembers the one
    question it just asked, so "London" after "which city, sir?" works."""

    def __init__(self) -> None:
        self._pending: str | None = None

    # -- follow-ups ------------------------------------------------------
    def _resume(self, command: str) -> ClassicReply | None:
        pending, self._pending = self._pending, None
        if pending is None:
            return None
        if pending == "weather":
            return ClassicReply("weather", skills.weather(command), {"city": command})
        if pending == "note":
            return ClassicReply("note", skills.save_note(command), {"text": command})
        if pending == "screenshot":
            name = "" if command in P.screenshot_i2 else command
            return ClassicReply("screenshot", skills.screenshot(name), {"name": name})
        if pending == "cpu":
            return ClassicReply("cpu", skills.cpu_usage(per_core=command in P.affirmative_i))
        if pending in {"shutdown", "restart"}:
            if command in P.affirmative_i:
                return self._power(pending, confirmed_by_voice=True)
            return ClassicReply(pending, "Standing down, sir.")
        return None

    # -- power -----------------------------------------------------------
    def _power(self, action: str, confirmed_by_voice: bool = False) -> ClassicReply:
        command = skills.power_command(action)
        detail = " ".join(command)
        try:
            from jarvis.core import confirm as confirm_gate

            pending = confirm_gate.request(
                title=f"{action.capitalize()} this computer",
                detail=f"JARVIS would run: {detail}",
                run=lambda: skills.run_power_command(action),
            )
            token = getattr(pending, "token", None) or (
                pending.get("token") if isinstance(pending, dict) else None
            )
            speech = skills.pick(P.shutdown_r) if action == "shutdown" else "Confirm the reboot, sir?"
            return ClassicReply(
                action,
                f"{speech} I will run: {detail}",
                {"command": command, "confirmed_by_voice": confirmed_by_voice},
                confirm_token=token,
            )
        except Exception:
            # No confirmation gate available (e.g. bare import of this module):
            # still refuse to act on a transcript alone.
            self._pending = action
            return ClassicReply(
                action,
                f"{skills.pick(P.shutdown_r)} I would run: {detail}",
                {"command": command},
                expects=action,
            )

    # -- main ladder -----------------------------------------------------
    def handle(self, text: str) -> ClassicReply:
        command = normalize(text)
        if not command:
            return ClassicReply("empty", skills.pick(P.check_r))

        resumed = self._resume(command)
        if resumed is not None:
            return resumed

        if command in {"help", "what can you do", "commands", "abilities"}:
            listing = "\n".join(f"- {c['example']} — {c['description']}" for c in COMMANDS)
            return ClassicReply("help", f"Here is what I can do, sir:\n{listing}", {"commands": COMMANDS})

        # Standby / greetings / time.
        if command in P.check_i:
            return ClassicReply("check", skills.pick(P.check_r))
        if command in P.greet_i:
            return ClassicReply("greet", f"{skills.pick(P.greet_r)}. {skills.greet()}")
        if command in P.time_i:
            return ClassicReply("time", skills.current_time())
        if command in P.self_destruct_i:
            return ClassicReply("quit", skills.pick(P.self_destruct_r), {"close": True})

        # Music.
        if _matches(command, P.playmusic_i):
            return ClassicReply("music", f"{skills.pick(P.playmusic_r)}. {skills.play_music()}")
        if command in P.stopmusic_i or command in P.pausemusic_i or command in P.mute_i:
            return ClassicReply("music_stop", "Silencing playback, sir.", {"action": "stop"})
        if command in P.unpausemusic_i:
            return ClassicReply("music_resume", "Resuming, sir.", {"action": "resume"})

        # Hardware.
        if _matches(command, P.battery_i):
            return ClassicReply("battery", skills.battery_status())
        if _matches(command, P.ram_i):
            return ClassicReply("ram", skills.ram_usage())
        if _matches(command, P.cpu_i):
            rest = _after(command, P.cpu_i)
            if "core" in rest or "all" in rest:
                return ClassicReply("cpu", skills.cpu_usage(per_core=True))
            self._pending = "cpu"
            return ClassicReply("cpu", skills.pick(P.cpu_r), expects="cpu")

        # Jokes.
        if _matches(command, P.joke_i):
            return ClassicReply("joke", f"{skills.pick(P.joke_r)}. {skills.joke()}")

        # Notes.
        if command in {"read my notes", "read notes", "list notes", "my notes", "show notes"}:
            return ClassicReply("notes_list", skills.list_notes())
        if _matches(command, P.notes_i):
            rest = _after(command, P.notes_i)
            if rest:
                return ClassicReply("note", skills.save_note(rest), {"text": rest})
            self._pending = "note"
            return ClassicReply("note", skills.pick(P.notes_r), expects="note")

        # Weather.
        if _matches(command, P.weather_i):
            rest = _after(command, P.weather_i)
            city = re.sub(r"^(in|for|at)\s+", "", rest).strip()
            if city:
                return ClassicReply("weather", skills.weather(city), {"city": city})
            self._pending = "weather"
            return ClassicReply("weather", skills.pick(P.weather_r), expects="weather")

        # Screenshot.
        if _matches(command, P.screenshot_i):
            rest = _after(command, P.screenshot_i)
            if rest:
                return ClassicReply("screenshot", skills.screenshot(rest), {"name": rest})
            self._pending = "screenshot"
            return ClassicReply("screenshot", skills.pick(P.screenshot_r), expects="screenshot")

        # Power.
        if _matches(command, P.shutdown_i):
            return self._power("shutdown")
        if _matches(command, P.restart_i):
            return self._power("restart")

        # Web.
        for phrase, url in P.open_site_i.items():
            if command == phrase:
                opened_url, speech = skills.open_site(url)
                return ClassicReply("open_site", speech, {"url": opened_url})
        for engine, intents in (
            ("wikipedia", P.search_wikipedia_i),
            ("youtube", P.search_youtube_i),
            ("google", P.search_google_i),
        ):
            if _matches(command, intents):
                query = re.sub(r"^(for|about)\s+", "", _after(command, intents)).strip()
                if not query:
                    return ClassicReply("search", f"What should I look for on {engine}, sir?")
                url, speech = skills.search(engine, query)
                return ClassicReply("search", speech, {"engine": engine, "query": query, "url": url})

        # Translate: "translate good morning to french".
        if _matches(command, P.translate_i):
            rest = _after(command, P.translate_i)
            dest = "en"
            match = re.search(r"\s+(?:to|into)\s+([a-z-]+)$", rest)
            if match:
                word = match.group(1)
                dest = _LANGUAGES.get(word, word if len(word) <= 3 else "en")
                rest = rest[: match.start()].strip()
            if not rest:
                return ClassicReply("translate", "What would you like me to translate, sir?")
            return ClassicReply("translate", skills.translate(rest, dest), {"text": rest, "dest": dest})

        # OCR: "read text from <path>".
        ocr = re.match(r"^(?:read|extract)\s+(?:the\s+)?text\s+(?:from\s+)?(.+)$", command)
        if ocr:
            target = ocr.group(1).strip()
            return ClassicReply("ocr", skills.extract_text(target), {"path": target})

        # Wolfram fallback, exactly where upstream put it.
        answer = skills.wolfram(command)
        if answer:
            return ClassicReply("wolfram", answer, {"question": command})

        return ClassicReply(
            "unknown",
            "Sorry sir, I cannot understand you. Say 'help' for what I can do.",
            {"suggestions": [c["example"] for c in COMMANDS[:6]]},
        )


_DEFAULT = ClassicRouter()


def handle(text: str) -> ClassicReply:
    """Module-level convenience using a shared router (so follow-ups work)."""
    return _DEFAULT.handle(text)
