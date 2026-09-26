# Jarvis desktop prototype

## Circular JARVIS HUD with Ollama

The circular cyan HUD opens by default in the React interface. Its chat uses
**`qwen2.5:3b` through Ollama on your computer**. The status badge checks that
Ollama is running and the model is installed. Conversation context is kept in
the open browser window; the three priorities are saved in browser local storage.

On Windows, install [Ollama](https://ollama.com/download), Python 3.10+ and
Node.js, then double-click `deploy\windows\RUN-OLLAMA-HUD.bat`. The launcher
pulls the model if needed, installs project dependencies, starts the API and
web interface, and opens `http://localhost:5173`. It also starts a minimized
microphone companion: two quick claps open the HUD and play a short response.
If clap sensitivity needs adjustment, set `JARVIS_CLAP_THRESHOLD` (default
`0.18`, between `0` and `1`) before launching. The microphone audio stays in
the companion process and is not sent to Ollama.

To start JARVIS automatically **after Windows sign-in**, run the launcher once,
then double-click `deploy\windows\ENABLE-HUD-STARTUP.bat`. To remove that startup
entry, double-click `deploy\windows\DISABLE-HUD-STARTUP.bat`. Startup cannot
show a desktop or listen to a microphone before the user signs in. A greeting
uses a Windows installed voice, preferring UK English when available. It is
not the film actor's voice. If the mic is unavailable, the HUD still supports
typing.

To run it manually:

```text
ollama pull qwen2.5:3b
python -m pip install -e .
python -m uvicorn jarvis.server.api:app --host 127.0.0.1 --port 8000
```

In another terminal, run `cd frontend`, `npm ci`, then `npm run dev`. Open
`http://localhost:5173`. Ollama normally starts in the background on Windows;
if the badge shows **OLLAMA OFFLINE**, start the Ollama app. The browser microphone
and spoken reply buttons depend on browser support and microphone permission.

The HUD is a visual assistant with local conversation, voice controls, clap
activation, and a small priority list. The clap opens the HUD; to dictate a
question, press its microphone button. Browser speech recognition may depend
on the browser's service, while Ollama chat stays local. Its chat does not yet
operate devices, email, calendar, or desktop files, and it does not claim to
have done those actions. The circular
reactor is an interface graphic, not a live battery or machine diagnostic.

A small Windows friendly desktop assistant built with Python's standard library. It can browse a local prompt library, prepare meeting briefs from details you paste, copy prompts, and ask an OpenAI compatible chat API to draft a response. The app runs without an API key in copy mode.

## Run

1. Install Python 3.10 or newer from python.org, including Tkinter.
2. Download or clone this repository.
3. Run `python app.py` from its folder.

For AI responses, set `OPENAI_API_KEY` in your environment before launching. The default endpoint is `https://api.openai.com/v1/chat/completions`, and the default model is `gpt-4o-mini`. You can override these with `JARVIS_API_URL` and `JARVIS_MODEL`. The API key stays in the environment and is never written to project files. API calls send the prompt and pasted context to your chosen provider.

To use [Jarvis Public Prompts](https://github.com/mihaiwillberich/jarvis-public-prompts), download its ZIP from GitHub, extract it, and select its root directory using **Open prompt folder**. The app reads Markdown files locally and extracts the first fenced prompt under `## The prompt`. It also ships with an original meeting brief starter prompt, so you can try it immediately.

## Current scope

This first version accepts pasted meeting details and files you choose as context. It does not automatically read your screen, calendar, email, or contacts. Add those integrations only after choosing the provider and permissions you want. It does not send email or modify calendar events.

The external prompt library is maintained separately and is MIT licensed; if you redistribute a copied set of its prompts, include its LICENSE file.
