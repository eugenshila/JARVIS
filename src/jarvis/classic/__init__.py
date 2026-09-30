"""
jarvis.classic — the 2020 "Iron man inspired Personal virtual assistant" ported in.

ORIGIN
    Upstream: https://github.com/KKshitiz/J.A.R.V.I.S (MIT, (c) 2020 Kshitiz
    Kamal). That project is a Windows-first, voice-loop script: ``main.py``
    listens on a microphone, string-matches the transcript against lists of
    intent phrases in ``action_phrases.py``, and calls one of a dozen small
    modules (weather, jokes, notes, screenshots, hardware stats, Wolfram,
    browser shortcuts, power options, music).

WHAT CHANGED IN THE PORT
    The *intent tables and the personality* are kept — that is the part worth
    having. The plumbing around them is replaced so it fits this repository:

      * No global mutable state, no hardcoded ``C:\\Users\\skili\\...`` paths,
        and no API keys committed in source. Keys come from the environment;
        weather now uses the key-free Open-Meteo API so it works out of the box.
      * Speech in/out is NOT re-implemented here. This package is text in,
        text out, so the same router serves the HTTP API, the React HUD, the
        agent tool and the CLI. Voice is the caller's business
        (``jarvis.speech``, or the browser's Web Speech API in the HUD).
      * Every third-party dependency is optional and probed at call time. A
        missing ``psutil`` degrades one command to an explanatory sentence
        instead of breaking the import of the whole assistant.
      * Irreversible actions (shutdown/restart) go through
        :mod:`jarvis.core.confirm` rather than firing ``shutdown /s /t 1``
        straight off a speech transcript.
"""

from jarvis.classic.router import ClassicReply, ClassicRouter, handle

__all__ = ["ClassicReply", "ClassicRouter", "handle"]
