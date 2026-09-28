import { useState, useEffect, useRef } from 'react'

/*
  JARVIS holographic desktop dashboard — single unified view.
  (build marker: redeploy dashboard to GitHub Pages)
  Central arc reactor (large), clock + gauge dials, storage / energy readouts,
  an ADHD co-pilot panel that runs "inside" the HUD, a live task list, a stock
  market watchlist, a multi-day weather panel, and an audio spectrum with media
  controls. Pure SVG + canvas, no backend required, so it renders identically on
  a static GitHub Pages link.
*/

const CYAN = '#22d3ee'
const CYAN_SOFT = 'rgba(34,211,238,0.55)'
const CYAN_DIM = 'rgba(34,211,238,0.25)'
const UP = '#34d399'
const DOWN = '#f87171'

// --- geometry helpers -------------------------------------------------------
function polar(cx: number, cy: number, r: number, deg: number) {
  const a = ((deg - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) }
}
function arcPath(cx: number, cy: number, r: number, start: number, end: number) {
  const s = polar(cx, cy, r, end)
  const e = polar(cx, cy, r, start)
  const large = end - start <= 180 ? 0 : 1
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 0 ${e.x} ${e.y}`
}
const HALO = (r: number) => ({ filter: `drop-shadow(0 0 ${r}px rgba(34,211,238,0.6))` })

// --- tick ring --------------------------------------------------------------
function TickRing({ cx, cy, r, count = 60, len = 6, color = CYAN_SOFT }:
  { cx: number; cy: number; r: number; count?: number; len?: number; color?: string }) {
  const ticks = []
  for (let i = 0; i < count; i++) {
    const deg = (i / count) * 360
    const big = i % 5 === 0
    const p1 = polar(cx, cy, r, deg)
    const p2 = polar(cx, cy, r - (big ? len + 3 : len), deg)
    ticks.push(<line key={i} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
      stroke={color} strokeWidth={big ? 1.4 : 0.7} opacity={big ? 0.9 : 0.5} />)
  }
  return <g>{ticks}</g>
}

// --- circular gauge ---------------------------------------------------------
function Gauge({ size, value, label, sub, color = CYAN }:
  { size: number; value: number; label: string; sub?: string; color?: string }) {
  const cx = size / 2, cy = size / 2
  const r = size / 2 - 8
  const sweep = Math.max(0, Math.min(100, value)) / 100 * 300
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ display: 'block' }}>
        <g className="spin-slow" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>
          <TickRing cx={cx} cy={cy} r={r} count={40} len={4} />
        </g>
        <circle cx={cx} cy={cy} r={r - 10} fill="none" stroke={CYAN_DIM} strokeWidth={4} />
        <path d={arcPath(cx, cy, r - 10, 210, 210 - sweep)} fill="none" stroke={color}
          strokeWidth={4} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 4px ${color})` }} />
        <circle cx={cx} cy={cy} r={r - 22} fill="none" stroke={CYAN_DIM} strokeWidth={1} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
        <div style={{ fontSize: size * 0.24, fontWeight: 700, color, textShadow: `0 0 8px ${color}` }}>
          {Math.round(value)}
        </div>
        <div style={{ fontSize: size * 0.1, letterSpacing: 1, color: CYAN_SOFT }}>{label}</div>
        {sub && <div style={{ fontSize: size * 0.08, color: CYAN_DIM }}>{sub}</div>}
      </div>
    </div>
  )
}

// --- weather glyphs ---------------------------------------------------------
function WxIcon({ kind, s = 22 }: { kind: string; s?: number }) {
  const st = { stroke: CYAN, strokeWidth: 1.4, fill: 'none' as const, strokeLinecap: 'round' as const }
  if (kind === 'sun') return (
    <svg width={s} height={s} viewBox="0 0 24 24"><circle cx="12" cy="12" r="4.5" {...st} />
      {[0, 45, 90, 135, 180, 225, 270, 315].map(a => { const p = polar(12, 12, 8, a), q = polar(12, 12, 10.5, a); return <line key={a} x1={p.x} y1={p.y} x2={q.x} y2={q.y} {...st} /> })}</svg>)
  if (kind === 'moon') return (
    <svg width={s} height={s} viewBox="0 0 24 24"><path d="M16 12a5.5 5.5 0 1 1-5.8-5.5A4.5 4.5 0 0 0 16 12z" {...st} /></svg>)
  if (kind === 'rain') return (
    <svg width={s} height={s} viewBox="0 0 24 24"><path d="M7 14a4 4 0 0 1 .5-8 5 5 0 0 1 9.5 2 3.2 3.2 0 0 1-.5 6H7z" {...st} />
      <line x1="8" y1="18" x2="7" y2="21" {...st} /><line x1="12" y1="18" x2="11" y2="21" {...st} /><line x1="16" y1="18" x2="15" y2="21" {...st} /></svg>)
  return (
    <svg width={s} height={s} viewBox="0 0 24 24"><path d="M7 17a4 4 0 0 1 .5-8 5 5 0 0 1 9.5 2 3.2 3.2 0 0 1-.5 6H7z" {...st} /></svg>)
}

