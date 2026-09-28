import { useEffect, useRef, useState } from "react";

type ChatMessage = { role: "user" | "assistant"; content: string };
type Status = "checking" | "ready" | "model_missing" | "unavailable" | "mock";

const isPagesMock = () => typeof window !== "undefined" && window.location.hostname.includes("github.io");

const mockPreflight = {
  adhd: {
    configured: true,
    latest: {
      icon: "⚖️",
      mode: "Steady",
      support_load: 3.3,
      support_level: "Light support is enough today",
      focus_pattern: "25/5 Pomodoro works well",
    },
  },
  connections: {
    google: { credentials: false, authenticated: false },
    microsoft: { implemented: false },
    local: { calendar_exists: true, email_exists: true },
    policy: "Read-only by default; sending mail or changing events requires explicit confirmation.",
  },
  career: {
    mode: "seeking",
    stats: {
      storage: "SQLite + JSON files",
      postgres_required: false,
      workspace: "JAUTOMATIC demo workspace",
      jobs: 12,
      applications: 7,
      sent: 5,
      materials_ready: 3,
      interviews: 1,
      offers: 0,
      follow_ups_due: 2,
      training: { total: 5, in_progress: 2, completed: 1 },
      top_matches: [
        { score: 87, title: "IT Support Analyst", company: "Nairobi Tech Services", status: "materials_ready" },
        { score: 82, title: "Junior Automation Assistant", company: "Remote Operations Co", status: "shortlisted" },
      ],
    },
  },
  apps: {
    count: 3,
    names: ["JAUTOMATIC", "Outlook", "Chrome"],
    items: [
      { name: "JAUTOMATIC", path: "C:\\Program Files\\JAUTOMATIC\\jautomatic.exe" },
      { name: "Outlook", path: "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE" },
      { name: "Chrome", path: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    ],
  },
};

export default function IronManCircularHUD() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chatEnd = useRef<HTMLDivElement>(null);
  const busyRef = useRef(false);
  const [time, setTime] = useState(new Date());
  const [status, setStatus] = useState<Status>("checking");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState<any>({ voice_name: "detecting voice" });
  const lastVoiceEvent = useRef(0);
  const [focusItems, setFocusItems] = useState<string[]>(() => {
    try {
      const raw = JSON.parse(localStorage.getItem("jarvis_focus") || "[]");
      return Array.isArray(raw) ? raw.filter((item): item is string => typeof item === "string").slice(0, 3) : [];
    } catch {
      return [];
    }
  });
  const [newFocus, setNewFocus] = useState("");
  const [preflight, setPreflight] = useState<any>(null);
  const [adhdForm, setAdhdForm] = useState({ energy: 5, focus: 5, stress: 5, sleep_hours: 7, mood: "", medication: "unknown" });
  const [adhdResult, setAdhdResult] = useState("");
  const [actionStatus, setActionStatus] = useState("");
  const userName = localStorage.getItem("jarvis_user_name") || "Eugene";

  useEffect(() => {
    const timer = window.setInterval(() => setTime(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const checkStatus = async () => {
    if (isPagesMock()) {
      setStatus("mock");
      return;
    }
    try {
      const res = await fetch("/hud/status");
      if (!res.ok) throw new Error("JARVIS server is not running");
      const data = await res.json();
      setStatus(data.ollama);
    } catch { setStatus("unavailable"); }
  };
  useEffect(() => {
    checkStatus();
    const timer = window.setInterval(checkStatus, 15000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);
  useEffect(() => { localStorage.setItem("jarvis_focus", JSON.stringify(focusItems)); }, [focusItems]);

  const refreshPreflight = async () => {
    if (isPagesMock()) {
      setPreflight(mockPreflight);
      return;
    }
    try {
      const res = await fetch("/hud/preflight");
      if (res.ok) setPreflight(await res.json());
      else setPreflight(mockPreflight);
    } catch { setPreflight(mockPreflight); }
  };
  useEffect(() => {
    refreshPreflight();
    const timer = window.setInterval(refreshPreflight, 30000);
    return () => window.clearInterval(timer);
  }, []);

  // Circular HUD canvas — matches screenshot
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let animId: number;
    let rot = 0;

    const draw = () => {
      rot += 0.008;
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      const base = Math.min(w, h) / 2 - 20;

      ctx.clearRect(0, 0, w, h);

      // Background dark
      ctx.fillStyle = "#020208";
      ctx.fillRect(0, 0, w, h);

      // Outer glow blue
      const bgGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, base + 30);
      bgGrad.addColorStop(0, `rgba(6, 182, 212, ${0.15 + Math.sin(rot * 2) * 0.05})`);
      bgGrad.addColorStop(0.5, `rgba(6, 182, 212, 0.05)`);
      bgGrad.addColorStop(1, `rgba(0,0,0,0)`);
      ctx.fillStyle = bgGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, base + 30, 0, Math.PI * 2);
      ctx.fill();

      // Outer housing — 2 rings
      ctx.strokeStyle = `rgba(100, 116, 139, 0.5)`;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, base, 0, Math.PI * 2);
      ctx.stroke();

      ctx.strokeStyle = `rgba(6, 182, 212, 0.3)`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, base - 10, 0, Math.PI * 2);
      ctx.stroke();

      // Tick marks 72 like screenshot
      for (let i = 0; i < 72; i++) {
        const angle = (i / 72) * Math.PI * 2;
        const isMajor = i % 6 === 0;
        const r1 = base - (isMajor ? 5 : 2);
        const r2 = base - (isMajor ? 18 : 8);
        const x1 = cx + Math.cos(angle) * r1;
        const y1 = cy + Math.sin(angle) * r1;
        const x2 = cx + Math.cos(angle) * r2;
        const y2 = cy + Math.sin(angle) * r2;
        ctx.strokeStyle = isMajor ? `rgba(6, 182, 212, 0.8)` : `rgba(100, 116, 139, 0.4)`;
        ctx.lineWidth = isMajor ? 1.5 : 0.5;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // Modern segmented rings like second screenshot - more detailed
      // 60 small segments outer
      const outerSegR = base - 8;
      for (let i = 0; i < 60; i++) {
        const angle = (i / 60) * Math.PI * 2 + rot * 0.2;
        const gap = 0.02;
        const alpha = 0.2 + 0.6 * (Math.sin(rot*2 + i*0.3) * 0.5 + 0.5);
        if (alpha > 0.4) {
          ctx.strokeStyle = `rgba(6, 182, 212, ${alpha})`;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(cx, cy, outerSegR, angle + gap, angle + Math.PI / 30 - gap);
          ctx.stroke();
        }
      }

      // 24 larger blocks middle - like screenshot
      const midR = base - 28;
      for (let i = 0; i < 24; i++) {
        const angle = (i / 24) * Math.PI * 2 + rot * 0.25;
        const gap = 0.08;
        ctx.strokeStyle = i % 4 === 0 ? `rgba(34, 211, 238, ${0.8 + Math.sin(rot*3 + i)*0.2})` : `rgba(6, 182, 212, ${0.4 + Math.sin(rot + i) * 0.2})`;
        ctx.lineWidth = i % 4 === 0 ? 6 : 3;
        ctx.beginPath();
        ctx.arc(cx, cy, midR, angle + gap, angle + Math.PI / 12 - gap);
        ctx.stroke();
      }

      // 16 segmented inner ring rotating opposite - more modern
      const innerSegR = base - 50;
      for (let i = 0; i < 16; i++) {
        const angle = (i / 16) * Math.PI * 2 - rot * 0.3;
        const gap = 0.15;
        ctx.strokeStyle = `rgba(125, 211, 252, ${0.5 + Math.sin(rot*2 + i) * 0.3})`;
        ctx.lineWidth = 8;
        ctx.beginPath();
        ctx.arc(cx, cy, innerSegR, angle + gap, angle + Math.PI / 8 - gap);
        ctx.stroke();
      }

      // Inner blue glowing ring — main reactor ring - more modern with multi-glow like second screenshot
      // Multi-layer glow
      for (let g = 0; g < 5; g++) {
        ctx.strokeStyle = `rgba(6, 182, 212, ${0.15 - g*0.02})`;
        ctx.lineWidth = 12 - g*2;
        ctx.beginPath();
        ctx.arc(cx, cy, base - 70 - g*2, 0, Math.PI*2);
        ctx.stroke();
      }
      ctx.strokeStyle = `rgba(6, 182, 212, ${0.9 + Math.sin(rot * 3) * 0.1})`;
      ctx.lineWidth = 3;
      ctx.shadowColor = "#06b6d4";
      ctx.shadowBlur = 20;
      ctx.beginPath();
      ctx.arc(cx, cy, base - 70, 0, Math.PI * 2);
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Rotating energy prongs — 3 like arc reactor
      for (let i = 0; i < 3; i++) {
        const angle = (i / 3) * Math.PI * 2 + rot;
        const innerR = 30;
        const outerR = base - 80;
        const grad = ctx.createLinearGradient(
          cx + Math.cos(angle) * innerR,
          cy + Math.sin(angle) * innerR,
          cx + Math.cos(angle) * outerR,
          cy + Math.sin(angle) * outerR
        );
        grad.addColorStop(0, `rgba(255, 255, 255, 0.95)`);
        grad.addColorStop(0.3, `rgba(6, 182, 212, 0.9)`);
        grad.addColorStop(1, `rgba(6, 182, 212, 0.2)`);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(angle - 0.12) * innerR, cy + Math.sin(angle - 0.12) * innerR);
        ctx.lineTo(cx + Math.cos(angle - 0.08) * outerR, cy + Math.sin(angle - 0.08) * outerR);
        ctx.lineTo(cx + Math.cos(angle + 0.08) * outerR, cy + Math.sin(angle + 0.08) * outerR);
        ctx.lineTo(cx + Math.cos(angle + 0.12) * innerR, cy + Math.sin(angle + 0.12) * innerR);
        ctx.closePath();
        ctx.fill();
      }

      // Inner core — pulsing blue like screenshot
      const corePulse = 28 + Math.sin(rot * 2) * 4;
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, corePulse + 15);
      coreGrad.addColorStop(0, `rgba(255, 255, 255, 1)`);
      coreGrad.addColorStop(0.2, `rgba(6, 182, 212, 0.95)`);
      coreGrad.addColorStop(0.5, `rgba(6, 182, 212, 0.6)`);
      coreGrad.addColorStop(1, `rgba(6, 182, 212, 0)`);
      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, corePulse + 15, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = `rgba(255, 255, 255, ${0.95 + Math.sin(rot * 3) * 0.05})`;
      ctx.shadowColor = "#06b6d4";
      ctx.shadowBlur = 25;
      ctx.beginPath();
      ctx.arc(cx, cy, corePulse, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;

      // Center identity — JARVIS only (no reactor number)
      ctx.fillStyle = "rgba(0, 0, 0, 0.72)";
      ctx.beginPath();
      ctx.arc(cx, cy, 34, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#e2e8f0";
      ctx.font = "bold 16px Arial, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.shadowColor = "#06b6d4";
      ctx.shadowBlur = 10;
      ctx.fillText("JARVIS", cx, cy);
      ctx.shadowBlur = 0;

      // Inner small ring
      ctx.strokeStyle = `rgba(255, 255, 255, 0.5)`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, 45, 0, Math.PI * 2);
      ctx.stroke();

      // Data points around — like screenshot UI elements
      for (let i = 0; i < 4; i++) {
        const angle = (i / 4) * Math.PI * 2 + rot * 0.5;
        const r = base - 110;
        const x = cx + Math.cos(angle) * r;
        const y = cy + Math.sin(angle) * r;
        ctx.fillStyle = `rgba(6, 182, 212, ${0.6 + Math.sin(rot * 2 + i) * 0.3})`;
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
      }

      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(animId);
  }, []);


  useEffect(() => {
    if (isPagesMock()) {
      setVoiceStatus({ voice_name: "mock voice preview" });
      return;
    }
    let cancelled = false;
    const pollVoice = async () => {
      try {
        const res = await fetch("/hud/voice-status");
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        setVoiceStatus(data);
        setIsListening(Boolean(data.listening));
        const eventId = Number(data.event_id || 0);
        if (eventId && eventId !== lastVoiceEvent.current) {
          lastVoiceEvent.current = eventId;
          if (data.transcript) {
            setMessages(previous => [...previous, { role: "user", content: data.transcript }]);
          }
          if (data.response) {
            setMessages(previous => [...previous, { role: "assistant", content: data.response }]);
          }
        }
      } catch { /* voice companion may still be starting */ }
    };
    pollVoice();
    const timer = window.setInterval(pollVoice, 700);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, []);

  const send = async () => {
    if (!input.trim() || busy) return;
    const userMessage = input.trim();
    setInput("");
    setBusy(true);
    setError("");
    setMessages(previous => [...previous, { role: "user", content: userMessage }]);
    if (isPagesMock()) {
      window.setTimeout(() => {
        const answer = `Demo mode, Sir. On the installed MSI I would route this through local Ollama and connected tools. For this mock: Career OS has ${mockPreflight.career.stats.applications} applications tracked, ${mockPreflight.career.stats.follow_ups_due} follow-ups due, and PostgreSQL is not required.`;
        setMessages(previous => [...previous, { role: "assistant", content: answer }]);
        setBusy(false);
      }, 450);
      return;
    }
    try {
      const res = await fetch("/hud/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [...messages, { role: "user", content: userMessage }] }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "JARVIS could not respond.");
      const answer = String(data.content || "").trim();
      if (answer) setMessages(previous => [...previous, { role: "assistant", content: answer }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "JARVIS communication error.");
    } finally {
      setBusy(false);
    }
  };

  const assessAdhd = async () => {
    setActionStatus("");
    setAdhdResult("Assessing support state…");
    if (isPagesMock()) {
      const mock = `⚖️ **ADHD Support State — Steady**\n\nDemo only: this is not a medical diagnosis.\n\nEnergy ${adhdForm.energy}/10 | Focus ${adhdForm.focus}/10 | Stress ${adhdForm.stress}/10 | Sleep ${adhdForm.sleep_hours}h | Mood: ${adhdForm.mood || "not set"}\n\nRecommended: 25/5 Pomodoro, max three priorities, log one tiny win.`;
      setAdhdResult(mock);
      setPreflight({ ...mockPreflight, adhd: { ...mockPreflight.adhd, latest: { ...mockPreflight.adhd.latest, support_load: Math.max(1, Math.min(10, 10 - adhdForm.energy + adhdForm.stress / 2)).toFixed(1) } } });
      return;
    }
    try {
      const res = await fetch("/hud/adhd-state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(adhdForm),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not assess ADHD support state.");
      setAdhdResult(String(data.content || ""));
      refreshPreflight();
    } catch (e) {
      setAdhdResult(e instanceof Error ? e.message : "ADHD support check failed.");
    }
  };

  const connectGoogle = async () => {
    if (isPagesMock()) {
      setActionStatus("Demo mode: Google OAuth opens in the installed app, stores a local token, and stays read-only by default.");
      return;
    }
    setActionStatus("Starting Google OAuth setup… your browser may open a consent window.");
    try {
      const res = await fetch("/hud/connections/google/setup", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Google setup failed.");
      setActionStatus(String(data.content || "Google setup complete."));
      refreshPreflight();
    } catch (e) {
      setActionStatus(e instanceof Error ? e.message : "Google setup failed.");
    }
  };

  const launchApp = async (appName: string) => {
    if (!window.confirm(`Launch ${appName}? JARVIS only opens apps from your approved allow-list.`)) return;
    if (isPagesMock()) {
      setActionStatus(`Demo mode: ${appName} would launch from the approved local allow-list after confirmation.`);
      return;
    }
    setActionStatus(`Launching ${appName}…`);
    try {
      const res = await fetch("/hud/apps/launch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ app: appName, confirm: true }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Launch failed.");
      setActionStatus(String(data.content || "Launch command sent."));
    } catch (e) {
      setActionStatus(e instanceof Error ? e.message : "Launch failed.");
    }
  };

  const setCareerMode = async (mode: string) => {
    if (isPagesMock()) {
      setPreflight((current:any) => ({ ...(current || mockPreflight), career: { ...((current || mockPreflight).career), mode } }));
      setActionStatus(`Demo mode: career mode set to ${mode}. Installed JARVIS saves this in ~/.jarvis/career.json.`);
      return;
    }
    setActionStatus(`Setting career mode to ${mode}…`);
    try {
      const res = await fetch("/hud/career/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not set career mode.");
      setActionStatus(String(data.content || "Career mode updated."));
      refreshPreflight();
    } catch (e) {
      setActionStatus(e instanceof Error ? e.message : "Career mode update failed.");
    }
  };

  const careerToday = async () => {
    if (isPagesMock()) {
      const mode = preflight?.career?.mode || "seeking";
      setActionStatus(`📅 **Career Plan for Today — Mode: ${mode}**\n\n1. Follow up on 2 applications in JAUTOMATIC.\n2. Complete one free training module tied to your target role.\n3. Apply to or prepare the highest match, then stop — no endless scrolling.\n\nDemo data only. The MSI reads your real local JAUTOMATIC SQLite workspace.`);
      return;
    }
    setActionStatus("Building career plan…");
    try {
      const res = await fetch("/hud/career/today");
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Career plan failed.");
      setActionStatus(String(data.content || "No plan returned."));
      refreshPreflight();
    } catch (e) {
      setActionStatus(e instanceof Error ? e.message : "Career plan failed.");
    }
  };

  const openJautomatic = async () => {
    if (!window.confirm("Open JAUTOMATIC JOB SEARCH?")) return;
    if (isPagesMock()) {
      setActionStatus("Demo mode: the installed MSI would open JAUTOMATIC from C:\\Program Files\\JAUTOMATIC or from your source checkout.");
      return;
    }
    setActionStatus("Opening JAUTOMATIC…");
    try {
      const res = await fetch("/hud/career/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ app: "JAUTOMATIC", confirm: true }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not open JAUTOMATIC.");
      setActionStatus(String(data.content || "Open command sent."));
    } catch (e) {
      setActionStatus(e instanceof Error ? e.message : "Could not open JAUTOMATIC.");
    }
  };

  const addFocus = () => {
    if (newFocus.trim()) setFocusItems(items => [...items, newFocus.trim()].slice(0, 3));
    setNewFocus("");
  };
  const statusLabel = status === "mock" ? "PAGES MOCK" : status === "ready" ? "OLLAMA READY" : status === "model_missing" ? "MODEL MISSING" : status === "checking" ? "CHECKING" : "OLLAMA OFFLINE";

  return (
    <div className="min-h-screen bg-[#01050a] text-cyan-100 font-mono relative overflow-x-hidden" style={{backgroundImage:"radial-gradient(circle at 50% 45%, rgba(0,180,255,.10), transparent 32%), linear-gradient(rgba(6,182,212,.025) 1px, transparent 1px), linear-gradient(90deg, rgba(6,182,212,.025) 1px, transparent 1px)", backgroundSize:"auto, 38px 38px, 38px 38px"}}>
      <header className="border-b border-cyan-800/40 bg-black/70 px-5 py-3 flex flex-wrap items-center justify-between gap-3 relative z-10">
        <div className="flex items-center gap-3"><div className="flex items-center gap-3"><div className="w-9 h-9 rounded-full border-2 border-cyan-400 shadow-[0_0_22px_rgba(6,182,212,.65)] flex items-center justify-center"><div className="w-4 h-4 rounded-full bg-cyan-200 shadow-[0_0_18px_#06b6d4]"/></div><span className="text-cyan-100 tracking-[.12em] font-bold text-xl">JARVIS</span></div><div className="hidden md:flex items-center gap-4 text-[10px]"><span className={status === "mock" ? "text-amber-400" : "text-emerald-400"}>● {status === "mock" ? "GITHUB PAGES MOCK" : "OLLAMA CONNECTED"}</span><span className="text-cyan-400">◈ Qwen2.5:3B</span><span className={status === "mock" ? "text-amber-400" : "text-emerald-400"}>● {status === "mock" ? "STATIC DEMO" : "LOCAL API RUNNING"}</span></div></div>
        <div className="flex items-center gap-4 text-[11px]"><span className="hidden sm:inline text-cyan-300">⌁ Always here. Always listening.</span><span className="text-slate-400">{time.toLocaleDateString()} • {time.toLocaleTimeString()}</span><button onClick={checkStatus} className={`border px-3 py-1 rounded ${status === "ready" ? "border-emerald-600 text-emerald-400" : "border-amber-700 text-amber-400"}`} title="Recheck Ollama connection">● {statusLabel} ↻</button></div>
      </header>
      <div className="relative z-10 grid grid-cols-1 xl:grid-cols-[250px_minmax(400px,1fr)_360px] min-h-[calc(100vh-60px)]">
        <aside className="p-4 border-r border-cyan-900/40 bg-black/45 space-y-4">
          <section className="hud-panel hud-brief"><div className="text-2xl font-bold text-cyan-300">Good morning, Sir</div><p className="text-slate-300 text-xs mt-2">Here’s what’s happening today.</p><div className="mt-4 space-y-3 text-xs"><div className="flex justify-between border-t border-cyan-900/40 pt-3"><span>☀ Nairobi, Kenya</span><span className="text-cyan-300">LIVE</span></div><div className="flex justify-between border-t border-cyan-900/40 pt-3"><span>▣ Today’s Tasks</span><span className="text-cyan-300">{focusItems.length} pending</span></div><div className="flex justify-between border-t border-cyan-900/40 pt-3"><span>▤ Latest News</span><span className="text-cyan-300">Standby</span></div></div></section>
          <section className="hud-panel"><h2>WEATHER</h2><div className="mt-3 text-cyan-300 text-3xl">Nairobi</div><p className="text-slate-400 text-xs mt-1">Live weather feed will appear here.</p></section>
          <section className="hud-panel"><h2>MODEL LINK</h2><div className="text-cyan-300 text-lg mt-3">{status === "mock" ? "GitHub Pages mock" : "qwen2.5:3b"}</div><p className="text-slate-400 text-[11px] mt-2">{status === "mock" ? "Static preview with sample Career OS, ADHD, and app data. The MSI uses local Ollama and JAUTOMATIC." : "Connected locally through Ollama on this computer."}</p><p className="mt-3 text-[11px] text-amber-400">{status === "mock" ? "Demo only — no local files or accounts are touched." : status === "model_missing" ? "Run: ollama pull qwen2.5:3b" : status === "unavailable" ? "Start Ollama and the JARVIS server." : status === "ready" ? "Model installed and ready to answer." : "Checking local model..."}</p></section>
          <section className="hud-panel"><h2>TODAY’S THREE PRIORITIES</h2><div className="space-y-2 mt-3">{focusItems.length ? focusItems.map((item,i) => <div key={i} className="flex gap-2 items-start text-xs"><button className="text-cyan-400 border border-cyan-900 rounded-full w-5 h-5 shrink-0" title="Mark complete" onClick={() => setFocusItems(items => items.filter((_,j) => i !== j))}>✓</button><span>{item}</span></div>) : <p className="text-slate-500 text-[11px]">Set up to three things to focus on today.</p>}</div>{focusItems.length < 3 && <div className="flex gap-1 mt-3"><input className="hud-input min-w-0 w-full" value={newFocus} onChange={e => setNewFocus(e.target.value)} onKeyDown={e => e.key === "Enter" && addFocus()} placeholder="Add a priority"/><button onClick={addFocus} className="hud-button">+</button></div>}</section>
          <section className="hud-panel"><h2>ADHD SUPPORT STATE</h2><p className="text-slate-400 text-[11px] mt-2">Daily operating mode, not a medical diagnosis.</p><div className="mt-3 space-y-2 text-[11px]"><label className="block">Energy {adhdForm.energy}/10<input type="range" min="1" max="10" value={adhdForm.energy} onChange={e => setAdhdForm({...adhdForm, energy: Number(e.target.value)})} className="w-full"/></label><label className="block">Focus {adhdForm.focus}/10<input type="range" min="1" max="10" value={adhdForm.focus} onChange={e => setAdhdForm({...adhdForm, focus: Number(e.target.value)})} className="w-full"/></label><label className="block">Stress {adhdForm.stress}/10<input type="range" min="1" max="10" value={adhdForm.stress} onChange={e => setAdhdForm({...adhdForm, stress: Number(e.target.value)})} className="w-full"/></label><div className="grid grid-cols-2 gap-2"><input className="hud-input w-full" type="number" min="0" max="24" value={adhdForm.sleep_hours} onChange={e => setAdhdForm({...adhdForm, sleep_hours: Number(e.target.value)})} title="Sleep hours"/><input className="hud-input w-full" value={adhdForm.mood} onChange={e => setAdhdForm({...adhdForm, mood: e.target.value})} placeholder="Mood"/></div><select className="hud-input w-full" value={adhdForm.medication} onChange={e => setAdhdForm({...adhdForm, medication: e.target.value})}><option value="unknown">Medication: unknown</option><option value="not_applicable">Medication: not applicable</option><option value="taken">Medication: taken</option><option value="skipped">Medication: skipped</option></select><button onClick={assessAdhd} className="hud-button w-full">ASSESS SUPPORT MODE</button>{preflight?.adhd?.latest && <div className="text-cyan-300 border-t border-cyan-900/40 pt-2">Latest: {preflight.adhd.latest.icon} {preflight.adhd.latest.mode} • load {preflight.adhd.latest.support_load}/10</div>}{adhdResult && <pre className="whitespace-pre-wrap text-[10px] text-slate-300 max-h-40 overflow-y-auto border border-cyan-900/40 p-2">{adhdResult.split("\n").slice(0, 10).join("\n")}</pre>}</div></section>
          <section className="hud-panel"><h2>CONNECTIONS</h2><div className="mt-3 space-y-2 text-[11px]"><div className="flex justify-between"><span>Google Calendar/Gmail</span><span className={preflight?.connections?.google?.authenticated ? "text-emerald-400" : "text-amber-400"}>{preflight?.connections?.google?.authenticated ? "CONNECTED" : preflight?.connections?.google?.credentials ? "READY TO SIGN IN" : "SETUP NEEDED"}</span></div><div className="flex justify-between"><span>Microsoft Outlook/365</span><span className="text-slate-400">GUIDE READY</span></div><div className="flex justify-between"><span>Local fallback</span><span className="text-cyan-300">JSON</span></div><button onClick={connectGoogle} className="hud-button w-full mt-2">CONNECT GOOGLE</button></div></section>
          <section className="hud-panel"><h2>CAREER OS</h2><p className="text-slate-400 text-[11px] mt-2">Powered by JAUTOMATIC JOB SEARCH. SQLite + JSON; PostgreSQL not required.</p><div className="mt-3 space-y-2 text-[11px]"><div className="flex justify-between"><span>Mode</span><span className="text-cyan-300 uppercase">{preflight?.career?.mode || "seeking"}</span></div><div className="flex justify-between"><span>Jobs tracked</span><span className="text-cyan-300">{preflight?.career?.stats?.jobs ?? 0}</span></div><div className="flex justify-between"><span>Applications</span><span className="text-cyan-300">{preflight?.career?.stats?.applications ?? 0}</span></div><div className="flex justify-between"><span>Follow-ups due</span><span className={(preflight?.career?.stats?.follow_ups_due || 0) ? "text-amber-400" : "text-emerald-400"}>{preflight?.career?.stats?.follow_ups_due ?? 0}</span></div><div className="grid grid-cols-2 gap-2"><button onClick={careerToday} className="hud-button">TODAY</button><button onClick={openJautomatic} className="hud-button">OPEN</button></div><select className="hud-input w-full" value={preflight?.career?.mode || "seeking"} onChange={e => setCareerMode(e.target.value)}><option value="seeking">Actively seeking</option><option value="employed">Employed + growing</option><option value="open_to_better">Open to better</option><option value="paused">Paused</option></select></div></section>
          <section className="hud-panel"><h2>APP LAUNCHER</h2><p className="text-slate-400 text-[11px] mt-2">Approved software only. JARVIS will ask before launch.</p><div className="mt-3 flex flex-wrap gap-2">{preflight?.apps?.items?.length ? preflight.apps.items.slice(0, 5).map((app:any) => <button key={app.name} onClick={() => launchApp(app.name)} className="hud-button text-[10px]">{app.name}</button>) : <span className="text-slate-500 text-[11px]">No approved apps yet. Use CLI: jarvis apps --discover</span>}</div>{actionStatus && <pre className="whitespace-pre-wrap text-[10px] text-amber-300 mt-3 max-h-32 overflow-y-auto">{actionStatus}</pre>}</section>
          <section className="hud-panel"><h2>VOICE LINK</h2><p className="text-slate-400 text-[11px] mt-2">Voice is handled by the Windows desktop companion. Wake with “Jarvis” or double-clap; no microphone button is required. <span className="text-cyan-300">{voiceStatus.voice_name || "detecting voice"}</span>.</p></section>
        </aside>
        <main className="flex flex-col items-center justify-center py-4 px-4 min-w-0">
          <div className="text-center mb-2"><div className="text-2xl font-semibold tracking-[.25em] text-cyan-100">JARVIS</div><div className="text-[9px] tracking-[.45em] text-cyan-600 mt-1">PERSONAL LOCAL INTELLIGENCE</div></div>
          <div className="text-cyan-600 tracking-[.3em] text-[10px] mb-2">INTERACTIVE REACTOR INTERFACE</div>
          <div className="relative w-full max-w-[580px] aspect-square"><canvas ref={canvasRef} width={560} height={560} className="w-full h-full"/><div className="absolute inset-0 flex items-center justify-center pointer-events-none"><span className="mt-[135px] text-[10px] tracking-[.3em] text-cyan-300/80">{busy ? "PROCESSING" : isListening ? "LISTENING" : status === "ready" ? "AWAITING COMMAND" : "LINK STANDBY"}</span></div></div>
          <div className="w-full max-w-[720px] grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2"><section className="hud-panel"><h2>STOCK MARKET</h2><div className="grid grid-cols-2 gap-2 mt-3 text-xs"><span>S&P 500</span><span className="text-right text-slate-400">LIVE FEED</span><span>NASDAQ</span><span className="text-right text-slate-400">LIVE FEED</span><span>DOW JONES</span><span className="text-right text-slate-400">LIVE FEED</span><span>NSE KENYA</span><span className="text-right text-slate-400">LIVE FEED</span></div></section><section className="hud-panel"><h2>LATEST NEWS</h2><div className="space-y-2 mt-3 text-xs text-slate-300"><div>Local news feed ready</div><div>Global headlines ready</div><div>Technology headlines ready</div></div></section></div><div className="flex flex-wrap gap-4 justify-center text-[10px] tracking-widest text-cyan-600 mt-3"><span>USER: {userName.toUpperCase()}</span><span>MODEL: QWEN 2.5 3B</span><span>ENGINE: OLLAMA</span></div>
        </main>
        <aside className="border-l border-cyan-900/40 bg-black/50 flex flex-col min-h-[500px] xl:h-[calc(100vh-60px)]">
          <div className="p-4 border-b border-cyan-900/40"><h2 className="text-cyan-400 tracking-[.2em] text-xs">COMMUNICATIONS</h2><p className="text-slate-500 text-[11px] mt-2">Conversation stays in this window while it is open. Ollama runs locally.</p></div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[280px]" aria-live="polite">{!messages.length && <div className="text-slate-400 text-xs leading-6">Hello, {userName}. Ask me a question, plan your day, or talk through a task. I’ll use Qwen through your local Ollama installation.</div>}{messages.map((m,i) => <div key={i} className={`border-l-2 pl-3 text-xs leading-5 whitespace-pre-wrap break-words ${m.role === "user" ? "border-emerald-500 text-emerald-200" : "border-cyan-500 text-cyan-100"}`}><div className="text-[9px] tracking-widest text-slate-500 mb-1">{m.role === "user" ? "YOU" : "JARVIS"}</div>{m.content}</div>)}{busy && <div className="text-cyan-500 text-xs animate-pulse">JARVIS is thinking…</div>}<div ref={chatEnd}/></div>
          <div className="p-4 border-t border-cyan-900/40 space-y-2 bg-black/35">{error && <div className="text-amber-400 text-[11px]" role="alert">{error}</div>}<div className="flex gap-2"><div className="flex-1 hud-input flex items-center gap-3"><span className={isListening ? "text-cyan-300 animate-pulse" : "text-slate-500"}>◉</span><input className="bg-transparent border-0 outline-none flex-1 min-w-0 text-cyan-100" aria-label="Message JARVIS" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} placeholder={isListening ? 'Always listening — say “Jarvis”...' : 'Ask JARVIS…'}/></div><span className={`hud-button ${isListening ? "text-cyan-200 border-cyan-400" : "text-slate-500"}`} aria-label="Local microphone status">{isListening ? "● LISTENING" : "MIC STANDBY"}</span><button onClick={() => send()} disabled={busy || !input.trim()} className="hud-button disabled:opacity-40">SEND</button></div><div className="text-[10px] text-cyan-700">{isListening ? "ALWAYS LISTENING • WAKE WORD: JARVIS • LOCAL WHISPER" : "LOCAL VOICE COMPANION STARTING"}</div></div>
        </aside>
      </div>
    </div>
  );
}
