# Notice

This directory is a port of **[adewaskar/jarvis](https://github.com/adewaskar/jarvis)**
— "J.A.R.V.I.S for automating your daily tasks using Claude Code" — used under
the MIT licence. The original licence is kept verbatim in `LICENSE`, and the
original documentation in `README.md`.

## Modifications made for JARVIS SHILATECH

- `bridge/jarvis-brain.mjs` (new) — drives the same WebSocket protocol from this
  repository's Python brain (`src/jarvis`, served by `jarvis serve`), so the
  interface works without a Claude Code subscription.
- `bridge/server.mjs` — brain selection (`JARVIS_BRAIN=claude|jarvis|auto`),
  brain reported on `/health` and in the boot banner, wildcard origins in
  `JARVIS_ALLOWED_ORIGINS`.
- `vite.config.ts` — binds all interfaces, allows remote hosts, and proxies
  `/bridge` (WebSocket + HTTP) so page and bridge share one origin.
- `src/config.ts` — derives the bridge URL from the page origin when the page is
  not served from localhost.
- `package.json` — `bridge:jarvis`, `bridge:claude`, `start:jarvis` scripts.

Audio in `public/audio/` ships from upstream for the demo; see
`public/audio/CREDITS.md`.
