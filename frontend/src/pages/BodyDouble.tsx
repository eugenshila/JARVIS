import { useEffect, useState, useRef } from "react";

// Body Double — virtual co-working for ADHD
// Like someone sitting next to you working too, you don't want to let them down
// Pomodoro + check-ins + distraction parking lot

export default function BodyDouble() {
  const [task, setTask] = useState("");
  const [timeLeft, setTimeLeft] = useState(25 * 60);
  const [isRunning, setIsRunning] = useState(false);
  const [wins, setWins] = useState<string[]>([]);
  const [distractions, setDistractions] = useState<string[]>([]);
  const [distractionInput, setDistractionInput] = useState("");
  const [checkIn, setCheckIn] = useState("");
  const [sessionCount, setSessionCount] = useState(0);
  const [bodyDoubleStatus, setBodyDoubleStatus] = useState("Ready — I'm here, working with you, Sir");
  const timerRef = useRef<number | null>(null);

  const statuses = [
    "Working on my tasks too — we got this",
    "Still here, still focused with you",
    "Good focus — I'm on my 2nd coffee",
    "You inspired me to start my MIT",
    "Not leaving — body double power",
    "Your focus helps me focus too",
  ];

  useEffect(() => {
    if (!isRunning) return;

    timerRef.current = window.setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          setIsRunning(false);
          setSessionCount((c) => c + 1);
          setBodyDoubleStatus("Session complete — great work, Sir! Break?");
          if (Notification.permission === "granted") {
            new Notification("Body Double — Session done!", { body: `Great focus on ${task || "your task"}, Sir` });
          }
          return 0;
        }
        // Check-in every 5 min
        if (prev % 300 === 0 && prev !== 25 * 60) {
          const elapsed = 25 * 60 - prev;
          const mins = Math.floor(elapsed / 60);
          setCheckIn(`Check-in ${mins} min — still with ${task || "task"}?`);
          setTimeout(() => setCheckIn(""), 8000);
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRunning, task]);

  useEffect(() => {
    if (Notification.permission === "default") {
      Notification.requestPermission();
    }
    // Random body double status updates
    const interval = setInterval(() => {
      if (isRunning) {
        setBodyDoubleStatus(statuses[Math.floor(Math.random() * statuses.length)]);
      }
    }, 15000);
    return () => clearInterval(interval);
  }, [isRunning]);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  const startSession = (minutes: number) => {
    setTimeLeft(minutes * 60);
    setIsRunning(true);
    setBodyDoubleStatus(`Focus ON — ${minutes} min on ${task || "your task"}, Sir — I'm here`);
  };

  const logWin = () => {
    if (!task) return;
    setWins((w) => [...w, `${new Date().toLocaleTimeString()} — ${task} — ${formatTime(timeLeft)} left — win!`]);
    setTask("");
  };

  const parkDistraction = () => {
    if (!distractionInput.trim()) return;
    setDistractions((d) => [...d, distractionInput]);
    setDistractionInput("");
  };

  const progress = ((25 * 60 - timeLeft) / (25 * 60)) * 100;

  return (
    <div className="min-h-screen bg-[#020208] text-cyan-100 p-4 flex flex-col items-center">
      {/* Header */}
      <div className="w-full max-w-4xl mb-6">
        <div className="flex items-center justify-between border-b border-cyan-900/30 pb-3">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center">
              <span className="text-black font-bold text-xs">BD</span>
            </div>
            <div>
              <div className="font-mono text-sm tracking-widest text-cyan-400">BODY DOUBLE — VIRTUAL CO-WORKING</div>
              <div className="font-mono text-[9px] text-slate-500 tracking-widest">ADHD FOCUS — YOU'RE NOT ALONE, SIR</div>
            </div>
          </div>
          <div className="text-right">
            <div className="font-mono text-[10px] text-slate-400">SESSIONS TODAY</div>
            <div className="font-mono text-lg text-emerald-400">{sessionCount}</div>
          </div>
        </div>
      </div>

      <div className="w-full max-w-4xl grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left — Timer + Task */}
        <div className="lg:col-span-2 space-y-4">
          {/* Body Double avatar */}
          <div className="rounded border border-cyan-900/30 bg-black/40 p-4">
            <div className="flex items-center gap-4">
              <div className="relative">
                <canvas
                  width={80}
                  height={80}
                  ref={(canvas) => {
                    if (!canvas) return;
                    const ctx = canvas.getContext("2d");
                    if (!ctx) return;
                    ctx.clearRect(0, 0, 80, 80);
                    // Simple arc reactor for body double presence
                    const cx = 40, cy = 40;
                    const pulse = Date.now() / 500;
                    ctx.beginPath();
                    ctx.arc(cx, cy, 30 + Math.sin(pulse) * 2, 0, Math.PI * 2);
                    ctx.fillStyle = isRunning ? `rgba(6,182,212,${0.3 + Math.sin(pulse) * 0.1})` : `rgba(100,116,139,0.2)`;
                    ctx.fill();
                    ctx.strokeStyle = isRunning ? "#06b6d4" : "#475569";
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.arc(cx, cy, 30, 0, Math.PI * 2);
                    ctx.stroke();
                    ctx.fillStyle = isRunning ? "#22d3ee" : "#64748b";
                    ctx.beginPath();
                    ctx.arc(cx, cy, 12, 0, Math.PI * 2);
                    ctx.fill();
                    requestAnimationFrame(() => {
                      if (canvas) canvas.dispatchEvent(new Event("redraw"));
                    });
                  }}
                  className="rounded-full"
                />
                <div className={`absolute -bottom-1 -right-1 h-3 w-3 rounded-full ${isRunning ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`} />
              </div>
              <div className="flex-1">
                <div className="font-mono text-xs text-cyan-300">JARVIS — Body Double</div>
                <div className="font-mono text-[11px] text-slate-400 mt-1">{bodyDoubleStatus}</div>
                <div className="mt-2 flex items-center gap-2">
                  <div className={`h-1.5 w-1.5 rounded-full ${isRunning ? "bg-emerald-400 animate-ping" : "bg-slate-600"}`} />
                  <span className="font-mono text-[9px] text-slate-500">{isRunning ? "WORKING WITH YOU" : "STANDBY"}</span>
                </div>
              </div>
            </div>
            {checkIn && (
              <div className="mt-3 rounded bg-cyan-950/50 border border-cyan-800/50 p-2 font-mono text-xs text-cyan-300 animate-pulse">
                💬 {checkIn}
              </div>
            )}
          </div>

          {/* Timer */}
          <div className="rounded border border-cyan-900/30 bg-black/40 p-6 text-center">
            <div className="font-mono text-[10px] tracking-[0.3em] text-slate-500 mb-2">FOCUS TIMER</div>
            <div className="font-mono text-6xl tracking-widest text-cyan-400 mb-4">{formatTime(timeLeft)}</div>
            <div className="h-1 w-full rounded bg-black/50 mb-4">
              <div className="h-1 rounded bg-gradient-to-r from-cyan-400 to-emerald-400 transition-all" style={{ width: `${progress}%` }} />
            </div>

            <div className="flex gap-2 justify-center mb-4">
              <button
                onClick={() => startSession(15)}
                className="rounded border border-cyan-800/50 bg-black/50 px-3 py-1.5 font-mono text-xs text-cyan-400 hover:bg-cyan-950/50"
              >
                15 MIN
              </button>
              <button
                onClick={() => startSession(25)}
                className="rounded bg-cyan-600 px-4 py-1.5 font-mono text-xs text-black font-bold hover:bg-cyan-500"
              >
                25 MIN — FOCUS
              </button>
              <button
                onClick={() => startSession(45)}
                className="rounded border border-cyan-800/50 bg-black/50 px-3 py-1.5 font-mono text-xs text-cyan-400 hover:bg-cyan-950/50"
              >
                45 MIN — DEEP
              </button>
              <button
                onClick={() => startSession(5)}
                className="rounded border border-emerald-800/50 bg-black/50 px-3 py-1.5 font-mono text-xs text-emerald-400 hover:bg-emerald-950/50"
              >
                5 MIN — BREAK
              </button>
            </div>

            <div className="flex gap-2">
              <input
                value={task}
                onChange={(e) => setTask(e.target.value)}
                placeholder="What are you working on? (e.g. Q4 brief draft — 2 min version)"
                className="flex-1 rounded bg-black/60 border border-cyan-900/30 px-3 py-2 font-mono text-sm text-cyan-100 placeholder:text-slate-600 focus:outline-none focus:border-cyan-700"
              />
            </div>

            <div className="mt-3 flex gap-2 justify-center">
              <button
                onClick={() => setIsRunning(!isRunning)}
                className={`rounded px-6 py-2 font-mono text-xs font-bold ${isRunning ? "bg-red-900/50 text-red-400 border border-red-800/50" : "bg-emerald-600 text-black"}`}
              >
                {isRunning ? "⏸ PAUSE" : "▶ START — BODY DOUBLE ON"}
              </button>
              <button onClick={logWin} className="rounded border border-emerald-800/50 bg-black/50 px-4 py-2 font-mono text-xs text-emerald-400 hover:bg-emerald-950/30">
                ✅ LOG WIN
              </button>
              <button
                onClick={() => {
                  setTimeLeft(25 * 60);
                  setIsRunning(false);
                }}
                className="rounded border border-slate-700/50 bg-black/50 px-4 py-2 font-mono text-xs text-slate-400 hover:bg-slate-900/50"
              >
                RESET
              </button>
            </div>
          </div>

          {/* Distraction parking lot */}
          <div className="rounded border border-amber-900/30 bg-black/40 p-4">
            <div className="font-mono text-[10px] tracking-widest text-amber-400 mb-2">DISTRACTION PARKING LOT — PARK IT, DON'T CHASE</div>
            <div className="flex gap-2 mb-3">
              <input
                value={distractionInput}
                onChange={(e) => setDistractionInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && parkDistraction()}
                placeholder="Distracting thought? Park it here (e.g. check email, order coffee)"
                className="flex-1 rounded bg-black/60 border border-amber-900/30 px-3 py-1.5 font-mono text-xs text-amber-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-700"
              />
              <button onClick={parkDistraction} className="rounded bg-amber-900/30 border border-amber-800/50 px-3 py-1.5 font-mono text-xs text-amber-400 hover:bg-amber-900/50">
                PARK
              </button>
            </div>
            <div className="space-y-1 max-h-24 overflow-y-auto">
              {distractions.map((d, i) => (
                <div key={i} className="font-mono text-xs text-amber-300/70 flex items-center gap-2">
                  <span className="text-[8px]">🅿️</span> {d}
                </div>
              ))}
              {distractions.length === 0 && <div className="font-mono text-[10px] text-slate-600">No distractions parked — clean mind, Sir</div>}
            </div>
          </div>
        </div>

        {/* Right — Wins + Stats */}
        <div className="space-y-4">
          <div className="rounded border border-emerald-900/30 bg-black/40 p-4">
            <div className="font-mono text-[10px] tracking-widest text-emerald-400 mb-3">WINS — TODAY</div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {wins.map((w, i) => (
                <div key={i} className="font-mono text-[11px] text-emerald-300/80">
                  ✅ {w}
                </div>
              ))}
              {wins.length === 0 && <div className="font-mono text-[10px] text-slate-600">No wins yet — start focus to log first win, Sir</div>}
            </div>
            <div className="mt-3 font-mono text-[9px] text-slate-500">ADHD tip: Log every tiny win — 2 min counts, Sir</div>
          </div>

          <div className="rounded border border-cyan-900/30 bg-black/40 p-4">
            <div className="font-mono text-[10px] tracking-widest text-cyan-400 mb-2">BODY DOUBLE — HOW IT WORKS</div>
            <div className="font-mono text-[11px] text-slate-400 space-y-2 leading-relaxed">
              <div>• ADHD brain focuses better with someone nearby — even virtual</div>
              <div>• I'm here working too — you don't want to let me down, right?</div>
              <div>• Check-ins every 5 min: still with task?</div>
              <div>• Distraction parking lot: park thought, return to task</div>
              <div>• 25 min focus → 5 min break → repeat</div>
              <div>• Any progress is win — 2 min counts, Sir</div>
            </div>
          </div>

          <div className="rounded border border-slate-800/50 bg-black/40 p-3">
            <div className="font-mono text-[9px] text-slate-500">FOCUS STATS</div>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <div className="rounded bg-black/50 p-2 text-center">
                <div className="font-mono text-lg text-cyan-400">{Math.floor((25 * 60 - timeLeft) / 60)}m</div>
                <div className="font-mono text-[8px] text-slate-500">FOCUSED</div>
              </div>
              <div className="rounded bg-black/50 p-2 text-center">
                <div className="font-mono text-lg text-amber-400">{distractions.length}</div>
                <div className="font-mono text-[8px] text-slate-500">PARKED</div>
              </div>
              <div className="rounded bg-black/50 p-2 text-center">
                <div className="font-mono text-lg text-emerald-400">{wins.length}</div>
                <div className="font-mono text-[8px] text-slate-500">WINS</div>
              </div>
              <div className="rounded bg-black/50 p-2 text-center">
                <div className="font-mono text-lg text-slate-400">{sessionCount}</div>
                <div className="font-mono text-[8px] text-slate-500">SESSIONS</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
