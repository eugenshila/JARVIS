import { useCallback, useEffect, useRef, useState } from 'react'

/*
  ConfirmGate — the interface half of jarvis/core/confirm.py.

  WHY THIS EXISTS
    The backend gate is only half a gate. A tool calls confirm.request(...),
    the work sits in a queue, and the model is told "a confirmation is
    waiting" — but until something on screen offers CONFIRM / CANCEL, the
    only way to release that work is curl. Irreversible actions therefore
    either never ran, or people went back to confirm=true tool parameters.

  WHAT IT DOES
    Polls GET /confirm, renders every pending item with its live countdown,
    and calls POST /confirm/{token}/approve | /cancel when a human presses a
    button. Nothing else in the UI can release the work: the token is issued
    by the server, never by the model.

  STATIC HOSTING
    The dashboard is also published to GitHub Pages with no backend. Polling
    fails there, so after a few misses the gate backs off to a slow heartbeat
    and renders nothing at all — no error banner on a demo page.
*/

const AMBER = '#f59e0b'
const AMBER_DIM = 'rgba(245,158,11,0.45)'
const CYAN = '#22d3ee'
const RED = '#f87171'
const GREEN = '#34d399'

const POLL_MS = 2000
const POLL_MS_OFFLINE = 30000
const MISSES_BEFORE_BACKOFF = 3

export type PendingConfirmation = {
  token: string
  title: string
  detail: string
  expires_in: number
}

/** Bearer token for a server started with JARVIS_API_REQUIRE_TOKEN=1. */
function authHeaders(): Record<string, string> {
  let token = ''
  try {
    token =
      new URLSearchParams(window.location.search).get('token') ||
      window.localStorage.getItem('jarvis_api_token') ||
      ''
  } catch {
    token = ''
  }
  return token ? { 'X-Jarvis-Token': token } : {}
}

