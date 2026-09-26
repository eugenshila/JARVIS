# The holographic interface — `web/`

The Iron Man interface in `web/` is a port of
[adewaskar/jarvis](https://github.com/adewaskar/jarvis) (MIT), adapted so it
runs on **this** repository's brain as well as on Claude Code.

Say **"Hey Jarvis"**, he wakes, listens and answers — a React + Vite +
Three.js + GLSL face in the browser, a small Node bridge as the nervous system,
and a brain behind it.

```
  ┌─ browser (the face) ───────────────┐        ┌─ bridge (the nerves) ────────────┐
  │  "Hey Jarvis" wake word            │        │  Node · web/bridge/server.mjs    │
  │  local VAD  →  speech to text      │   ws   │                                  │
  │  reactor UI (Three.js + GLSL)      │◄─────► │   brain=jarvis → Python API      │
  │  text to speech                    │  8787  │   brain=claude → Claude Agent SDK│
  │  heads-up display                  │        │  permission gate (decideTool)    │
  └────────────────────────────────────┘        └──────────────────────────────────┘
                                                              │ http 8000
                                                 ┌────────────▼─────────────────────┐
                                                 │  jarvis serve — src/jarvis       │
                                                 │  agents · engines · Business OS  │
                                                 │  memory · tools · voice          │
                                                 └──────────────────────────────────┘
```

## Run it

```bash
jarvis web                    # our Python brain (default) — no Claude subscription needed
jarvis web --engine openai    # pick the engine the Python brain uses
jarvis web --agent business_os
jarvis web --brain claude     # upstream behaviour: Claude Code, headless
```

`jarvis web` starts all three processes (API, bridge, face), wires the ports
together and prints the URL. Open it in a **real Chrome or Edge window** — an
embedded preview pane blocks the microphone, so the interface looks perfectly
alive and never hears you.

Node 20+ is required; the first run does `npm install` for you. Without the CLI:

```bash
cd web
npm install
npm run start:jarvis          # bridge on our Python brain + the face
npm start                     # bridge on Claude Code + the face (upstream)
```

## What changed from upstream

Everything upstream still works unchanged. The additions are:

| Change | File | Why |
|---|---|---|
| **A second brain** — the bridge can be driven by our Python JARVIS over its HTTP API | `web/bridge/jarvis-brain.mjs` | Upstream requires a Claude Code subscription. This repo already has agents, engines, memory and the Business OS; the same face now drives them, including fully offline with the mock engine. |
| `JARVIS_BRAIN=claude\|jarvis\|auto` and a brain-aware `/health` + banner | `web/bridge/server.mjs` | One switch, and the running process says which brain answered instead of leaving a silent assistant to be diagnosed by guesswork. |
| Wildcard entries in `JARVIS_ALLOWED_ORIGINS` (`https://*.example.app`) | `web/bridge/server.mjs` | Remote dev hosts have a name you cannot know in advance. Still default-deny: the scheme and domain must match, `*` covers exactly one label. |
| Same-origin `/bridge` proxy, `host: 0.0.0.0`, `allowedHosts` | `web/vite.config.ts` | `ws://localhost:8787` means the *viewer's* machine when the page is served anywhere but locally, and the socket silently connects to nothing. Proxying keeps page, socket and media endpoints on one origin — which the page's CSP already allows. |
| Bridge URL derived from the page origin when it is not localhost | `web/src/config.ts` | Same reason, from the browser's side. Local behaviour is unchanged. |
| `jarvis web` | `src/jarvis/cli/web.py` | One command for brain + bridge + face, with the ports and origins wired together. |

## The brain protocol

`jarvis-brain.mjs` speaks the exact frames the browser already understands, so
`src/lib/bridge.ts` cannot tell the two brains apart:

| Direction | Frame |
|---|---|
| browser → bridge | `{type:'ask', text, id}`, `{type:'interrupt'}`, `{type:'reply', id, …}` |
| bridge → browser | `{type:'ready', servers}`, `{type:'text', delta, ask}`, `{type:'tool', name, ask}`, `{type:'done', text, ask}`, `{type:'error', message}` |

Upstream it streams Claude Agent SDK events; here it streams
`POST /run` (`text/event-stream`) from `jarvis.server.api`, with the rolling
transcript passed as `context` so every agent in the registry works — including
the ones that build their own prompts (Iron Man, Business OS).

## Configuration

Bridge (environment variables):

| Variable | Default | Effect |
|---|---|---|
| `JARVIS_BRAIN` | `auto` | `jarvis`, `claude`, or auto-detect (Claude if it is installed and logged in) |
| `JARVIS_API_URL` | `http://127.0.0.1:8000` | Where the Python brain listens |
| `JARVIS_AGENT` | `ironman` | Agent that answers (`business_os`, `adhd_coach`, `deep_research`, …) |
| `JARVIS_ENGINE` | — | Engine override per turn: `openai`, `ollama`, `auto`, `mock` |
| `JARVIS_TURN_TIMEOUT_MS` | `120000` | How long one spoken turn may take |
| `JARVIS_BRIDGE_PORT` | `8787` | Bridge port |
| `JARVIS_ALLOWED_ORIGINS` | local dev | Extra origins, wildcards allowed |
| `JARVIS_ALLOW_WRITES` | off | `1` permits effectful tools (Claude brain) |
| `ELEVENLABS_API_KEY` | — | Optional: better voice + Scribe transcription |

Everything else — `VITE_*` frontend settings, the ElevenLabs upgrade path, the
tool gate, the HUD tools — behaves exactly as documented in `web/README.md`,
which is the upstream README kept intact.

## Voice

With no keys at all the browser's own `SpeechRecognition` and `speechSynthesis`
do the work, so it runs offline. Add `ELEVENLABS_API_KEY` to the bridge (or to
the `elevenlabs` MCP server in `~/.claude.json`) and both the voice and the
transcription upgrade themselves on the next boot — there is no flag to set.

## Credits

Upstream: [adewaskar/jarvis](https://github.com/adewaskar/jarvis), MIT. The
licence ships at `web/LICENSE` and the upstream README at `web/README.md`.
