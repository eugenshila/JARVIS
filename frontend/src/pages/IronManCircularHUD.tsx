import { useEffect, useRef, useState } from "react";

// Iron Man Circular HUD — matches Bing wallpaper screenshot
// Central large circular HUD with blue glow, outer rings, segments, left/right panels
// For both local and online starts — same UI, only ONLINE/OFFLINE badge changes

export default function IronManCircularHUD() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [time, setTime] = useState(new Date());
  const [arcPower, setArcPower] = useState(97.3);
  const [online, setOnline] = useState(navigator.onLine);
  const [engine, setEngine] = useState("auto");
  const [userName] = useState(localStorage.getItem("jarvis_user_name") || "Eugene");
  const [weather] = useState({ temp: "56°F", condition: "Partly Cloudy", high: "74°", low: "60°" });
  const [messages, setMessages] = useState<{role: string, content: string}[]>([]);
  const [input, setInput] = useState("");

  useEffect(() => {
    const id = setInterval(() => {
      setTime(new Date());
      setArcPower(p => 94 + Math.random() * 6);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const checkOnline = async () => {
      setOnline(navigator.onLine);
      try {
        const res = await fetch("/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: "network_status check", agent: "ironman", engine: "mock" }),
        });
        const data = await res.json();
        if (data.content) {
          if (data.content.includes("openai")) setEngine("openai");
          else if (data.content.includes("ollama")) setEngine("ollama");
          else setEngine("mock");
        }
      } catch {
        setEngine("mock");
      }
    };
    checkOnline();
    window.addEventListener("online", checkOnline);
    window.addEventListener("offline", checkOnline);
    const iid = setInterval(checkOnline, 30000);
    return () => {
      window.removeEventListener("online", checkOnline);
      window.removeEventListener("offline", checkOnline);
      clearInterval(iid);
    };
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

      // Middle segmented ring — like screenshot outer segments
      const midR = base - 35;
      for (let i = 0; i < 16; i++) {
        const angle = (i / 16) * Math.PI * 2 + rot * 0.3;
        const gap = 0.15;
        ctx.strokeStyle = `rgba(6, 182, 212, ${0.4 + Math.sin(rot + i) * 0.2})`;
        ctx.lineWidth = 8;
        ctx.beginPath();
        ctx.arc(cx, cy, midR, angle + gap, angle + Math.PI / 8 - gap);
        ctx.stroke();
      }

      // Inner blue glowing ring — main reactor ring
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

      // Center number 13 like screenshot
      ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
      ctx.beginPath();
      ctx.arc(cx, cy, 18, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#e2e8f0";
      ctx.font = "bold 14px JetBrains Mono";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("13", cx, cy);

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

  const send = async (text?: string) => {
    const prompt = text || input;
    if (!prompt.trim()) return;
    setMessages(m => [...m, { role: "user", content: prompt }]);
    setInput("");
    try {
      const res = await fetch("/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, agent: "ironman", engine: "auto" }),
      });
      const data = await res.json();
      setMessages(m => [...m, { role: "assistant", content: data.content || "Error, Sir." }]);
    } catch {
      setMessages(m => [...m, { role: "assistant", content: "Comms down, Sir. Running offline mock — always works." }]);
    }
  };

  return (
    <div className="h-screen w-screen bg-[#020208] text-cyan-100 overflow-hidden relative font-mono">
      {/* Background grid like screenshot */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: `linear-gradient(rgba(6,182,212,1) 1px, transparent 1px), linear-gradient(90deg, rgba(6,182,212,1) 1px, transparent 1px)`,
        backgroundSize: "40px 40px"
      }} />

      {/* Top bar — Chrome-like from screenshot */}
      <div className="relative z-10 flex items-center justify-between px-4 py-2 border-b border-cyan-900/30 bg-black/80 text-[11px]">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_10px_#22c55e]" />
            <span className="tracking-widest text-cyan-400 font-bold">J.A.R.V.I.S</span>
            <span className="border border-cyan-700 px-1.5 py-0.5 rounded text-[9px] text-cyan-600">MARK XLII</span>
          </div>
          <span className="text-slate-500">STARK INDUSTRIES • {time.toLocaleTimeString()} • {time.toLocaleDateString()}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-2 py-0.5 rounded border text-[10px] flex items-center gap-1.5 ${online ? "bg-emerald-950/50 border-emerald-700 text-emerald-400" : "bg-red-950/50 border-red-700 text-red-400"}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${online ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
            {online ? `ONLINE ${engine.toUpperCase()} • FULL STACK` : "OFFLINE • BASIC"}
          </span>
          <span className="text-slate-400">USER: {userName.toUpperCase()}</span>
          <span className="px-2 py-0.5 rounded bg-cyan-950/50 border border-cyan-800 text-cyan-400">ARC {arcPower.toFixed(1)}%</span>
        </div>
      </div>

      <div className="relative z-10 flex h-[calc(100vh-40px)]">
        {/* Left panel — like screenshot left */}
        <div className="w-[220px] border-r border-cyan-900/20 bg-black/40 p-3 flex flex-col gap-3 overflow-y-auto">
          <div className="border border-cyan-900/30 rounded bg-black/60 p-2">
            <div className="text-[10px] tracking-widest text-cyan-600 mb-2">SYSTEM • DEVICE SPECIFICATIONS</div>
            <div className="text-[11px] space-y-1.5 text-slate-300">
              <div className="flex justify-between"><span className="text-slate-500">Device</span><span>DESKTOP-3D8CN02</span></div>
              <div className="flex justify-between"><span className="text-slate-500">CPU</span><span className="text-[10px]">i5-6300U @ 2.40GHz</span></div>
              <div className="flex justify-between"><span className="text-slate-500">RAM</span><span>8.00 GB (7.41 usable)</span></div>
              <div className="flex justify-between"><span className="text-slate-500">System</span><span>64-bit x64</span></div>
              <div className="flex justify-between"><span className="text-slate-500">OS</span><span>Windows 11 Pro 21H2</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Engine</span><span className={online ? "text-emerald-400" : "text-amber-400"}>{engine.toUpperCase()} • {online ? "ONLINE" : "OFFLINE"}</span></div>
            </div>
          </div>

          <div className="border border-cyan-900/30 rounded bg-black/60 p-2">
            <div className="text-[10px] tracking-widest text-cyan-600 mb-2">TODAY'S ALIGNMENT • 3 MITS</div>
            <div className="space-y-2">
              {["Q4 Planning Brief", "Client Email Response", "Lab Diagnostics"].map((mit, i) => (
                <div key={i} className="flex gap-2 text-[11px] py-1 border-b border-cyan-900/10 last:border-0">
                  <div className="w-5 h-5 rounded-full border border-cyan-700 flex items-center justify-center text-[10px] flex-shrink-0">{i+1}</div>
                  <div className="text-slate-300">{mit}</div>
                </div>
              ))}
            </div>
            <div className="mt-2 text-[9px] text-slate-500">Good morning {userName}, Sir. 3 MITs to make today a win.</div>
          </div>

          <div className="border border-amber-900/20 rounded bg-black/60 p-2">
            <div className="text-[10px] tracking-widest text-amber-600 mb-2">SECURITY • DATA PROTECTION</div>
            <div className="text-[10px] space-y-1.5 text-slate-400 leading-relaxed">
              <div className="flex gap-1.5"><span className="text-emerald-400">🔒</span> Local-first, private by default</div>
              <div className="flex gap-1.5"><span className="text-emerald-400">📴</span> Offline: nothing leaves device</div>
              <div className="flex gap-1.5"><span className="text-cyan-400">🌐</span> Online: only prompt sent to OpenAI API if you set key</div>
              <div className="flex gap-1.5"><span className="text-cyan-400">🏠</span> Ollama local: LLM stays on device even online</div>
              <div className="flex gap-1.5"><span className="text-slate-500">🛡️</span> No telemetry, Apache 2.0, open source</div>
            </div>
          </div>

          <div className="mt-auto border border-cyan-900/10 rounded p-2 bg-black/30">
            <div className="text-[9px] text-slate-600 leading-relaxed">
              JARVIS v0.1.9 • Hybrid Online/Offline<br/>
              Local-first • Auto Engine • Voice ready<br/>
              Stark Industries • Malibu Point 10880<br/>
              <span className={online ? "text-emerald-500" : "text-amber-500"}>{online ? "🌐 ONLINE FULL STACK" : "📴 OFFLINE BASIC"} • SECURE</span>
            </div>
          </div>
        </div>

        {/* Center — Circular HUD like screenshot */}
        <div className="flex-1 flex flex-col items-center justify-center relative bg-[#020208]">
          {/* Circular HUD */}
          <div className="relative">
            <canvas ref={canvasRef} width={560} height={560} className="w-[560px] h-[560px]" />

            {/* Overlays like screenshot — left/right data around circle */}
            <div className="absolute top-[10%] left-[-80px] text-[10px] text-cyan-700 space-y-1">
              <div>99% - Strength</div>
              <div>Home WiFi - Source</div>
              <div className="mt-4 text-[9px] text-slate-600">Jarvis list</div>
              <div className="text-[8px] text-slate-700 space-y-0.5 mt-1">
                <div>• backup themes</div>
                <div>• backup control</div>
                <div>• warning control</div>
              </div>
            </div>

            <div className="absolute top-[15%] right-[-90px] text-[10px] text-slate-400 space-y-2">
              <div className="border border-cyan-900/20 p-2 rounded bg-black/60 w-[160px]">
                <div className="text-cyan-600 text-[9px] tracking-widest">WEATHER • NAIROBI</div>
                <div className="text-[20px] font-bold text-cyan-300 mt-1">{weather.temp}</div>
                <div className="text-[11px]">{weather.condition}</div>
                <div className="text-[9px] text-slate-500 mt-1">High {weather.high} • Low {weather.low}</div>
                <div className="text-[8px] text-slate-600 mt-2">Precipitation: 10% • Humidity: 65% • Wind: 5 mph</div>
              </div>

              <div className="border border-cyan-900/20 p-2 rounded bg-black/60 w-[160px]">
                <div className="text-cyan-600 text-[9px]">SYSTEM • {online ? "ONLINE" : "OFFLINE"}</div>
                <div className="text-[9px] space-y-1 mt-1">
                  <div className="flex justify-between"><span>Engine</span><span className={online ? "text-emerald-400" : "text-amber-400"}>{engine.toUpperCase()}</span></div>
                  <div className="flex justify-between"><span>Mode</span><span>{online ? "FULL STACK" : "BASIC"}</span></div>
                  <div className="flex justify-between"><span>Security</span><span className="text-emerald-400">🔒 SECURE</span></div>
                  <div className="flex justify-between"><span>Data</span><span className="text-emerald-400">{online ? "ENCRYPTED" : "LOCAL ONLY"}</span></div>
                </div>
              </div>
            </div>

            {/* Bottom info like screenshot */}
            <div className="absolute bottom-[-10px] left-1/2 -translate-x-1/2 flex gap-6 text-[9px] text-slate-500">
              <span>Trash - 44 items</span>
              <span>Size - 248.95 MB</span>
              <span>Source - AC Line</span>
              <span>Power - 90%</span>
              <span className={online ? "text-emerald-400" : "text-amber-400"}>{online ? "🌐 ONLINE" : "📴 OFFLINE"} • {engine.toUpperCase()}</span>
            </div>
          </div>

          {/* Chat under circle — like Iron Man interactive */}
          <div className="mt-8 w-[600px] max-w-[90%]">
            <div className="border border-cyan-900/30 rounded bg-black/60 backdrop-blur p-3">
              <div className="h-[120px] overflow-y-auto space-y-2 mb-2 text-[11px]">
                {messages.length === 0 && (
                  <div className="text-slate-500">
                    Good morning {userName}, Sir. It's {time.toLocaleTimeString()} on {time.toLocaleDateString([], { weekday: "long" })}.<br/>
                    Arc reactor at {arcPower.toFixed(1)}% — {online ? "Online full stack" : "Offline basic"} — {online ? "All systems nominal, data secure, encrypted channel" : "Local only, nothing leaves device, secure"}.
                    <br/><br/>
                    <span className={online ? "text-emerald-400" : "text-amber-400"}>{online ? "🌐 ONLINE MODE — Full stack" : "📴 OFFLINE MODE — Basic"} — Same interface, Sir. {online ? "Prompt sent to OpenAI API only if you set key, else Ollama local stays private." : "Nothing leaves device, offline mock."}</span>
                  </div>
                )}
                {messages.map((m, i) => (
                  <div key={i} className={m.role === "user" ? "text-emerald-300 text-right" : "text-cyan-300"}>
                    <span className="text-[9px] text-slate-500">{m.role.toUpperCase()} • </span>{m.content.slice(0, 200)}
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && send()}
                  placeholder={`Ask JARVIS... (Good morning ${userName}, network_status, hybrid_mode, brain dump...)`}
                  className="flex-1 bg-black/80 border border-cyan-900/30 rounded px-3 py-1.5 text-[11px] text-cyan-100 placeholder:text-slate-600 focus:outline-none focus:border-cyan-700"
                />
                <button onClick={() => send()} className="px-4 py-1.5 rounded bg-cyan-600 text-black text-[11px] font-bold hover:bg-cyan-500">TRANSMIT</button>
              </div>
            </div>
          </div>
        </div>

        {/* Right panel — related like screenshot */}
        <div className="w-[240px] border-l border-cyan-900/20 bg-black/40 p-3 flex flex-col gap-3 overflow-y-auto">
          <div className="text-[10px] tracking-widest text-slate-500">More images on this site</div>
          <div className="grid grid-cols-3 gap-1.5">
            {[1, 2, 3].map(i => (
              <div key={i} className="aspect-square rounded border border-cyan-900/20 bg-cyan-950/20 flex items-center justify-center">
                <div className="w-6 h-6 rounded-full border border-cyan-700 bg-cyan-900/30 animate-pulse" />
              </div>
            ))}
          </div>

          <div className="border border-cyan-900/20 rounded p-2 bg-black/60">
            <div className="text-[10px] tracking-widest text-slate-400 mb-2">Related searches</div>
            <div className="space-y-1.5">
              {[
                "Iron Man Jarvis PC Wallpaper",
                "Iron Man Jarvis Desktop Wallpaper",
                "Iron Man Jarvis Desktop Theme",
                "Iron Man Jarvis Wallpaper 4K",
              ].map((s, i) => (
                <button key={i} onClick={() => send(s)} className="w-full text-left text-[10px] px-2 py-1 rounded bg-black/40 border border-cyan-900/20 text-cyan-600 hover:bg-cyan-950/30 hover:text-cyan-400 flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-cyan-900/50 flex items-center justify-center text-[8px]">◉</span> {s}
                </button>
              ))}
            </div>
          </div>

          <div className="border border-emerald-900/20 rounded p-2 bg-emerald-950/10">
            <div className="text-[10px] tracking-widest text-emerald-600 mb-2">SECURITY • YOUR DATA</div>
            <div className="text-[10px] space-y-2 text-slate-300 leading-relaxed">
              <div>
                <div className="text-emerald-400 font-bold">📴 Offline Mode — Basic</div>
                <div className="text-[9px] text-slate-400">Nothing leaves device. Mock LLM + keyword memory + local calendar.json/email.json mock. 100% private, Sir. Always works.</div>
              </div>
              <div>
                <div className="text-cyan-400 font-bold">🌐 Online Mode — Full Stack</div>
                <div className="text-[9px] text-slate-400">Only prompt you type sent to OpenAI API if you set OPENAI_API_KEY. Or Ollama local — LLM stays on device even online, only search goes online if you use Tavily. Your choice, Sir.</div>
              </div>
              <div className="text-[9px] text-slate-500 border-t border-emerald-900/20 pt-2 mt-2">
                <div>🔒 Local-first, private by default</div>
                <div>🔒 No telemetry (disabled)</div>
                <div>🔒 API keys from env, not stored in config.toml</div>
                <div>🔒 Google OAuth token local ~/.jarvis/google_token.json</div>
                <div>🔒 FAISS memory local ~/.jarvis/memory</div>
                <div>🔒 Open source Apache 2.0</div>
                <div className="mt-1 text-emerald-400">Same circular interface online/offline, Sir. Only badge changes.</div>
              </div>
            </div>
          </div>

          <div className="border border-cyan-900/20 rounded p-2 bg-black/40">
            <div className="text-[9px] text-slate-500 tracking-widest">QUICK PROTOCOLS</div>
            <div className="grid grid-cols-2 gap-1 mt-2">
              {[
                ["ONLINE CHECK", "network_status status"],
                ["HYBRID MODE", "hybrid_mode status"],
                ["GOOD MORNING", `Good morning ${userName}`],
                ["BRAIN DUMP", "brain dump "],
                ["FOCUS 25M", "focus on "],
                ["SECURITY", "How is my data secure?"],
              ].map(([label, cmd]) => (
                <button key={label} onClick={() => (cmd.endsWith(" ") ? setInput(cmd) : send(cmd))} className="text-[8px] px-2 py-1 rounded bg-black/60 border border-cyan-900/20 text-cyan-700 hover:bg-cyan-950/40 hover:text-cyan-300">
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom bar like screenshot */}
      <div className="relative z-10 flex items-center justify-between px-4 py-1.5 border-t border-cyan-900/20 bg-black/80 text-[9px] text-slate-500">
        <div className="flex gap-4">
          <span>Jarvis Iron Man Wallpaper 4K</span>
          <span>Jarvis Iron Man Quotes</span>
          <span>Jarvis Iron Man Hologram</span>
        </div>
        <div className="flex gap-4">
          <span>Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90%</span>
          <span className={online ? "text-emerald-400" : "text-amber-400"}>{online ? "🌐 ONLINE SECURE • ENCRYPTED" : "📴 OFFLINE SECURE • LOCAL ONLY"}</span>
          <span>{time.toLocaleTimeString()} • {time.toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
}