export default function ConfirmGate() {
  const [pending, setPending] = useState<PendingConfirmation[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [flash, setFlash] = useState<{ tone: 'ok' | 'bad'; text: string } | null>(null)
  const misses = useRef(0)
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const say = useCallback((tone: 'ok' | 'bad', text: string) => {
    setFlash({ tone, text })
    if (flashTimer.current) clearTimeout(flashTimer.current)
    flashTimer.current = setTimeout(() => setFlash(null), 6000)
  }, [])

  const poll = useCallback(async () => {
    try {
      const res = await fetch('/confirm', { headers: authHeaders() })
      if (!res.ok) throw new Error(String(res.status))
      const data = await res.json()
      misses.current = 0
      setPending(Array.isArray(data?.pending) ? data.pending : [])
    } catch {
      misses.current += 1
      // No backend (static Pages, server restarting): show nothing.
      if (misses.current >= MISSES_BEFORE_BACKOFF) setPending([])
    }
  }, [])

  // Poll, slowly when there is nothing listening, and never while hidden.
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>
    let stopped = false
    const loop = async () => {
      if (!document.hidden) await poll()
      if (stopped) return
      const wait = misses.current >= MISSES_BEFORE_BACKOFF ? POLL_MS_OFFLINE : POLL_MS
      timer = setTimeout(loop, wait)
    }
    loop()
    return () => {
      stopped = true
      clearTimeout(timer)
      if (flashTimer.current) clearTimeout(flashTimer.current)
    }
  }, [poll])

  // Local countdown between polls so the timer does not visibly jump.
  useEffect(() => {
    if (pending.length === 0) return
    const tick = setInterval(() => {
      setPending(items =>
        items
          .map(p => ({ ...p, expires_in: Math.max(0, p.expires_in - 1) }))
          .filter(p => p.expires_in > 0),
      )
    }, 1000)
    return () => clearInterval(tick)
  }, [pending.length])

  const act = useCallback(
    async (item: PendingConfirmation, action: 'approve' | 'cancel') => {
      if (busy) return
      setBusy(item.token)
      // Optimistic: a token is single-use, so it is gone either way.
      setPending(items => items.filter(p => p.token !== item.token))
      try {
        const res = await fetch(`/confirm/${encodeURIComponent(item.token)}/${action}`, {
          method: 'POST',
          headers: authHeaders(),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) {
          say('bad', data?.detail || `${item.title} — ${action} failed (${res.status}).`)
        } else if (action === 'approve') {
          say('ok', String(data?.result || `${item.title} — done.`))
        } else {
          say('ok', `${item.title} — cancelled.`)
        }
      } catch {
        say('bad', `${item.title} — could not reach JARVIS.`)
      } finally {
        setBusy(null)
        poll()
      }
    },
    [busy, poll, say],
  )

  // Esc cancels the oldest pending item. There is deliberately no keyboard
  // shortcut for approve: confirming is a decision, not a reflex.
  useEffect(() => {
    if (pending.length === 0) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') act(pending[0], 'cancel')
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [pending, act])

  if (pending.length === 0 && !flash) return null

  return (
    <div
      data-testid="confirm-gate"
      style={{
        position: 'fixed', top: 12, left: '50%', transform: 'translateX(-50%)',
        zIndex: 9999, width: 'min(560px, calc(100vw - 24px))',
        display: 'flex', flexDirection: 'column', gap: 8,
        fontFamily: "'JetBrains Mono','Share Tech Mono',monospace",
      }}
    >
      {pending.map(item => {
        const pct = Math.max(0, Math.min(100, (item.expires_in / 90) * 100))
        const working = busy === item.token
        return (
          <div
            key={item.token}
            role="alertdialog"
            aria-live="assertive"
            aria-label={`Confirmation required: ${item.title}`}
            style={{
              background: 'rgba(8,6,2,0.94)', border: `1px solid ${AMBER}`, borderRadius: 10,
              boxShadow: '0 0 22px rgba(245,158,11,0.35)', padding: '12px 14px',
              backdropFilter: 'blur(3px)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{ fontSize: 10, letterSpacing: 2, color: AMBER }}>⚠ CONFIRMATION REQUIRED</span>
              <span style={{ flex: 1 }} />
              <span style={{ fontSize: 11, color: AMBER_DIM }}>{Math.ceil(item.expires_in)}s</span>
            </div>
            <div style={{ fontSize: 14, color: '#fde68a', marginBottom: 2, wordBreak: 'break-word' }}>{item.title}</div>
            <div style={{ fontSize: 12, color: 'rgba(253,230,138,0.7)', marginBottom: 10, wordBreak: 'break-word', whiteSpace: 'pre-wrap' }}>
              {item.detail}
            </div>
            <div style={{ height: 3, background: 'rgba(245,158,11,0.18)', borderRadius: 2, marginBottom: 10 }}>
              <div style={{ height: '100%', width: `${pct}%`, background: AMBER, borderRadius: 2, transition: 'width 1s linear' }} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => act(item, 'approve')}
                disabled={working}
                style={{
                  flex: 1, background: 'rgba(245,158,11,0.16)', border: `1px solid ${AMBER}`, color: '#fde68a',
                  borderRadius: 6, padding: '9px 12px', fontSize: 12, letterSpacing: 2,
                  cursor: working ? 'wait' : 'pointer', fontFamily: 'inherit', opacity: working ? 0.6 : 1,
                }}
              >
                {working ? 'WORKING…' : 'CONFIRM'}
              </button>
              <button
                onClick={() => act(item, 'cancel')}
                disabled={working}
                style={{
                  flex: 1, background: 'rgba(2,8,12,0.8)', border: `1px solid ${CYAN}`, color: CYAN,
                  borderRadius: 6, padding: '9px 12px', fontSize: 12, letterSpacing: 2,
                  cursor: working ? 'wait' : 'pointer', fontFamily: 'inherit', opacity: working ? 0.6 : 1,
                }}
              >
                CANCEL <span style={{ opacity: 0.6 }}>(ESC)</span>
              </button>
            </div>
          </div>
        )
      })}

      {flash && (
        <div
          role="status"
          style={{
            background: 'rgba(2,8,12,0.94)', border: `1px solid ${flash.tone === 'ok' ? GREEN : RED}`,
            color: flash.tone === 'ok' ? GREEN : RED, borderRadius: 10, padding: '9px 12px',
            fontSize: 12, wordBreak: 'break-word', whiteSpace: 'pre-wrap',
          }}
        >
          {flash.text}
        </div>
      )}
    </div>
  )
}
