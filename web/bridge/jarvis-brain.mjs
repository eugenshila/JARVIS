/**
 * The SHILATECH brain — the same bridge protocol, powered by our own Python JARVIS.
 *
 * The upstream bridge runs the Claude Agent SDK, which requires a Claude Code
 * subscription. This repository already has a brain of its own: the Python
 * package in `src/jarvis` (agents, engines, tools, Business OS, memory) served
 * over FastAPI by `jarvis serve`. This module speaks the bridge's WebSocket
 * protocol to the browser and the JARVIS HTTP API upstream, so the Iron Man
 * interface is identical either way and the brain is swappable:
 *
 *   JARVIS_BRAIN=claude   Claude Code, headless (upstream behaviour)
 *   JARVIS_BRAIN=jarvis   our Python stack (OpenAI / Ollama / mock, offline-capable)
 *   JARVIS_BRAIN=auto     Claude when it is logged in, otherwise ours (default)
 *
 * The frames sent here are the same ones bridge/server.mjs sends, because the
 * browser (src/lib/bridge.ts) cannot tell the difference and must not have to:
 *   -> { type: 'ready', servers }         capabilities for the HUD
 *   -> { type: 'text', delta, ask }       streamed tokens
 *   -> { type: 'tool', name, ask }        tool badge
 *   -> { type: 'done', text, ask }        end of turn
 *   -> { type: 'error', message, ask }    spoken failure
 */

/** Where the Python API lives. `jarvis serve` binds 8000 by default. */
export const JARVIS_API_URL = (
  process.env.JARVIS_API_URL ?? 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

/** Which agent answers. `ironman` is the JARVIS persona; `business_os` knows your goals. */
export const JARVIS_AGENT = process.env.JARVIS_AGENT ?? 'ironman'

/** Engine override handed to the API per turn (openai, ollama, auto, mock, ...). */
export const JARVIS_ENGINE = process.env.JARVIS_ENGINE ?? ''

/** How long one spoken turn may take before we give up and say so. */
const TURN_TIMEOUT_MS = Number(process.env.JARVIS_TURN_TIMEOUT_MS ?? 120_000)

/**
 * Is the Python brain actually up?
 *
 * Used by the `auto` resolution at boot and by /health, so the banner can state
 * plainly which brain answered — the worst failure mode here is an interface
 * that looks alive and silently has nothing behind it.
 */
export async function jarvisApiReachable(timeoutMs = 1500) {
  try {
    const stop = AbortSignal.timeout(timeoutMs)
    const res = await fetch(`${JARVIS_API_URL}/health`, { signal: stop })
    return res.ok
  } catch {
    return false
  }
}

/** Agents and engines the API reports, shown in the HUD's systems rail. */
export async function jarvisCapabilities() {
  const out = { agents: [], engines: [] }
  try {
    const stop = AbortSignal.timeout(2000)
    const res = await fetch(`${JARVIS_API_URL}/`, { signal: stop })
    if (res.ok) {
      const body = await res.json()
      out.agents = Array.isArray(body.agents) ? body.agents : []
      out.engines = Array.isArray(body.engines) ? body.engines : []
    }
  } catch {
    /* the rail simply stays short */
  }
  return out
}

/**
 * Parse the API's `text/event-stream` into whole SSE data payloads.
 *
 * Both /run and /v1/chat/completions emit `data: {...}` lines terminated by a
 * blank line. Chunk boundaries fall anywhere, so the tail is carried over.
 */
async function* sseLines(response) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let cut
    while ((cut = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, cut).trim()
      buffer = buffer.slice(cut + 1)
      if (line.startsWith('data:')) yield line.slice(5).trim()
    }
  }
  const rest = buffer.trim()
  if (rest.startsWith('data:')) yield rest.slice(5).trim()
}

/**
 * Attach the Python brain to one browser socket.
 *
 * One conversation per socket, exactly like the Claude path: the history lives
 * here, so a dropped socket starts a clean conversation rather than replaying a
 * stale one. Returns nothing — everything happens through the socket.
 */