type Forecast = { day: string; icon: string; hi: number; lo: number; desc: string }
const FORECAST: Forecast[] = [
  { day: 'TONIGHT', icon: 'moon', hi: 13, lo: 9, desc: 'Clear' },
  { day: 'FRI', icon: 'sun', hi: 23, lo: 11, desc: 'Sunny' },
  { day: 'SAT', icon: 'cloud', hi: 19, lo: 12, desc: 'Cloudy' },
  { day: 'SUN', icon: 'rain', hi: 17, lo: 10, desc: 'Showers' },
  { day: 'MON', icon: 'sun', hi: 21, lo: 12, desc: 'Sunny' },
]

// --- sparkline --------------------------------------------------------------
function Sparkline({ data, color, w = 64, h = 22 }: { data: number[]; color: string; w?: number; h?: number }) {
  const min = Math.min(...data), max = Math.max(...data)
  const rng = max - min || 1
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / rng) * (h - 3) - 1.5}`).join(' ')
  return (
    <svg width={w} height={h} style={{ display: 'block' }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.4}
        strokeLinejoin="round" strokeLinecap="round" style={{ filter: `drop-shadow(0 0 2px ${color})` }} />
    </svg>
  )
}

// --- central arc reactor ----------------------------------------------------
function ArcReactor({ size }: { size: number }) {
  const c = size / 2
  const coils = []
  const n = 12
  for (let i = 0; i < n; i++) {
    const deg = (i / n) * 360
    const a = polar(c, c, size * 0.2, deg)
    const b = polar(c, c, size * 0.28, deg - 8)
    const d = polar(c, c, size * 0.28, deg + 8)
    coils.push(<path key={i} d={`M ${a.x} ${a.y} L ${b.x} ${b.y} L ${d.x} ${d.y} Z`}
      fill="rgba(34,211,238,0.18)" stroke={CYAN} strokeWidth={0.8} />)
  }
  return (
    <svg width={size} height={size} style={{ ...HALO(24) }}>
      <defs>
        <radialGradient id="core" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#eafcff" />
          <stop offset="35%" stopColor="#8be9ff" />
          <stop offset="70%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="rgba(34,211,238,0)" />
        </radialGradient>
      </defs>
      <g className="spin-slow" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>
        <TickRing cx={c} cy={c} r={size * 0.47} count={72} len={12} />
      </g>
      <circle cx={c} cy={c} r={size * 0.45} fill="none" stroke={CYAN_DIM} strokeWidth={1} />
      <g className="spin-rev" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>
        {[0, 90, 180, 270].map(a => (
          <path key={a} d={arcPath(c, c, size * 0.4, a + 8, a + 82)} fill="none"
            stroke={CYAN} strokeWidth={3} strokeLinecap="round" style={HALO(6)} />
        ))}
      </g>
      <g className="spin-slow2" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>
        <circle cx={c} cy={c} r={size * 0.34} fill="none" stroke={CYAN_SOFT}
          strokeWidth={1.5} strokeDasharray="2 8" />
      </g>
      <g className="spin-fast" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>{coils}</g>
      <circle cx={c} cy={c} r={size * 0.19} fill="none" stroke={CYAN} strokeWidth={2} style={HALO(8)} />
      <circle cx={c} cy={c} r={size * 0.16} fill="url(#core)" className="pulse-core" />
      <circle cx={c} cy={c} r={size * 0.055} fill="#f2feff" style={HALO(16)} />
    </svg>
  )
}

// --- audio spectrum ---------------------------------------------------------
function Spectrum() {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const cv = ref.current; if (!cv) return
    const ctx = cv.getContext('2d'); if (!ctx) return
    let raf = 0; let t = 0
    const bars = 96
    const draw = () => {
      const w = cv.width, h = cv.height
      ctx.clearRect(0, 0, w, h)
      const bw = w / bars
      t += 0.08
      for (let i = 0; i < bars; i++) {
        const dist = Math.abs(i - bars / 2) / (bars / 2)
        const base = (1 - dist) * 0.9 + 0.1
        const v = (Math.sin(i * 0.5 + t) * 0.5 + 0.5) * (Math.sin(i * 0.13 + t * 0.7) * 0.5 + 0.5)
        const bh = Math.max(2, v * base * h * 0.92)
        const x = i * bw
        const grad = ctx.createLinearGradient(0, h / 2 - bh / 2, 0, h / 2 + bh / 2)
        grad.addColorStop(0, 'rgba(34,211,238,0.15)')
        grad.addColorStop(0.5, 'rgba(120,240,255,0.95)')
        grad.addColorStop(1, 'rgba(34,211,238,0.15)')
        ctx.fillStyle = grad
        ctx.fillRect(x + bw * 0.2, h / 2 - bh / 2, bw * 0.6, bh)
      }
      raf = requestAnimationFrame(draw)
    }
    draw()
    return () => cancelAnimationFrame(raf)
  }, [])
  return <canvas ref={ref} width={720} height={72} style={{ width: '100%', height: 72, display: 'block' }} />
}

// --- panel chrome -----------------------------------------------------------
function Panel({ title, right, children, style }:
  { title?: string; right?: React.ReactNode; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      border: `1px solid ${CYAN_DIM}`, borderRadius: 10, padding: 12,
      background: 'rgba(6,16,22,0.55)', backdropFilter: 'blur(4px)',
      boxShadow: 'inset 0 0 24px rgba(34,211,238,0.06)', ...style,
    }}>
      {title && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <div style={{ fontSize: 10, letterSpacing: 2, color: CYAN_SOFT }}>{title}</div>
          {right}
        </div>
      )}
      {children}
    </div>
  )
}

// --- stock watchlist --------------------------------------------------------
type Stock = { sym: string; price: number; base: number; hist: number[] }
const START_STOCKS: Stock[] = [
  { sym: 'STARK', price: 412.55, base: 400, hist: [] },
  { sym: 'AAPL', price: 229.30, base: 225, hist: [] },
  { sym: 'NVDA', price: 178.42, base: 170, hist: [] },
  { sym: 'TSLA', price: 251.10, base: 260, hist: [] },
  { sym: 'BTC', price: 63120, base: 61000, hist: [] },
].map(s => ({ ...s, hist: Array.from({ length: 20 }, () => s.price * (1 + (Math.random() - 0.5) * 0.02)) }))

// --- sample data for testing ------------------------------------------------
const CALENDAR = ['10:00 · Q4 planning prep', '14:00 · Q4 planning meeting', '16:30 · Client call']
const INBOX = [
  { from: 'Client', subj: 'Need Q4 brief by Friday', unread: true },
  { from: 'Team', subj: 'Project update — on track', unread: true },
  { from: 'Newsletter', subj: 'Weekly digest', unread: false },
]

// --- Career OS + Income OS sample fallback (used until the local API answers) ---
const SAMPLE_CAREER = { mode: 'seeking', stats: { jobs: 12, applications: 7, follow_ups_due: 2 } }
const SAMPLE_INCOME = {
  disclaimer: 'Informational only — not financial advice. No automated trading.',
  opportunities: { count: 4, awaiting_review: 2 },
  watchlist: { count: 3 },
  portfolio: { count: 2 },
  projects: { count: 2, active: 1 },
}

export default function JarvisDashboard() {
  const [now, setNow] = useState(new Date())
  const [sys, setSys] = useState({ cpu: 74, ram: 15, swap: 49 })
  const [timer, setTimer] = useState(1500) // 25:00 focus session
  const [running, setRunning] = useState(true)
  const [stocks, setStocks] = useState<Stock[]>(START_STOCKS)
  const [reactor, setReactor] = useState(520)

  // voice sample state
  const [speaking, setSpeaking] = useState(false)
  const [voiceText, setVoiceText] = useState('Good morning, sir. All systems nominal.')
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // tasks
  const [tasks, setTasks] = useState<{ text: string; done: boolean }[]>(() => {
    try {
      const raw = localStorage.getItem('jarvis_dashboard_tasks')
      if (raw) return JSON.parse(raw)
    } catch {}
    return [
      { text: 'Q4 planning brief', done: false },
      { text: 'Reply to client email', done: false },
      { text: 'Lab diagnostics run', done: true },
    ]
  })
  const [newTask, setNewTask] = useState('')
  useEffect(() => { localStorage.setItem('jarvis_dashboard_tasks', JSON.stringify(tasks)) }, [tasks])

  // Career OS + Income OS — read-only glance, falls back to sample data on
  // GitHub Pages / when the local JARVIS API isn't running.
  const [career, setCareer] = useState<any>(SAMPLE_CAREER)
  const [income, setIncome] = useState<any>(SAMPLE_INCOME)
  useEffect(() => {
    fetch('/hud/career').then(r => r.ok ? r.json() : Promise.reject()).then(setCareer).catch(() => {})
    fetch('/hud/income').then(r => r.ok ? r.json() : Promise.reject()).then(setIncome).catch(() => {})
  }, [])

  // MITs for ADHD co-pilot (top 3 undone tasks)
  const mits = tasks.filter(t => !t.done).slice(0, 3)
  const wins = tasks.filter(t => t.done).length

  // reactor size responsive
  useEffect(() => {
    const fit = () => setReactor(Math.round(Math.min(820, window.innerWidth * 0.52, window.innerHeight * 0.88)))
    fit()
    window.addEventListener('resize', fit)
    return () => window.removeEventListener('resize', fit)
  }, [])

  useEffect(() => {
    const id = setInterval(() => {
      setNow(new Date())
      setSys(s => ({
        cpu: Math.max(8, Math.min(96, s.cpu + (Math.random() - 0.5) * 6)),
        ram: Math.max(5, Math.min(90, s.ram + (Math.random() - 0.5) * 4)),
        swap: Math.max(5, Math.min(90, s.swap + (Math.random() - 0.5) * 4)),
      }))
      setTimer(t => (running ? (t <= 0 ? 1500 : t - 1) : t))
    }, 1000)
    return () => clearInterval(id)
  }, [running])

  // stock ticker random walk
  useEffect(() => {
    const id = setInterval(() => {
      setStocks(prev => prev.map(s => {
        const np = Math.max(0.01, s.price * (1 + (Math.random() - 0.5) * 0.012))
        return { ...s, price: np, hist: [...s.hist.slice(-19), np] }
      }))
    }, 2500)
    return () => clearInterval(id)
  }, [])

  const hh = String(now.getHours()).padStart(2, '0')
  const mm = String(now.getMinutes()).padStart(2, '0')
  const ss = String(now.getSeconds()).padStart(2, '0')
  const weekday = now.toLocaleDateString([], { weekday: 'long' })
  const monthName = now.toLocaleDateString([], { month: 'long' })
  const dayNum = now.getDate()
  const tMin = Math.floor(timer / 60), tSec = String(timer % 60).padStart(2, '0')

  // --- ADHD day plan: energy-aware schedule + "do now" + smart tips ---
  const mitText = (i: number) => mits[i]?.text || ['Deep work block', 'Second priority', 'Third priority'][i]

  // Energy curve across the day (ADHD-friendly: peak AM, post-lunch dip, PM second wind)
  const energyFor = (h: number) => {
    if (h < 6) return { level: 'LOW', pct: 20, note: 'Rest — protect your sleep', color: DOWN }
    if (h < 9) return { level: 'RISING', pct: 55, note: 'Ease in — hydrate, quick wins', color: CYAN }
    if (h < 12) return { level: 'PEAK', pct: 96, note: 'Peak focus — do your hardest MIT now', color: UP }
    if (h < 13) return { level: 'GOOD', pct: 72, note: 'Still sharp — finish deep work', color: UP }
    if (h < 15) return { level: 'DIP', pct: 38, note: 'Post-lunch dip — admin, not deep work', color: '#fbbf24' }
    if (h < 18) return { level: 'SECOND WIND', pct: 70, note: 'Second wind — tackle MIT 2 & 3', color: UP }
    if (h < 21) return { level: 'WIND-DOWN', pct: 46, note: 'Wrap up and plan tomorrow', color: CYAN }
    return { level: 'LOW', pct: 24, note: 'Wind down — screens off soon', color: DOWN }
  }
  const energy = energyFor(now.getHours())

  const dayPlan = [
    { s: 7, t: '07:00', label: 'Morning routine · hydrate + move', tip: 'Sunlight + water wakes the brain', ph: 'RISING' },
    { s: 9, t: '09:00', label: `Peak deep work · ${mitText(0)}`, tip: 'Hardest MIT first, one tab only', ph: 'PEAK' },
    { s: 10.5, t: '10:30', label: 'Movement break · 5-min walk', tip: 'Dopamine reset before the next block', ph: 'PEAK' },
    { s: 10.75, t: '10:45', label: `Deep work · ${mitText(1)}`, tip: '25-min sprints, short rests', ph: 'PEAK' },
    { s: 12, t: '12:00', label: 'Lunch + reset', tip: 'No screens — a real break', ph: 'DIP' },
    { s: 13, t: '13:00', label: 'Admin · email & messages', tip: '2-minute rule during the dip', ph: 'DIP' },
    { s: 15, t: '15:00', label: `Second wind · ${mitText(2)}`, tip: 'Body-double on for momentum', ph: 'SECOND WIND' },
    { s: 16.5, t: '16:30', label: 'Log wins + plan tomorrow', tip: 'Celebrate small wins', ph: 'WIND-DOWN' },
  ]
  const nowFloat = now.getHours() + now.getMinutes() / 60
  let doNow = dayPlan[0]
  for (const b of dayPlan) if (nowFloat >= b.s) doNow = b

  // Smart tips chosen by current energy phase (rotates within the phase)
  const tipsByEnergy: Record<string, string[]> = {
    RISING: ['Start small to build momentum', 'Write today’s 3 MITs before anything else', 'Move + hydrate before MIT 1'],
    PEAK: ['Attack your hardest MIT — this is prime time', 'Silence notifications, single-task 25 min', 'Batch similar deep tasks while sharp'],
    GOOD: ['Keep going — one more 25-min sprint', 'Pick the next MIT, hide the rest', 'Use a body-double for accountability'],
    DIP: ['Low energy? Do admin/email, not deep work', 'Take a real break — walk, water, daylight', 'Shrink the task to a 10-minute step'],
    'SECOND WIND': ['Ride the second wind — tackle MIT 2 or 3', 'Set a 25-min timer and just start', 'Clear one quick win for momentum'],
    'WIND-DOWN': ['Log your wins — celebrate progress', 'Plan tomorrow’s 3 MITs now', 'Tidy one thing, then stop'],
    LOW: ['Rest is productive — protect your sleep', 'Brain-dump worries to clear your head', 'No new tasks — you’ve done enough today'],
  }
  const phaseTips = tipsByEnergy[energy.level] || tipsByEnergy.GOOD
  const tipOfNow = phaseTips[now.getMinutes() % phaseTips.length]



  const addTask = () => {
    const v = newTask.trim()
    if (!v) return
    setTasks(t => [...t, { text: v, done: false }])
    setNewTask('')
  }

  // --- JARVIS voice sample: play pre-rendered clip, fall back to browser TTS ---
  const base = import.meta.env.BASE_URL // '/JARVIS/' on pages, '/' in dev
  const clips = [
    { id: 'greeting', label: 'GREETING', file: `${base}voice/jarvis-greeting.mp3`, text: 'Good morning, sir. JARVIS online. All systems nominal.' },
    { id: 'status', label: 'STATUS', file: `${base}voice/jarvis-status.mp3`, text: 'Arc reactor holding at one hundred percent. Lab secure, perimeter clear.' },
    { id: 'focus', label: 'FOCUS', file: `${base}voice/jarvis-focus.mp3`, text: 'Beginning your first priority. Focus session engaged for twenty-five minutes.' },
  ]
  const speakBrowser = (text: string) => {
    try {
      if (!('speechSynthesis' in window)) { setSpeaking(false); return }
      window.speechSynthesis.cancel()
      const u = new SpeechSynthesisUtterance(text)
      u.rate = 1.0; u.pitch = 0.9
      const vs = window.speechSynthesis.getVoices()
      const gb = vs.find(v => /en-GB/i.test(v.lang) && /male|daniel|george|arthur|ryan/i.test(v.name))
        || vs.find(v => /en-GB/i.test(v.lang)) || vs.find(v => /^en/i.test(v.lang))
      if (gb) u.voice = gb
      setSpeaking(true)
      u.onend = () => setSpeaking(false)
      window.speechSynthesis.speak(u)
    } catch { setSpeaking(false) }
  }
  const playClip = (file: string, fallback: string) => {
    try { audioRef.current?.pause() } catch {}
    setSpeaking(true)
    const a = new Audio(file)
    audioRef.current = a
    let fell = false
    const fb = () => { if (fell) return; fell = true; speakBrowser(fallback) }
    a.onended = () => setSpeaking(false)
    a.onerror = fb
    a.play().catch(fb)
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background:
        'radial-gradient(1200px 700px at 50% 55%, rgba(10,40,55,0.55), rgba(2,6,10,0.98) 70%), #01050a',
      color: CYAN, fontFamily: '"Share Tech Mono","JetBrains Mono",monospace', overflow: 'hidden',
    }}>
      {/* grid + scanlines */}
      <div style={{ position: 'absolute', inset: 0, backgroundImage:
        'linear-gradient(rgba(34,211,238,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(34,211,238,0.04) 1px,transparent 1px)',
        backgroundSize: '46px 46px' }} />
      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', background:
        'repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,0.18) 3px,rgba(0,0,0,0.18) 4px)' }} />

      {/* ===== TOP-LEFT: clock / calendar dial ===== */}
      <div style={{ position: 'absolute', top: '3%', left: '2%', display: 'flex', gap: 14, alignItems: 'center' }}>
        <div style={{ position: 'relative', width: 150, height: 150 }}>
          <svg width={150} height={150} style={HALO(10)}>
            <g className="spin-slow" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>
              <TickRing cx={75} cy={75} r={71} count={60} len={6} />
            </g>
            <circle cx={75} cy={75} r={58} fill="none" stroke={CYAN_DIM} strokeWidth={1} />
            <path d={arcPath(75, 75, 58, 210, 210 - (now.getSeconds() / 60) * 300)} fill="none"
              stroke={CYAN} strokeWidth={3} strokeLinecap="round" style={HALO(5)} />
          </svg>
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ fontSize: 10, letterSpacing: 2, color: CYAN_SOFT }}>{weekday.toUpperCase()}</div>
            <div style={{ fontSize: 36, fontWeight: 700, lineHeight: 1, textShadow: `0 0 10px ${CYAN}` }}>{dayNum}</div>
            <div style={{ fontSize: 10, letterSpacing: 2, color: CYAN_SOFT }}>{monthName.toUpperCase()}</div>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: 3, textShadow: `0 0 10px ${CYAN}` }}>
            {hh}:{mm}<span style={{ fontSize: 14, color: CYAN_SOFT }}>:{ss}</span>
          </div>
          <div style={{ fontSize: 9, letterSpacing: 2, color: CYAN_SOFT, marginTop: 4 }}>LOCAL SYSTEM TIME</div>
          <div style={{ fontSize: 9, letterSpacing: 2, color: CYAN_DIM }}>J.A.R.V.I.S · MARK XLII</div>
        </div>
      </div>

      {/* ===== TOP-CENTER: cpu / ram / swap gauges ===== */}
      <div style={{ position: 'absolute', top: '3.5%', left: '50%', transform: 'translateX(-50%)',
        display: 'flex', gap: 16, alignItems: 'center' }}>
        <Gauge size={84} value={sys.cpu} label="CPU" />
        <Gauge size={72} value={sys.ram} label="RAM" color="#7dd3fc" />
        <Gauge size={72} value={sys.swap} label="SWAP" color="#67e8f9" />
      </div>

      {/* ===== TOP-RIGHT: header + city ===== */}
      <div style={{ position: 'absolute', top: '3%', right: '2%', textAlign: 'right' }}>
        <div style={{ fontSize: 11, letterSpacing: 1, color: CYAN_SOFT }}>{now.toLocaleDateString([], { year: 'numeric', month: '2-digit', day: '2-digit' })}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
          <WxIcon kind="moon" s={24} />
          <div>
            <div style={{ fontSize: 20, fontWeight: 700, textShadow: `0 0 8px ${CYAN}` }}>13°</div>
            <div style={{ fontSize: 9, letterSpacing: 1, color: CYAN_SOFT }}>NAIROBI · CLEAR</div>
          </div>
        </div>
      </div>

      {/* ===== CENTER: big arc reactor ===== */}
      <div style={{ position: 'absolute', top: '52%', left: '50%', transform: 'translate(-50%,-50%)' }}>
        <ArcReactor size={reactor} />
      </div>
      {[
        { t: '42%', l: '31%', txt: 'NEURAL LINK' }, { t: '38%', l: '69%', txt: 'REPULSOR' },
        { t: '66%', l: '32%', txt: 'DIAGNOSTIC' }, { t: '68%', l: '68%', txt: 'STARK IND.' },
      ].map((p, i) => (
        <div key={i} style={{ position: 'absolute', top: p.t, left: p.l, fontSize: 9, letterSpacing: 2,
          color: CYAN_DIM, transform: 'translate(-50%,-50%)', pointerEvents: 'none' }}>{p.txt}</div>
      ))}

      {/* ===== LEFT COLUMN: storage, energy, ADHD co-pilot ===== */}
      <div style={{ position: 'absolute', top: '22%', left: '2%', bottom: '3%', width: 300, display: 'flex', flexDirection: 'column', gap: 10, overflowY: 'auto', paddingRight: 4 }}>
        {/* ADHD co-pilot — day planning, runs inside the system */}
        <Panel title="ADHD CO-PILOT · PLAN MY DAY" right={<span style={{ fontSize: 8, color: UP, letterSpacing: 1 }}>● RUNNING</span>}>
          {/* focus timer + do-now */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div style={{ position: 'relative', width: 74, height: 74, flexShrink: 0 }}>
              <svg width={74} height={74} style={HALO(6)}>
                <circle cx={37} cy={37} r={30} fill="none" stroke={CYAN_DIM} strokeWidth={4} />
                <path d={arcPath(37, 37, 30, 0, (1 - timer / 1500) * 359.9)} fill="none" stroke={CYAN}
                  strokeWidth={4} strokeLinecap="round" style={HALO(4)} />
              </svg>
              <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ fontSize: 15, fontWeight: 700 }}>{tMin}:{tSec}</div>
                <div style={{ fontSize: 7, letterSpacing: 1, color: CYAN_SOFT }}>FOCUS</div>
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 9, color: CYAN_SOFT, letterSpacing: 1 }}>DO NOW · {doNow.t}</div>
              <div style={{ fontSize: 11, color: CYAN, lineHeight: 1.4, marginTop: 2 }}>{doNow.label}</div>
              <div style={{ fontSize: 9, color: UP, marginTop: 2 }}>▸ {doNow.tip}</div>
            </div>
          </div>

          {/* Live energy read-out */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, border: `1px solid ${CYAN_DIM}`, borderRadius: 6, padding: '5px 8px' }}>
            <span style={{ fontSize: 8, color: CYAN_SOFT, letterSpacing: 1 }}>ENERGY NOW</span>
            <span style={{ fontSize: 11, color: energy.color, textShadow: `0 0 6px ${energy.color}`, fontWeight: 700 }}>{energy.level}</span>
            <div style={{ flex: 1, height: 5, background: CYAN_DIM, borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ width: `${energy.pct}%`, height: '100%', background: energy.color, boxShadow: `0 0 6px ${energy.color}`, transition: 'width 0.6s' }} />
            </div>
          </div>
          <div style={{ fontSize: 9, color: CYAN_DIM, marginTop: 4 }}>▸ {energy.note}</div>
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <button onClick={() => setRunning(r => !r)} style={btn}>{running ? 'PAUSE' : 'START'} FOCUS</button>
            <button onClick={() => setTimer(1500)} style={btn}>RESET</button>
          </div>

          {/* Today's plan (time blocks) */}
          <div style={{ fontSize: 9, color: CYAN_SOFT, letterSpacing: 1, margin: '10px 0 4px' }}>HOW TO PLAN YOUR DAY</div>
          <div style={{ maxHeight: 148, overflowY: 'auto', paddingRight: 4 }}>
            {dayPlan.map((b, i) => {
              const active = b.t === doNow.t
              return (
                <div key={i} style={{ display: 'flex', gap: 8, padding: '4px 0',
                  borderBottom: i < dayPlan.length - 1 ? `1px solid ${CYAN_DIM}` : 'none' }}>
                  <div style={{ width: 40, fontSize: 10, color: active ? CYAN : CYAN_DIM, flexShrink: 0 }}>{b.t}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6 }}>
                      <div style={{ fontSize: 10, color: active ? CYAN : CYAN_SOFT, textShadow: active ? `0 0 6px ${CYAN}` : 'none' }}>
                        {active && '▸ '}{b.label}
                      </div>
                      <div style={{ fontSize: 7, color: CYAN_DIM, letterSpacing: 1, whiteSpace: 'nowrap', alignSelf: 'center' }}>{b.ph}</div>
                    </div>
                    <div style={{ fontSize: 8, color: CYAN_DIM }}>{b.tip}</div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Improve-your-day tip */}
          <div style={{ marginTop: 8, border: `1px solid ${CYAN_DIM}`, borderRadius: 6, padding: '6px 8px', background: 'rgba(34,211,238,0.06)' }}>
            <div style={{ fontSize: 8, color: CYAN_SOFT, letterSpacing: 1 }}>IMPROVE YOUR DAY</div>
            <div style={{ fontSize: 10, color: CYAN, marginTop: 2 }}>💡 {tipOfNow}</div>
          </div>

          <div style={{ fontSize: 9, color: CYAN_DIM, marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
            <span>MITs left: <span style={{ color: CYAN }}>{mits.length}</span></span>
            <span>Wins today: <span style={{ color: UP }}>{wins}</span></span>
          </div>
        </Panel>

        {/* storage + energy compact row */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <Gauge size={78} value={energy.pct} label="ENERGY" sub="%" color={energy.color} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 16, fontWeight: 800, letterSpacing: 3, color: CYAN_SOFT, textShadow: `0 0 8px ${CYAN}` }}>
              EXPO<span style={{ color: CYAN }}> 2010</span>
            </div>
            <div style={{ fontSize: 9, color: CYAN_DIM, lineHeight: 1.6, marginTop: 4 }}>
              <div>Storage 98 / 100 GB</div><div>Reactor online · 284 K</div><div>Output 3.2 GJ/s · stable</div>
            </div>
          </div>
        </div>

        {/* CAREER OS + INCOME OS — glance card, reads the local JARVIS API */}
        <Panel title="CAREER + INCOME OS" right={<span style={{ fontSize: 8, color: CYAN_SOFT, letterSpacing: 1 }}>{(career?.mode || 'seeking').toUpperCase()}</span>}>
          <div style={{ fontSize: 9, color: '#f59e0b', letterSpacing: 0.5, marginBottom: 6 }}>⚠ Research &amp; tracking only — not financial advice</div>
          <div style={{ fontSize: 10, color: CYAN_DIM, marginBottom: 4, letterSpacing: 1 }}>CAREER · JAUTOMATIC</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, padding: '2px 0' }}>
            <span>Applications tracked</span><span style={{ color: CYAN }}>{career?.stats?.applications ?? 0}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, padding: '2px 0' }}>
            <span>Follow-ups due</span>
            <span style={{ color: (career?.stats?.follow_ups_due || 0) ? '#f59e0b' : UP }}>{career?.stats?.follow_ups_due ?? 0}</span>
          </div>
          <div style={{ fontSize: 10, color: CYAN_DIM, margin: '8px 0 4px', letterSpacing: 1 }}>INCOME OS</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, padding: '2px 0' }}>
            <span>Opportunities awaiting review</span><span style={{ color: CYAN }}>{income?.opportunities?.awaiting_review ?? 0} / {income?.opportunities?.count ?? 0}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, padding: '2px 0' }}>
            <span>Watchlist</span><span style={{ color: CYAN }}>{income?.watchlist?.count ?? 0} symbols</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, padding: '2px 0' }}>
            <span>Portfolio (user-entered)</span><span style={{ color: CYAN }}>{income?.portfolio?.count ?? 0} holdings</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, padding: '2px 0' }}>
            <span>Active income projects</span><span style={{ color: CYAN }}>{income?.projects?.active ?? 0}</span>
          </div>
          <div style={{ fontSize: 8, color: CYAN_DIM, marginTop: 6 }}>Watchlist/portfolio are entries you make — nothing here trades or connects to a brokerage.</div>
        </Panel>
      </div>

      {/* ===== RIGHT COLUMN: weather, tasks, stocks ===== */}
      <div style={{ position: 'absolute', top: '15%', right: '2%', bottom: '3%', width: 256, display: 'flex', flexDirection: 'column', gap: 10, overflowY: 'auto', paddingRight: 4 }}>
        <Panel title="5-DAY FORECAST · NAIROBI">
          {FORECAST.map((f, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '5px 0',
              borderBottom: i < FORECAST.length - 1 ? `1px solid ${CYAN_DIM}` : 'none' }}>
              <div style={{ width: 44, fontSize: 10, letterSpacing: 1, color: CYAN_SOFT }}>{f.day}</div>
              <WxIcon kind={f.icon} s={20} />
              <div style={{ flex: 1, fontSize: 10, color: CYAN_DIM }}>{f.desc}</div>
              <div style={{ fontSize: 11, color: CYAN }}>{f.hi}°<span style={{ color: CYAN_DIM }}> / {f.lo}°</span></div>
            </div>
          ))}
        </Panel>

        {/* TASKS */}
        <Panel title="TASKS" right={<span style={{ fontSize: 9, color: CYAN_SOFT }}>{tasks.filter(t => !t.done).length} OPEN</span>}>
          <div style={{ maxHeight: 118, overflowY: 'auto' }}>
            {tasks.map((t, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
                <div onClick={() => setTasks(ts => ts.map((x, j) => j === i ? { ...x, done: !x.done } : x))}
                  style={{ width: 14, height: 14, borderRadius: 3, border: `1px solid ${t.done ? UP : CYAN_SOFT}`,
                    background: t.done ? UP : 'transparent', color: '#01050a', fontSize: 10, lineHeight: '12px',
                    textAlign: 'center', cursor: 'pointer', flexShrink: 0 }}>{t.done ? '✓' : ''}</div>
                <div style={{ flex: 1, fontSize: 11, color: t.done ? CYAN_DIM : CYAN,
                  textDecoration: t.done ? 'line-through' : 'none', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.text}</div>
                <span onClick={() => setTasks(ts => ts.filter((_, j) => j !== i))}
                  style={{ fontSize: 12, color: CYAN_DIM, cursor: 'pointer' }}>×</span>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <input value={newTask} onChange={e => setNewTask(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addTask()} placeholder="Add task + Enter"
              style={{ flex: 1, background: 'rgba(2,8,12,0.8)', border: `1px solid ${CYAN_DIM}`, color: CYAN,
                borderRadius: 6, padding: '6px 8px', fontSize: 10, fontFamily: 'inherit', outline: 'none' }} />
            <button onClick={addTask} style={btn}>ADD</button>
          </div>
        </Panel>

        {/* STOCK MARKET */}
        <Panel title="MARKET WATCH" right={<span style={{ fontSize: 8, color: UP, letterSpacing: 1 }}>● LIVE</span>}>
          {stocks.map((s, i) => {
            const chg = ((s.price - s.base) / s.base) * 100
            const up = chg >= 0
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0',
                borderBottom: i < stocks.length - 1 ? `1px solid ${CYAN_DIM}` : 'none' }}>
                <div style={{ width: 46, fontSize: 11, color: CYAN, letterSpacing: 1 }}>{s.sym}</div>
                <Sparkline data={s.hist} color={up ? UP : DOWN} w={58} h={20} />
                <div style={{ flex: 1, textAlign: 'right' }}>
                  <div style={{ fontSize: 11, color: CYAN }}>{s.price >= 1000 ? s.price.toLocaleString(undefined, { maximumFractionDigits: 0 }) : s.price.toFixed(2)}</div>
                  <div style={{ fontSize: 9, color: up ? UP : DOWN }}>{up ? '▲' : '▼'} {Math.abs(chg).toFixed(2)}%</div>
                </div>
              </div>
            )
          })}
        </Panel>

        {/* COMMS (moved from bottom-left to right column) */}
        <Panel title="COMMS · SAMPLE" right={<span style={{ fontSize: 9, color: DOWN }}>{INBOX.filter(m => m.unread).length} NEW</span>}>
          <div style={{ fontSize: 9, color: CYAN_SOFT, letterSpacing: 1, marginBottom: 4 }}>CALENDAR · TODAY</div>
          {CALENDAR.map((c, i) => (
            <div key={i} style={{ display: 'flex', gap: 6, fontSize: 10, color: CYAN, padding: '2px 0' }}>
              <span style={{ color: CYAN_DIM }}>▸</span>{c}
            </div>
          ))}
          <div style={{ fontSize: 9, color: CYAN_SOFT, letterSpacing: 1, margin: '8px 0 4px' }}>INBOX</div>
          {INBOX.map((m, i) => (
            <div key={i} style={{ display: 'flex', gap: 6, fontSize: 10, padding: '2px 0', color: m.unread ? CYAN : CYAN_DIM }}>
              <span style={{ color: m.unread ? DOWN : CYAN_DIM }}>{m.unread ? '●' : '○'}</span>
              <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.from}: {m.subj}</span>
            </div>
          ))}
        </Panel>
      </div>

      {/* ===== BOTTOM-CENTER: JARVIS voice sample + spectrum ===== */}
      <div style={{ position: 'absolute', bottom: '2.5%', left: '50%', transform: 'translateX(-50%)', width: '52%', maxWidth: 820 }}>
        <Panel title="JARVIS VOICE · SAMPLE" right={<span style={{ fontSize: 8, color: speaking ? UP : CYAN_SOFT, letterSpacing: 1 }}>{speaking ? '● SPEAKING' : 'neural en-GB · MSI'}</span>}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' }}>
            {clips.map(c => (
              <button key={c.id} onClick={() => playClip(c.file, c.text)} style={btn}>▶ {c.label}</button>
            ))}
            <input value={voiceText} onChange={e => setVoiceText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && speakBrowser(voiceText)}
              placeholder="Type for JARVIS to speak…"
              style={{ flex: 1, minWidth: 140, background: 'rgba(2,8,12,0.8)', border: `1px solid ${CYAN_DIM}`, color: CYAN,
                borderRadius: 6, padding: '7px 10px', fontSize: 11, fontFamily: 'inherit', outline: 'none' }} />
            <button onClick={() => speaking ? (window.speechSynthesis?.cancel(), audioRef.current?.pause(), setSpeaking(false)) : speakBrowser(voiceText)}
              style={{ ...btn, borderColor: speaking ? DOWN : CYAN_SOFT, color: speaking ? DOWN : CYAN }}>
              {speaking ? '■ STOP' : '▶ SPEAK'}
            </button>
          </div>
          <Spectrum />
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 6 }}>
            <div style={{ display: 'flex', gap: 14, color: CYAN }}>
              <span style={{ fontSize: 15, cursor: 'pointer' }}>⏮</span>
              <span onClick={() => playClip(clips[0].file, clips[0].text)} style={{ fontSize: 17, cursor: 'pointer', textShadow: `0 0 8px ${CYAN}` }}>{speaking ? '⏸' : '▶'}</span>
              <span style={{ fontSize: 15, cursor: 'pointer' }}>⏭</span>
            </div>
            <div style={{ flex: 1, height: 4, background: CYAN_DIM, borderRadius: 2, position: 'relative' }}>
              <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '42%', background: CYAN, borderRadius: 2, boxShadow: `0 0 8px ${CYAN}` }} />
              <div style={{ position: 'absolute', left: '42%', top: -3, width: 10, height: 10, borderRadius: '50%', background: '#eafcff', boxShadow: `0 0 8px ${CYAN}` }} />
            </div>
            <div style={{ fontSize: 9, color: CYAN_SOFT, letterSpacing: 1 }}>SAMPLE · en-GB</div>
          </div>
        </Panel>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Share+Tech+Mono&display=swap');
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes spinRev { to { transform: rotate(-360deg); } }
        @keyframes pulseCore { 0%,100% { opacity: 1; } 50% { opacity: 0.72; } }
        .spin-slow { animation: spin 26s linear infinite; }
        .spin-slow2 { animation: spinRev 40s linear infinite; }
        .spin-rev { animation: spinRev 18s linear infinite; }
        .spin-fast { animation: spin 9s linear infinite; }
        .pulse-core { animation: pulseCore 2.4s ease-in-out infinite; transform-origin: center; transform-box: fill-box; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-thumb { background: rgba(34,211,238,0.3); border-radius: 3px; }
      `}</style>
    </div>
  )
}

const btn: React.CSSProperties = {
  background: 'rgba(34,211,238,0.12)', border: `1px solid ${CYAN_SOFT}`, color: CYAN,
  borderRadius: 6, padding: '6px 10px', fontSize: 9, letterSpacing: 1, cursor: 'pointer',
  fontFamily: 'inherit', whiteSpace: 'nowrap',
}
