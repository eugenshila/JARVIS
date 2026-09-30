# Classic J.A.R.V.I.S

The 2020 assistant from [KKshitiz/J.A.R.V.I.S](https://github.com/KKshitiz/J.A.R.V.I.S)
now runs inside this repository — same commands, same deadpan "sir", but as a
library, an HTTP endpoint, a CLI command, an agent tool and a HUD page rather
than a Windows-only microphone loop.

## Try it

```bash
jarvis classic --list                 # every command it understands
jarvis classic "weather in Oslo"
jarvis classic "tell me a joke"
jarvis classic --repl                 # the original loop, typed instead of spoken
```

In the interface:

```bash
python -m uvicorn jarvis.server.api:app --host 127.0.0.1 --port 8000
cd frontend && npm ci && npm run dev   # http://localhost:5173
```

The dashboard's top-right **CLASSIC J.A.R.V.I.S** button opens the console.
Click a command in the left rail, type one, or press **🎙 SPEAK** to dictate.
Replies are read back with the browser voice (UK English when available);
untick **VOICE** for silence.

## Commands

| Say | Does |
| --- | --- |
| `are you there`, `wake up` | Standby check |
| `hello`, `good morning` | Greeting plus the time |
| `what time is it` | Local time |
| `weather`, `weather in Berlin` | Current conditions (asks for the city if you leave it out) |
| `tell me a joke` | pyjokes when installed, a built-in list otherwise |
| `battery status`, `ram usage`, `cpu usage` | Machine stats (`cpu usage` asks about per-core) |
| `make a note buy milk`, `read my notes` | Notes under `~/.jarvis/notes` |
| `take a screenshot` | Uses this repo's capture layer, honouring its consent flag |
| `play some music` | Random track from `JARVIS_MUSIC_DIR` or `~/Music` |
| `search google for …`, `wikipedia …`, `youtube …`, `open youtube` | Web shortcuts |
| `translate good morning to french` | Translation |
| `read text from ~/news.png` | OCR (needs `pytesseract`, Pillow, Tesseract) |
| `shut down`, `restart` | **Asks a human first** — see below |
| `help` | The list above, from the assistant itself |

Anything unmatched falls through to Wolfram Alpha when `WOLFRAM_APP_ID` is set,
exactly as upstream did, and otherwise gets "Sorry sir, I cannot understand you."

## Configuration

| Variable | Effect |
| --- | --- |
| `OPENWEATHER_API_KEY` | Use OpenWeatherMap instead of the key-free Open-Meteo default |
| `WOLFRAM_APP_ID` | Enable the Wolfram Alpha fallback |
| `JARVIS_MUSIC_DIR` | Music library for `play some music` |
| `JARVIS_NO_BROWSER` | Return links instead of opening a browser (headless boxes, tests) |
| `JARVIS_HOME` | Where notes and captures are written (default `~/.jarvis`) |

Nothing is required. With no keys and no optional packages installed, every
command either works or explains in one sentence what to install.

## What changed from upstream, and why

* **Text in, text out.** `main.py` upstream was a `while True` loop around a
  microphone, so each feature could only ever be used one way and none of it
  could be tested. `ClassicRouter.handle()` is a function; the CLI, the API, the
  agent tool and the HUD are four callers of the same code.
* **No committed secrets.** Upstream ships an OpenWeatherMap key, a Wolfram app
  id, `credentials.json` and a Google `token.pickle` in the repository. None of
  those were copied. Keys come from the environment, and weather defaults to a
  service that needs none.
* **No hardcoded paths.** `C:\Users\skili\Documents\GitHub\J.A.R.V.I.S\assets`
  becomes `JARVIS_HOME`, and `notepad.exe` is not launched at people.
* **Shutdown asks a human.** Upstream ran `shutdown /s /t 1` when a speech
  transcript happened to match "nuke it". Here the router builds the command,
  shows it, and hands it to `jarvis.core.confirm`; it only runs when someone
  clicks CONFIRM in the HUD (or approves the token via `/confirm/{token}/approve`).
* **Optional dependencies stay optional.** Every third-party import happens
  inside the function that needs it, so a missing `psutil` costs you one
  command, not the assistant.
* **The GUI upstream only sketched.** Its `gui/README_gui.md` listed candidate
  platforms for an interface that was never built. `frontend/src/pages/ClassicJarvis.tsx`
  is that interface, in the same React/HUD style as the rest of this repo.
* **No media copied.** Upstream carries ~200 MB of MP3s; `play some music`
  points at your own library instead.

## Where the code lives

```
src/jarvis/classic/phrases.py   intent and response lists (derived from action_phrases.py)
src/jarvis/classic/skills.py    weather, jokes, notes, stats, search, OCR, power, music
src/jarvis/classic/router.py    the intent ladder, follow-up questions, confirmation gate
src/jarvis/tools/classic_tools.py   classic_command / classic_commands agent tools
src/jarvis/server/api.py        GET /hud/classic/commands, POST /hud/classic/command
frontend/src/pages/ClassicJarvis.tsx   the console
tests/test_classic_jarvis.py    29 tests, no network or microphone needed
```

Licensing and attribution: see [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