export function attachJarvisBrain(socket, options = {}) {
  const agent = options.agent ?? JARVIS_AGENT
  const send = (msg) => {
    if (socket.readyState === socket.OPEN) socket.send(JSON.stringify(msg))
  }

  /** The question currently being answered, echoed on every frame of its turn. */
  let answering = null
  const sendTurn = (msg) => send({ ...msg, ask: answering })

  /** Rolling transcript, trimmed so a long session cannot grow without bound. */
  const history = []
  const remember = (role, content) => {
    history.push({ role, content })
    if (history.length > 24) history.splice(0, history.length - 24)
  }

  /** In-flight turn, so a barge-in can cut it off mid-sentence. */
  let abort = null
  let turn = Promise.resolve()

  // Tell the HUD what is behind it before the first question, the way the
  // Claude path announces its MCP servers.
  void jarvisCapabilities().then(({ agents, engines }) => {
    const servers = [
      `jarvis:${agent}`,
      ...engines.map((e) => `engine:${e}`),
      ...agents.filter((a) => a !== agent).slice(0, 8).map((a) => `agent:${a}`),
    ]
    send({ type: 'ready', servers })
  })

  async function ask(text, id) {
    answering = id
    abort?.abort()
    abort = new AbortController()
    const timer = setTimeout(() => abort?.abort(), TURN_TIMEOUT_MS)

    // The API's /run takes one prompt plus context, so the transcript is passed
    // as context rather than as a message list — that keeps this working with
    // every agent in the registry, including the ones that build their own
    // prompts (Business OS, Iron Man).
    const context = history
      .map((m) => `${m.role === 'user' ? 'User' : 'JARVIS'}: ${m.content}`)
      .join('\n')

    let spoken = ''
    try {
      sendTurn({ type: 'tool', name: `jarvis__${agent}` })
      const res = await fetch(`${JARVIS_API_URL}/run`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          prompt: text,
          context,
          agent,
          engine: JARVIS_ENGINE || undefined,
          stream: true,
        }),
        signal: abort.signal,
      })

      if (!res.ok) {
        const detail = await res.text().catch(() => '')
        throw new Error(
          `the JARVIS API answered ${res.status}${detail ? ` — ${detail.slice(0, 200)}` : ''}`,
        )
      }

      for await (const payload of sseLines(res)) {
        if (payload === '[DONE]') break
        let frame
        try {
          frame = JSON.parse(payload)
        } catch {
          continue
        }
        if (frame.error) throw new Error(String(frame.error))
        // /run streams {content}; /v1/chat/completions streams OpenAI deltas.
        const delta =
          frame.content ?? frame.choices?.[0]?.delta?.content ?? frame.delta ?? ''
        if (delta) {
          spoken += delta
          sendTurn({ type: 'text', delta })
        }
      }

      remember('user', text)
      remember('assistant', spoken)
      sendTurn({ type: 'done', text: spoken, costUsd: null })
    } catch (err) {
      if (err?.name === 'AbortError') {
        // A barge-in, not a fault: the next question is already on its way and
        // announcing a failure would make JARVIS apologise for being interrupted.
        sendTurn({ type: 'done', text: spoken, costUsd: null })
      } else {
        const message = String(err?.message ?? err)
        console.error('[jarvis] turn failed:', message)
        sendTurn({
          type: 'error',
          message: message.includes('fetch failed')
            ? 'The JARVIS brain is not running. Start it with: jarvis serve'
            : message,
        })
      }
    } finally {
      clearTimeout(timer)
      abort = null
    }
  }

  socket.on('message', (raw) => {
    let msg
    try {
      msg = JSON.parse(raw.toString())
    } catch {
      return
    }

    if (msg.type === 'ask' && typeof msg.text === 'string') {
      const id = typeof msg.id === 'string' ? msg.id : null
      // Serialised, so two questions in quick succession cannot interleave
      // their tokens on the same socket.
      turn = turn.then(() => ask(msg.text, id)).catch(() => {})
    }

    if (msg.type === 'interrupt') {
      abort?.abort()
    }
  })

  socket.on('close', () => {
    abort?.abort()
  })
}
