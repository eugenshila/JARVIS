import { useState, useEffect, useRef } from 'react'

/*
  JARVIS holographic desktop dashboard.
  A faithful, animated recreation of the classic cyan Iron Man / JARVIS HUD:
  central arc reactor, circular clock + gauge dials, disk / energy readouts,
  a multi-day weather panel on the right, and an audio spectrum with media
  controls along the bottom. Pure SVG + canvas, no backend required, so it
  renders identically on a static GitHub Pages link.
*/

const CYAN = '#22d3ee'
const CYAN_SOFT = 'rgba(34,211,238,0.55)'
const CYAN_DIM = 'rgba(34,211,238,0.25)'

// --- small geometry helpers -------------------------------------------------
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

// --- circular gauge with a value arc ---------------------------------------
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

// --- weather glyphs (cyan line icons) --------------------------------------
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
  // cloud
  return (
    <svg width={s} height={s} viewBox="0 0 24 24"><path d="M7 17a4 4 0 0 1 .5-8 5 5 0 0 1 9.5 2 3.2 3.2 0 0 1-.5 6H7z" {...st} /></svg>)
}

type Forecast = { day: string; icon: string; hi: number; lo: number; desc: string }
const FORECAST: Forecast[] = [
  { day: 'TONIGHT', icon: 'moon', hi: 13, lo: 9, desc: 'Clear' },
  { day: 'FRI', icon: 'sun', hi: 23, lo: 11, desc: 'Sunny' },
  { day: 'SAT', icon: 'cloud', hi: 19, lo: 12, desc: 'Cloudy' },
  { day: 'SUN', icon: 'rain', hi: 17, lo: 10, desc: 'Showers' },
  { day: 'MON', icon: 'cloud', hi: 18, lo: 11, desc: 'Overcast' },
  { day: 'TUE', icon: 'sun', hi: 21, lo: 12, desc: 'Sunny' },
  { day: 'WED', icon: 'rain', hi: 14, lo: 9, desc: 'Rain' },
]

const HALO = (r: number) => ({ filter: `drop-shadow(0 0 ${r}px rgba(34,211,238,0.6))` })

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
    <svg width={size} height={size} style={{ ...HALO(18) }}>
      <defs>
        <radialGradient id="core" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#eafcff" />
          <stop offset="35%" stopColor="#8be9ff" />
          <stop offset="70%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="rgba(34,211,238,0)" />
        </radialGradient>
      </defs>
      {/* outer rotating tick ring */}
      <g className="spin-slow" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>
        <TickRing cx={c} cy={c} r={size * 0.47} count={72} len={10} />
      </g>
      <circle cx={c} cy={c} r={size * 0.45} fill="none" stroke={CYAN_DIM} strokeWidth={1} />
      {/* segmented ring, counter rotating */}
      <g className="spin-rev" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>
        {[0, 90, 180, 270].map(a => (
          <path key={a} d={arcPath(c, c, size * 0.4, a + 8, a + 82)} fill="none"
            stroke={CYAN} strokeWidth={3} strokeLinecap="round" style={HALO(5)} />
        ))}
      </g>
      {/* dashed mid ring */}
      <g className="spin-slow2" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>
        <circle cx={c} cy={c} r={size * 0.34} fill="none" stroke={CYAN_SOFT}
          strokeWidth={1.5} strokeDasharray="2 8" />
      </g>
      {/* coil ring */}
      <g className="spin-fast" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>{coils}</g>
      <circle cx={c} cy={c} r={size * 0.19} fill="none" stroke={CYAN} strokeWidth={2} style={HALO(6)} />
      {/* glowing core */}
      <circle cx={c} cy={c} r={size * 0.16} fill="url(#core)" className="pulse-core" />
      <circle cx={c} cy={c} r={size * 0.055} fill="#f2feff" style={HALO(14)} />
    </svg>
  )
}

// --- audio spectrum canvas --------------------------------------------------
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
  return <canvas ref={ref} width={720} height={90} style={{ width: '100%', height: 90, display: 'block' }} />
}

