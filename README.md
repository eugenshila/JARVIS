# J.A.R.V.I.S — SHILATECH

Personal AI, on personal devices. Three faces, one brain:

| Face | Command | What it is |
|---|---|---|
| **Holographic web UI** | `jarvis web` | Iron Man interface in the browser — wake word, voice, arc reactor, heads-up display. React + Three.js + GLSL, ported from [adewaskar/jarvis](https://github.com/adewaskar/jarvis) (MIT). |
| **Desktop HUD** | `python app.py` | Tkinter circular HUD that stays open, works offline. |
| **CLI** | `jarvis chat` | Agents, Business OS, memory, tools, voice. |

The brain is the Python package in `src/jarvis`: agents (Iron Man, Business OS,
ADHD coach, deep research, code assistant), engines (OpenAI, Ollama, vLLM, MLX,
LiteLLM, mock), memory, tools and a FastAPI server.

## Quick start

```bash
pip install -e ".[server]"
jarvis web                     # holographic UI on http://localhost:5173
```

Open it in a **real Chrome or Edge window** — embedded preview panes block the
microphone — click **INITIALISE** and say **"Hey Jarvis"**. Node 20+ is needed
for the web face; the first run installs its dependencies for you.

Prefer the other faces:

```bash
python app.py                  # desktop HUD
jarvis chat --interactive      # CLI
jarvis serve                   # API only, on :8000
```

## Which brain answers

`jarvis web` runs our Python brain by default, so no Claude subscription is
needed and the mock engine works with no network at all. The upstream brain is
one flag away:

```bash
jarvis web --brain claude      # Claude Code, headless (needs a Claude Code login)
jarvis web --engine openai     # our brain, OpenAI engine
jarvis web --agent business_os # our brain, Business OS agent
```

See [docs/WEB_HOLOGRAM.md](docs/WEB_HOLOGRAM.md) for the architecture, the
bridge protocol and every setting.

## Is my build complete?

```bash
jarvis selftest                # imports every module in the manifest, checks the payload
```

This is what the MSI now ships with — the installer carries the complete source
payload, not just two executables, and `selftest` fails loudly if anything is
missing.

## Desktop prototype notes

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
