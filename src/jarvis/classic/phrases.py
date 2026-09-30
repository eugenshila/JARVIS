"""
classic/phrases.py — intent phrases and spoken responses.

Ported from ``software_AI/natural-language-processing/action_phrases.py`` of
KKshitiz/J.A.R.V.I.S (MIT). The lists are kept close to the originals because
they *are* the character of that assistant; a few obvious synonyms were added
so typed input matches as readily as dictated input.

Naming follows the upstream convention: ``*_i`` is what the user may say,
``*_r`` is what JARVIS may answer, and a trailing ``2`` marks the second turn
of a two-step exchange.
"""

from __future__ import annotations

WAKE_WORDS = ["jarvis", "hey jarvis", "ok jarvis"]

# Generic yes/no.
affirmative_i = ["yes", "yep", "sure", "do it", "just do it", "go for it", "go on", "yeah", "ya", "y"]
negative_i = ["no", "nope", "stop", "don't do it", "dont do it", "wait", "give me some time", "let me think", "n"]

affirmative_r = ["yes sir", "doing it for you", "working on it", "i am on it, sir", "ok, i'll do it"]
negative_r = ["sorry sir, i have not been programmed to do so", "i am unable to do it, sir"]

# Standby check.
check_i = [
    "are you awake", "are you up", "are you there", "are you dead", "are you alive yet",
    "are you alive", "daddy's home", "wake up", "wake up daddy's home", "status", "you there",
]
check_r = [
    "at your service, sir", "i'm here, sir", "for you sir, always",
    "i am feeding on electricity already", "consuming memory, sir", "welcome home, sir",
]

# Greetings.
greet_i = ["hey", "hi", "yo", "howdy", "hola", "hello", "helloo", "good morning", "good evening"]
greet_r = [
    "hello, jarvis here, how are you", "hi, nice to meet you!", "hello, how can i help you",
    "hi, i am jarvis", "jarvis here, how can i help you",
]

# Music.
playmusic_i = [
    "turn up the heat", "play some music", "party time", "i think the atmosphere is a little tensed",
    "let's do some work", "lets do some work", "it's showtime", "its showtime", "play music",
]
playmusic_r = ["playing music", "on it sir", "ok sir", *affirmative_r]
stopmusic_i = ["stop music", "stop the music"]
pausemusic_i = ["pause", "pause music"]
unpausemusic_i = ["unpause", "unpause music", "resume music", "resume"]
mute_i = ["shut up", "mute", "sounds off", "silence"]

# Power.
shutdown_i = ["shut down", "shutdown", "nuke it", "time to go to sleep", "go to sleep", "go get some rest"]
shutdown_r = [
    "are you sure?", "system will shut down. do you want to continue?",
    "all functions will suspend. continue?",
]
restart_i = ["restart", "reboot", "restart the system", "reboot the system"]

# Screenshot.
screenshot_i = ["take screenshot", "take a screenshot", "capture the screen", "save the screen", "capture it"]
screenshot_r = [
    "name?", "what should be the name?", "filename?", "what should be the filename, sir?",
    "what shall i name it, sir?",
]
screenshot_i2 = ["anything you wish", "you decide", "decide yourself", "i don't know", "anything"]
screenshot_r2 = ["capturing screen for reference", "screen saved", "stored it in my database"]

# Jokes.
joke_i = [
    "tell me a joke", "do you have a joke for me", "amuse me", "make me laugh",
    "i am feeling sad", "tell a joke", "joke",
]
joke_r = ["here we go", "joke time", "hear me carefully", "hear out", "here's a programmer joke for you"]

# Hardware.
battery_i = [
    "check battery usage", "check battery health", "check battery", "battery status",
    "power status", "check battery status", "check system battery", "battery",
]
ram_i = ["check virtual memory", "ram usage", "check ram usage", "memory usage", "check memory usage", "ram"]
cpu_i = ["check cpu usage", "check cpu health", "cpu usage", "cpu"]
cpu_r = [
    "would you like to know usage for all cpu cores?",
    "sir, shall i enumerate the usages of all the cores?",
]

# Notes.
notes_i = ["make a note", "write this down", "remember this", "type this", "take a note", "note"]
notes_r = ["what would you like to write", "what would you like to remember"]
notes_r2 = ["noted", "i've made a note of it", "saved it in the notes directory"]

# Weather.
weather_i = [
    "check weather", "what's the weather", "whats the weather", "how's the sky", "hows the sky",
    "do i need to carry an umbrella", "how about a picnic", "weather",
]
weather_r = ["which city would you like to check?"]

# Web shortcuts — upstream had these in webbrowser_functions.py but never wired
# them into the command table. They are wired in here.
search_google_i = ["search google for", "google", "search for", "search the web for"]
search_wikipedia_i = ["search wikipedia for", "wikipedia", "look up on wikipedia"]
search_youtube_i = ["search youtube for", "youtube", "play on youtube"]
open_site_i = {
    "open google": "https://www.google.com/",
    "open youtube": "https://www.youtube.com/",
    "open facebook": "https://www.facebook.com/",
    "open instagram": "https://www.instagram.com/",
}

# Translate.
translate_i = ["translate"]

# Time / greeting sequence.
time_i = ["what time is it", "time", "what's the time", "whats the time", "tell me the time"]

# Quit.
self_destruct_i = ["close", "quit", "self destruct", "goodbye", "bye"]
self_destruct_r = ["shutting down my side of the conversation, sir", "goodbye, sir"]

__all__ = [name for name in dir() if name.endswith(("_i", "_r", "_i2", "_r2")) or name == "WAKE_WORDS"]