// --- panel chrome -----------------------------------------------------------
function Panel({ title, children, style }: { title?: string; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      border: `1px solid ${CYAN_DIM}`, borderRadius: 10, padding: 12,
      background: 'rgba(6,16,22,0.55)', backdropFilter: 'blur(4px)',
      boxShadow: 'inset 0 0 24px rgba(34,211,238,0.06)', ...style,
    }}>
      {title && <div style={{ fontSize: 10, letterSpacing: 2, color: CYAN_SOFT, marginBottom: 8 }}>{title}</div>}
      {children}
    </div>
  )
}

export default function JarvisDashboard() {
  const [now, setNow] = useState(new Date())
  const [sys, setSys] = useState({ cpu: 74, ram: 15, swap: 49 })
  const [timer, setTimer] = useState(160) // seconds -> shows 2:40 style
  useEffect(() => {
    const id = setInterval(() => {
      setNow(new Date())
      setSys(s => ({
        cpu: Math.max(8, Math.min(96, s.cpu + (Math.random() - 0.5) * 6)),
        ram: Math.max(5, Math.min(90, s.ram + (Math.random() - 0.5) * 4)),
        swap: Math.max(5, Math.min(90, s.swap + (Math.random() - 0.5) * 4)),
      }))
      setTimer(t => (t <= 0 ? 300 : t - 1))
    }, 1000)
    return () => clearInterval(id)
  }, [])

  const hh = String(now.getHours()).padStart(2, '0')
  const mm = String(now.getMinutes()).padStart(2, '0')
  const ss = String(now.getSeconds()).padStart(2, '0')
  const weekday = now.toLocaleDateString([], { weekday: 'long' })
  const monthName = now.toLocaleDateString([], { month: 'long' })
  const dayNum = now.getDate()
  const tMin = Math.floor(timer / 60), tSec = String(timer % 60).padStart(2, '0')

  return (
    <div style={{
      position: 'fixed', inset: 0, background:
        'radial-gradient(1200px 700px at 50% 55%, rgba(10,40,55,0.55), rgba(2,6,10,0.98) 70%), #01050a',
      color: CYAN, fontFamily: '"Share Tech Mono","JetBrains Mono",monospace', overflow: 'hidden',
    }}>
      {/* faint grid + scanlines */}
      <div style={{ position: 'absolute', inset: 0, backgroundImage:
        'linear-gradient(rgba(34,211,238,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(34,211,238,0.04) 1px,transparent 1px)',
        backgroundSize: '46px 46px' }} />
      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', background:
        'repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,0.18) 3px,rgba(0,0,0,0.18) 4px)' }} />

      {/* ===== TOP-LEFT: clock / calendar dial ===== */}
      <div style={{ position: 'absolute', top: '3.5%', left: '2.5%', display: 'flex', gap: 14, alignItems: 'center' }}>
        <div style={{ position: 'relative', width: 168, height: 168 }}>
          <svg width={168} height={168} style={HALO(10)}>
            <g className="spin-slow" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>
              <TickRing cx={84} cy={84} r={80} count={60} len={7} />
            </g>
            <circle cx={84} cy={84} r={66} fill="none" stroke={CYAN_DIM} strokeWidth={1} />
            <path d={arcPath(84, 84, 66, 210, 210 - (now.getSeconds() / 60) * 300)} fill="none"
              stroke={CYAN} strokeWidth={3} strokeLinecap="round" style={HALO(5)} />
          </svg>
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ fontSize: 11, letterSpacing: 2, color: CYAN_SOFT }}>{weekday.toUpperCase()}</div>
            <div style={{ fontSize: 40, fontWeight: 700, lineHeight: 1, textShadow: `0 0 10px ${CYAN}` }}>{dayNum}</div>
            <div style={{ fontSize: 11, letterSpacing: 2, color: CYAN_SOFT }}>{monthName.toUpperCase()}</div>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 30, fontWeight: 700, letterSpacing: 3, textShadow: `0 0 10px ${CYAN}` }}>
            {hh}:{mm}<span style={{ fontSize: 16, color: CYAN_SOFT }}>:{ss}</span>
          </div>
          <div style={{ fontSize: 10, letterSpacing: 2, color: CYAN_SOFT, marginTop: 4 }}>LOCAL SYSTEM TIME</div>
          <div style={{ fontSize: 10, letterSpacing: 2, color: CYAN_DIM }}>J.A.R.V.I.S · MARK XLII</div>
        </div>
      </div>

      {/* ===== TOP-CENTER: cpu / ram / swap gauges ===== */}
      <div style={{ position: 'absolute', top: '4%', left: '38%', display: 'flex', gap: 18, alignItems: 'center' }}>
        <Gauge size={92} value={sys.cpu} label="CPU" />
        <Gauge size={78} value={sys.ram} label="RAM" color="#7dd3fc" />
        <Gauge size={78} value={sys.swap} label="SWAP" color="#67e8f9" />
      </div>

      {/* ===== TOP-CENTER-RIGHT: focus timer ring ===== */}
      <div style={{ position: 'absolute', top: '3%', left: '60%', width: 120, height: 120 }}>
        <svg width={120} height={120} style={HALO(8)}>
          <g className="spin-rev" style={{ transformOrigin: 'center', transformBox: 'fill-box' } as any}>
            <TickRing cx={60} cy={60} r={56} count={48} len={6} />
          </g>
          <circle cx={60} cy={60} r={44} fill="none" stroke={CYAN_DIM} strokeWidth={3} />
          <path d={arcPath(60, 60, 44, 0, (1 - timer / 300) * 359)} fill="none" stroke={CYAN}
            strokeWidth={3} strokeLinecap="round" style={HALO(5)} />
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ fontSize: 26, fontWeight: 700, textShadow: `0 0 8px ${CYAN}` }}>{tMin}:{tSec}</div>
          <div style={{ fontSize: 8, letterSpacing: 2, color: CYAN_SOFT }}>FOCUS</div>
        </div>
      </div>

      {/* ===== TOP-RIGHT: header + city ===== */}
      <div style={{ position: 'absolute', top: '3.5%', right: '2.5%', textAlign: 'right' }}>
        <div style={{ fontSize: 12, letterSpacing: 1, color: CYAN_SOFT }}>{now.toLocaleDateString([], { year: 'numeric', month: '2-digit', day: '2-digit' })}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end', marginTop: 6 }}>
          <WxIcon kind="moon" s={26} />
          <div>
            <div style={{ fontSize: 22, fontWeight: 700, textShadow: `0 0 8px ${CYAN}` }}>13°</div>
            <div style={{ fontSize: 10, letterSpacing: 1, color: CYAN_SOFT }}>NAIROBI · CLEAR</div>
          </div>
        </div>
      </div>

      {/* ===== CENTER: arc reactor ===== */}
      <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}>
        <ArcReactor size={Math.min(460, Math.round(window.innerWidth * 0.32))} />
      </div>
      {/* scattered labels around reactor */}
      {[
        { t: '40%', l: '30%', txt: 'NEURAL LINK' }, { t: '36%', l: '64%', txt: 'REPULSOR' },
        { t: '62%', l: '31%', txt: 'DIAGNOSTIC' }, { t: '64%', l: '63%', txt: 'STARK IND.' },
      ].map((p, i) => (
        <div key={i} style={{ position: 'absolute', top: p.t, left: p.l, fontSize: 9, letterSpacing: 2,
          color: CYAN_DIM, transform: 'translate(-50%,-50%)' }}>{p.txt}</div>
      ))}

      {/* ===== LEFT: disk + energy ===== */}
      <div style={{ position: 'absolute', top: '34%', left: '2.5%', width: 210, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: 4, color: CYAN_SOFT, textShadow: `0 0 10px ${CYAN}` }}>
          EXPO<span style={{ color: CYAN }}> 2010</span>
        </div>
        <Panel title="STORAGE VOLUME">
          <div style={{ fontSize: 11, color: CYAN }}>Total: 100 GB</div>
          <div style={{ fontSize: 11, color: CYAN_SOFT }}>Free: 2 GB</div>
          <div style={{ height: 6, background: CYAN_DIM, borderRadius: 3, marginTop: 8, overflow: 'hidden' }}>
            <div style={{ width: '98%', height: '100%', background: CYAN, boxShadow: `0 0 8px ${CYAN}` }} />
          </div>
          <div style={{ fontSize: 9, color: CYAN_DIM, marginTop: 6, lineHeight: 1.6 }}>
            <div>▸ Local disk C:</div><div>▸ Arduino · AMP 2</div><div>▸ Dead Space · Limbo</div>
          </div>
        </Panel>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <Gauge size={96} value={100} label="ENERGY" sub="%" />
          <div style={{ fontSize: 9, color: CYAN_DIM, lineHeight: 1.7 }}>
            <div>REACTOR ONLINE</div><div>OUTPUT 3.2 GJ/s</div><div>TEMP 284 K</div><div>STABLE</div>
          </div>
        </div>
      </div>

      {/* ===== BOTTOM-LEFT: small gauge cluster ===== */}
      <div style={{ position: 'absolute', bottom: '15%', left: '2.5%', display: 'flex', gap: 10 }}>
        <Gauge size={66} value={sys.ram} label="I/O" color="#67e8f9" />
        <Gauge size={66} value={sys.cpu} label="NET" color="#7dd3fc" />
        <div style={{ alignSelf: 'center', fontSize: 9, color: CYAN_DIM, lineHeight: 1.7 }}>
          <div>COMMS · ONLINE</div><div>NEW MAIL · 3</div><div>91.219.164.5</div>
        </div>
      </div>

      {/* ===== RIGHT: weather forecast ===== */}
      <div style={{ position: 'absolute', top: '17%', right: '2.5%', width: 232 }}>
        <Panel title="7-DAY FORECAST · NAIROBI">
          {FORECAST.map((f, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0',
              borderBottom: i < FORECAST.length - 1 ? `1px solid ${CYAN_DIM}` : 'none' }}>
              <div style={{ width: 44, fontSize: 10, letterSpacing: 1, color: CYAN_SOFT }}>{f.day}</div>
              <WxIcon kind={f.icon} s={22} />
              <div style={{ flex: 1, fontSize: 10, color: CYAN_DIM }}>{f.desc}</div>
              <div style={{ fontSize: 12, color: CYAN }}>{f.hi}°<span style={{ color: CYAN_DIM }}> / {f.lo}°</span></div>
            </div>
          ))}
        </Panel>
      </div>

      {/* ===== BOTTOM: audio spectrum + media controls ===== */}
      <div style={{ position: 'absolute', bottom: '3%', left: '50%', transform: 'translateX(-50%)', width: '58%', maxWidth: 900 }}>
        <Panel>
          <Spectrum />
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 8 }}>
            <div style={{ display: 'flex', gap: 14, color: CYAN }}>
              <span style={{ fontSize: 16, cursor: 'pointer' }}>⏮</span>
              <span style={{ fontSize: 18, cursor: 'pointer', textShadow: `0 0 8px ${CYAN}` }}>⏸</span>
              <span style={{ fontSize: 16, cursor: 'pointer' }}>⏭</span>
            </div>
            <div style={{ flex: 1, height: 4, background: CYAN_DIM, borderRadius: 2, position: 'relative' }}>
              <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '42%', background: CYAN, borderRadius: 2, boxShadow: `0 0 8px ${CYAN}` }} />
              <div style={{ position: 'absolute', left: '42%', top: -3, width: 10, height: 10, borderRadius: '50%', background: '#eafcff', boxShadow: `0 0 8px ${CYAN}` }} />
            </div>
            <div style={{ fontSize: 10, color: CYAN_SOFT, letterSpacing: 1 }}>01:24 / 03:12</div>
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
      `}</style>
    </div>
  )
}
