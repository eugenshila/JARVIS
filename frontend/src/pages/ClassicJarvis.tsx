/*
 * ClassicJarvis.tsx — the interface for the 2020 assistant ported into this repo.
 *
 * The upstream project (KKshitiz/J.A.R.V.I.S) shipped no GUI: its `gui/` folder
 * held a README listing "tentative platforms" for one. This is that interface,
 * built the way the rest of this repo builds them — a React page against the
 * local API, styled to match the existing Iron Man HUD.
 *
 * Voice is browser-side on purpose: Web Speech API for dictation and playback,
 * so no audio ever leaves the machine and the page still works with the mic
 * blocked (type instead).
 */
import { useEffect, useRef, useState } from 'react'

const CYAN = '#22d3ee'
const CYAN_DIM = 'rgba(34,211,238,0.35)'
const AMBER = '#f59e0b'

type Command = { intent: string; example: string; description: string }
type Reply = {
  intent: string
  speech: string
  data: Record<string, any>
  expects: string | null
  confirm_token: string | null
}
type Line = { who: 'you' | 'jarvis'; text: string; intent?: string; token?: string | null }

export default function ClassicJarvis() {
  const [commands, setCommands] = useState<Command[]>([])
  const [log, setLog] = useState<Line[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [listening, setListening] = useState(false)
  const [speak, setSpeak] = useState(true)
  const [online, setOnline] = useState<boolean | null>(null)
  const [pendingToken, setPendingToken] = useState<string | null>(null)
  const bottom = useRef<HTMLDivElement>(null)
  const recognition = useRef<any>(null)

  useEffect(() => {
    fetch('/hud/classic/commands')
      .then(r => r.json())
      .then(d => { setCommands(d.commands || []); setOnline(true) })
      .catch(() => setOnline(false))
  }, [])

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [log])

  function say(text: string) {
    if (!speak || !('speechSynthesis' in window)) return
    const utterance = new SpeechSynthesisUtterance(text)
    const voices = window.speechSynthesis.getVoices()
    // Prefer a UK English voice — closest to the character, and present on
    // most Windows installs. Falls back to whatever the browser has.
    const preferred = voices.find(v => /en-GB/i.test(v.lang)) || voices.find(v => /^en/i.test(v.lang))
    if (preferred) utterance.voice = preferred
    utterance.rate = 1.02
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utterance)
  }

  async function send(text: string) {
    const command = text.trim()
    if (!command || busy) return
    setInput('')
    setLog(l => [...l, { who: 'you', text: command }])
    setBusy(true)
    try {
      const response = await fetch('/hud/classic/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command }),
      })
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || `HTTP ${response.status}`)
      const reply: Reply = await response.json()
      setLog(l => [...l, { who: 'jarvis', text: reply.speech, intent: reply.intent, token: reply.confirm_token }])
      setPendingToken(reply.confirm_token)
      setOnline(true)
      say(reply.speech)
    } catch (error: any) {
      setOnline(false)
      setLog(l => [...l, { who: 'jarvis', text: `Local API unreachable — ${error.message}. Start it with: jarvis serve`, intent: 'error' }])
    } finally {
      setBusy(false)
    }
  }

  async function resolveConfirm(approve: boolean) {
    if (!pendingToken) return
    const path = `/confirm/${pendingToken}/${approve ? 'approve' : 'cancel'}`
    try {
      const response = await fetch(path, { method: 'POST' })
      const body = await response.json().catch(() => ({}))
      setLog(l => [...l, { who: 'jarvis', text: body.result || body.detail || (approve ? 'Confirmed.' : 'Cancelled, sir.'), intent: 'confirm' }])
    } catch (error: any) {
      setLog(l => [...l, { who: 'jarvis', text: `Could not reach the confirmation gate: ${error.message}`, intent: 'error' }])
    } finally {
      setPendingToken(null)
    }
  }

  function toggleMic() {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      setLog(l => [...l, { who: 'jarvis', text: 'This browser has no speech recognition, sir. Typing works.', intent: 'error' }])
      return
    }
    if (listening) { recognition.current?.stop(); setListening(false); return }
    const engine = new SpeechRecognition()
    engine.lang = 'en-GB'
    engine.interimResults = false
    engine.maxAlternatives = 1
    engine.onresult = (event: any) => send(event.results[0][0].transcript)
    engine.onend = () => setListening(false)
    engine.onerror = () => setListening(false)
    recognition.current = engine
    engine.start()
    setListening(true)
  }

  const chip: React.CSSProperties = {
    background: 'rgba(34,211,238,0.06)', border: `1px solid ${CYAN_DIM}`, color: CYAN,
    borderRadius: 16, padding: '5px 11px', fontSize: 11, cursor: 'pointer',
    fontFamily: 'monospace', letterSpacing: 0.5,
  }

  return (
    <div style={{ minHeight: '100vh', background: 'radial-gradient(circle at 50% 0%, #061420 0%, #020208 60%)', color: '#cbd5e1', fontFamily: 'ui-monospace, monospace', display: 'flex', flexDirection: 'column' }}>
      <header style={{ padding: '18px 22px 12px', borderBottom: `1px solid ${CYAN_DIM}` }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 18, letterSpacing: 7, color: CYAN }}>J.A.R.V.I.S</span>
          <span style={{ fontSize: 10, letterSpacing: 2, color: '#64748b' }}>CLASSIC COMMAND CONSOLE</span>
          <span style={{ marginLeft: 'auto', fontSize: 10, letterSpacing: 1, color: online === false ? '#ef4444' : online ? '#22c55e' : '#64748b' }}>
            {online === false ? '◍ LOCAL API OFFLINE' : online ? '◉ LOCAL API ONLINE' : '◌ CONNECTING'}
          </span>
        </div>
        <div style={{ fontSize: 10, color: '#475569', marginTop: 6 }}>
          Ported from KKshitiz/J.A.R.V.I.S (MIT) — runs on your machine, no cloud account required.
        </div>
      </header>

      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <aside style={{ width: 268, borderRight: `1px solid ${CYAN_DIM}`, padding: 16, overflowY: 'auto' }}>
          <div style={{ fontSize: 10, letterSpacing: 2, color: CYAN, marginBottom: 10 }}>COMMAND SET</div>
          {commands.map(c => (
            <div key={c.intent} onClick={() => send(c.example)} title={c.description}
                 style={{ padding: '7px 9px', marginBottom: 5, borderRadius: 7, cursor: 'pointer', border: '1px solid transparent', background: 'rgba(34,211,238,0.04)' }}
                 onMouseEnter={e => (e.currentTarget.style.border = `1px solid ${CYAN_DIM}`)}
                 onMouseLeave={e => (e.currentTarget.style.border = '1px solid transparent')}>
              <div style={{ fontSize: 11.5, color: '#e2e8f0' }}>{c.example}</div>
              <div style={{ fontSize: 10, color: '#64748b' }}>{c.description}</div>
            </div>
          ))}
          {commands.length === 0 && (
            <div style={{ fontSize: 11, color: '#64748b' }}>
              No command list yet. Start the API:<br /><code style={{ color: CYAN }}>jarvis serve</code>
            </div>
          )}
        </aside>

        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: 22, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {log.length === 0 && (
              <div style={{ margin: 'auto', textAlign: 'center', maxWidth: 440 }}>
                <div style={{ width: 96, height: 96, margin: '0 auto 18px', borderRadius: '50%', border: `2px solid ${CYAN}`, boxShadow: `0 0 34px ${CYAN_DIM} inset, 0 0 24px ${CYAN_DIM}`, display: 'grid', placeItems: 'center', fontSize: 11, letterSpacing: 2, color: CYAN }}>
                  STANDBY
                </div>
                <div style={{ fontSize: 13, color: '#94a3b8' }}>At your service, sir.</div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 8 }}>
                  Ask for the weather, a joke, your CPU load, a screenshot, or say "help".
                </div>
                <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap', marginTop: 16 }}>
                  {['help', 'tell me a joke', 'weather in London', 'battery status'].map(s => (
                    <button key={s} style={chip} onClick={() => send(s)}>{s}</button>
                  ))}
                </div>
              </div>
            )}
            {log.map((line, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: line.who === 'you' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '76%', whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.55, padding: '10px 14px',
                  borderRadius: line.who === 'you' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                  background: line.who === 'you' ? 'rgba(34,211,238,0.14)' : 'rgba(148,163,184,0.07)',
                  border: `1px solid ${line.who === 'you' ? CYAN_DIM : 'rgba(148,163,184,0.18)'}`,
                  color: line.who === 'you' ? '#e0f2fe' : '#cbd5e1',
                }}>
                  {line.who === 'jarvis' && line.intent && (
                    <div style={{ fontSize: 9, letterSpacing: 2, color: line.intent === 'error' ? '#ef4444' : CYAN, marginBottom: 4 }}>
                      {line.intent.toUpperCase()}
                    </div>
                  )}
                  {line.text}
                </div>
              </div>
            ))}
            {busy && <div style={{ fontSize: 11, color: '#64748b', letterSpacing: 2 }}>PROCESSING…</div>}
            <div ref={bottom} />
          </div>

          {pendingToken && (
            <div style={{ margin: '0 22px 10px', padding: 12, border: `1px solid ${AMBER}`, borderRadius: 10, background: 'rgba(245,158,11,0.08)', display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 11, color: AMBER, letterSpacing: 1 }}>
                THIS ONE IS IRREVERSIBLE — A HUMAN MUST APPROVE IT
              </span>
              <button style={{ ...chip, borderColor: AMBER, color: AMBER }} onClick={() => resolveConfirm(true)}>CONFIRM</button>
              <button style={chip} onClick={() => resolveConfirm(false)}>CANCEL</button>
            </div>
          )}

          <div style={{ padding: 16, borderTop: `1px solid ${CYAN_DIM}`, display: 'flex', gap: 10, alignItems: 'center' }}>
            <button onClick={toggleMic} title="Dictate with the browser's speech recognition"
                    style={{ ...chip, borderColor: listening ? '#ef4444' : CYAN_DIM, color: listening ? '#ef4444' : CYAN, padding: '9px 13px' }}>
              {listening ? '● LISTENING' : '🎙 SPEAK'}
            </button>
            <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send(input)}
                   placeholder='Say "jarvis, weather in Oslo"…'
                   style={{ flex: 1, background: 'rgba(2,2,8,0.8)', border: `1px solid ${CYAN_DIM}`, color: '#e2e8f0', borderRadius: 22, padding: '11px 17px', fontSize: 13, outline: 'none', fontFamily: 'inherit' }} />
            <label style={{ fontSize: 10, color: '#64748b', display: 'flex', alignItems: 'center', gap: 5, cursor: 'pointer' }}>
              <input type="checkbox" checked={speak} onChange={e => setSpeak(e.target.checked)} /> VOICE
            </label>
            <button onClick={() => send(input)} disabled={busy}
                    style={{ ...chip, background: CYAN, color: '#021018', borderColor: CYAN, fontWeight: 700, padding: '10px 18px' }}>
              SEND
            </button>
          </div>
        </main>
      </div>
    </div>
  )
}
