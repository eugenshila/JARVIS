"""
JARVIS Desktop — Iron Man HUD that stays open + Hybrid Online/Offline

Fixes old starter app.py that disappeared. This version:
- Stays open, no console close
- Iron Man HUD styling #020208 + cyan/green
- Good Morning Eugene + 3 MITs + task alignment
- Hybrid mode: online full stack (openai/ollama) vs offline basic (mock)
- Online indicator: 🌐 ONLINE <engine> <latency>ms vs 📴 OFFLINE BASIC
- 6 modes: HUD, ADHD, Body Double, Arc 3D, Iron Man Classic, Chat
- Threaded agent calls (no UI block)
- Autostart toggle
- Personalization: name entry
- Lab systems + ADHD stats
- Mock works offline, real engines if configured

Run: python app.py
Build: pyinstaller --windowed --icon assets/icon.ico app.py

For i5-6300U 8GB:
- Online: openai best (no RAM) or ollama tinyllama
- Offline: mock basic or ollama tinyllama offline
"""

import sys
import os
import threading
import traceback
import logging
from pathlib import Path
from datetime import datetime

# Setup logging to file to debug disappearing issue
try:
    log_dir = Path.home() / ".jarvis"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "jarvis.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("JARVIS Desktop starting - SHILATECH v0.1.9.4 - logging to %s", log_file)
except Exception as e:
    print(f"Logging setup failed: {e}")
    logging = None


ROOT = Path(__file__).parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

def get_home():
    try:
        from jarvis.core.config import get_home as _get_home
        return _get_home()
    except:
        home = Path.home() / ".jarvis"
        home.mkdir(exist_ok=True)
        return home

def try_imports():
    try:
        from jarvis.core.config import JarvisConfig
        from jarvis.agents.registry import get_agent, list_agents
        from jarvis.engine.registry import list_engines
        from jarvis.core.types import EngineType
        from jarvis.tools.registry import list_tools
        from jarvis.core.network import get_auto_status
        return True, (JarvisConfig, get_agent, list_agents, list_engines, EngineType, list_tools, get_auto_status)
    except Exception as e:
        return False, str(e)

HAS_JARVIS, IMPORTS = try_imports()

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    HAS_TK = True
except ImportError:
    HAS_TK = False
    print("Tkinter not available. On Windows reinstall Python with tcl/tk. On Linux: sudo apt install python3-tk")
    sys.exit(1)


class IronManHUDApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("J.A.R.V.I.S — MARK XLII — SHILATECH — Personal AI — Hybrid Online/Offline — Voice — Stays Open")
        self.geometry("1250x780")
        self.minsize(1000, 600)
        self.configure(bg="#020208")
        # Prevent disappearing: handle close button, keep window alive
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._is_closing = False
        self._keep_alive_id = None
        # Log uncaught exceptions
        def log_excepthook(exc_type, exc_value, exc_traceback):
            err = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            try:
                if logging:
                    logging.error("Uncaught exception: %s", err)
                print(f"Uncaught exception: {err}")
            except:
                pass
            try:
                messagebox.showerror("JARVIS Error - But Staying Open", f"Error occurred but JARVIS stays open, Sir:\n{exc_value}\n\nSee ~/.jarvis/jarvis.log\n\n{err[:500]}")
            except:
                pass
        sys.excepthook = log_excepthook

        self.user_name = self.load_name()
        self.mits = self.load_mits()
        self.tasks = self.load_tasks()
        self.online_status = {"online": True, "engine": "auto", "mode": "CHECKING", "latency": None}

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except:
            pass
        style.configure("TButton", padding=6, font=("JetBrains Mono", 9))

        # Top HUD bar
        top = tk.Frame(self, bg="#020208", padx=16, pady=10, highlightbackground="#22c55e", highlightthickness=1)
        top.pack(fill="x")

        left_top = tk.Frame(top, bg="#020208")
        left_top.pack(side="left")
        tk.Label(left_top, text="J.A.R.V.I.S", bg="#020208", fg="#22c55e", font=("JetBrains Mono", 16, "bold")).pack(side="left")
        tk.Label(left_top, text=" MARK XLII", bg="#020208", fg="#22c55e", font=("JetBrains Mono", 9), borderwidth=1, relief="solid", padx=4).pack(side="left", padx=8)
        self.time_label = tk.Label(left_top, text=datetime.now().strftime("%H:%M:%S %Y-%m-%d"), bg="#020208", fg="#94a3b8", font=("JetBrains Mono", 9))
        self.time_label.pack(side="left", padx=12)

        # Online indicator
        self.online_frame = tk.Frame(left_top, bg="#020208")
        self.online_frame.pack(side="left", padx=12)
        self.online_dot = tk.Label(self.online_frame, text="●", bg="#020208", fg="#22c55e", font=("JetBrains Mono", 12))
        self.online_dot.pack(side="left")
        self.online_label = tk.Label(self.online_frame, text="CHECKING...", bg="#020208", fg="#22c55e", font=("JetBrains Mono", 9))
        self.online_label.pack(side="left", padx=4)

        right_top = tk.Frame(top, bg="#020208")
        right_top.pack(side="right")

        self.mode_var = tk.StringVar(value="HUD")
        modes = ["HUD", "ADHD", "BODY DOUBLE", "ARC 3D", "IRON MAN", "CHAT"]
        for m in modes:
            btn = tk.Button(right_top, text=m, command=lambda mm=m: self.switch_mode(mm),
                            bg="#020208", fg="#22c55e" if m=="HUD" else "#94a3b8",
                            font=("JetBrains Mono", 8), borderwidth=1, relief="solid",
                            padx=8, pady=4, activebackground="#22c55e", activeforeground="#020208")
            btn.pack(side="left", padx=2)

        tk.Button(right_top, text="AUTOSTART", command=self.toggle_autostart,
                  bg="#020208", fg="#f59e0b", font=("JetBrains Mono", 8), borderwidth=1, relief="solid",
                  padx=8, pady=4).pack(side="left", padx=6)

        tk.Label(right_top, text=f"USER: {self.user_name.upper()}", bg="#020208", fg="#22c55e",
                 font=("JetBrains Mono", 8)).pack(side="left", padx=8)

        # Main 3 columns
        main = tk.Frame(self, bg="#020208")
        main.pack(fill="both", expand=True, padx=8, pady=8)

        # Left
        left = tk.Frame(main, bg="#020208", width=280, highlightbackground="#22c55e", highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0,4))
        left.pack_propagate(False)

        arc_frame = tk.Frame(left, bg="#020208", padx=8, pady=8, highlightbackground="#22c55e", highlightthickness=1)
        arc_frame.pack(fill="x", padx=6, pady=6)
        tk.Label(arc_frame, text="ARC REACTOR • STABLE", bg="#020208", fg="#22c55e", font=("JetBrains Mono", 9)).pack()
        self.arc_label = tk.Label(arc_frame, text="◉ 97.3%", bg="#020208", fg="#22c55e", font=("JetBrains Mono", 20, "bold"))
        self.arc_label.pack()
        tk.Label(arc_frame, text="OUTPUT: 3.2 GJ/s • TEMP: 284K", bg="#020208", fg="#64748b", font=("JetBrains Mono", 7)).pack()
        self.hybrid_label = tk.Label(arc_frame, text="HYBRID: CHECKING...", bg="#020208", fg="#22d3ee", font=("JetBrains Mono", 7))
        self.hybrid_label.pack()

        mit_frame = tk.Frame(left, bg="#020208", padx=8, pady=8, highlightbackground="#22c55e", highlightthickness=1)
        mit_frame.pack(fill="x", padx=6, pady=4)
        tk.Label(mit_frame, text="TODAY'S ALIGNMENT • 3 MITS • LIVE", bg="#020208", fg="#22c55e", font=("JetBrains Mono", 9)).pack(anchor="w")
        self.mit_list = tk.Listbox(mit_frame, bg="#0a0a0f", fg="#86efac", font=("JetBrains Mono", 9), height=5,
                                   borderwidth=1, highlightthickness=0, selectbackground="#22c55e", selectforeground="#020208")
        self.mit_list.pack(fill="x", pady=4)
        for mit in self.mits:
            self.mit_list.insert("end", f"• {mit}")

        mit_entry_frame = tk.Frame(mit_frame, bg="#020208")
        mit_entry_frame.pack(fill="x", pady=2)
        self.mit_entry = tk.Entry(mit_entry_frame, bg="#0a0a0f", fg="#86efac", font=("JetBrains Mono", 9), insertbackground="#22c55e")
        self.mit_entry.pack(side="left", fill="x", expand=True, padx=(0,4))
        self.mit_entry.bind("<Return>", lambda e: self.add_mit())
        tk.Button(mit_entry_frame, text="ADD", command=self.add_mit, bg="#020208", fg="#22c55e", font=("JetBrains Mono", 8), borderwidth=1, relief="solid", padx=6).pack(side="right")

        tk.Button(mit_frame, text="RE-ALIGN DAY", command=lambda: self.send_prompt(f"plan my day MITs: {', '.join(self.mits)}"),
                  bg="#22c55e", fg="#020208", font=("JetBrains Mono", 8, "bold"), borderwidth=0, padx=8, pady=4).pack(fill="x", pady=4)

        sys_frame = tk.Frame(left, bg="#020208", padx=8, pady=8, highlightbackground="#22d3ee", highlightthickness=1)
        sys_frame.pack(fill="x", padx=6, pady=4)
        tk.Label(sys_frame, text="SYSTEM DIAGNOSTICS", bg="#020208", fg="#22d3ee", font=("JetBrains Mono", 9)).pack(anchor="w")
        for label in ["NEURAL NET 12%", "MEMORY CORE 34%", "COMMS ARRAY 89%", "SECURITY 100%", "ARC 97.3% STABLE"]:
            tk.Label(sys_frame, text=f"• {label}", bg="#020208", fg="#94a3b8", font=("JetBrains Mono", 8), anchor="w").pack(fill="x")

        qp_frame = tk.Frame(left, bg="#020208", padx=8, pady=8, highlightbackground="#a78bfa", highlightthickness=1)
        qp_frame.pack(fill="x", padx=6, pady=4)
        tk.Label(qp_frame, text="QUICK PROTOCOLS", bg="#020208", fg="#a78bfa", font=("JetBrains Mono", 9)).pack(anchor="w")
        qp_grid = tk.Frame(qp_frame, bg="#020208")
        qp_grid.pack(fill="x", pady=4)
        protocols = [
            ("BRAIN DUMP", "brain dump "),
            ("BREAK DOWN", "break down "),
            ("FOCUS 25M", "focus on "),
            ("ENERGY CHK", "energy check"),
            ("LOG WIN", "log win "),
            ("OVERWHELM", "overwhelm"),
            ("ONLINE", "network_status status"),
            ("GOOD MORNING", f"Good morning {self.user_name}"),
        ]
        for i, (label, cmd) in enumerate(protocols):
            r, c = divmod(i, 2)
            tk.Button(qp_grid, text=label, command=lambda cc=cmd: self.quick_protocol(cc),
                      bg="#020208", fg="#a78bfa", font=("JetBrains Mono", 7), borderwidth=1, relief="solid",
                      padx=4, pady=3).grid(row=r, column=c, padx=2, pady=2, sticky="ew")
        qp_grid.columnconfigure(0, weight=1)
        qp_grid.columnconfigure(1, weight=1)

        tk.Label(left, text="JARVIS v0.1.9 • Hybrid Online/Offline\nLocal-first • Auto Engine • Voice ready\nSHILATECH • Malibu Point 10880",
                 bg="#020208", fg="#475569", font=("JetBrains Mono", 7), justify="left").pack(side="bottom", padx=6, pady=6, anchor="w")

        # Center
        center = tk.Frame(main, bg="#020208", highlightbackground="#22c55e", highlightthickness=1)
        center.pack(side="left", fill="both", expand=True, padx=4)

        center_top = tk.Frame(center, bg="#020208", padx=8, pady=6, highlightbackground="#22c55e", highlightthickness=1)
        center_top.pack(fill="x")
        self.center_status = tk.Label(center_top, text="MAIN HUD • INTERACTIVE • VOICE: ○ STANDBY • HYBRID: CHECKING", bg="#020208", fg="#22c55e", font=("JetBrains Mono", 9))
        self.center_status.pack(side="left")
        tk.Label(center_top, text=f"ENCRYPTED • MARK XLII • {self.user_name.upper()}", bg="#020208", fg="#64748b", font=("JetBrains Mono", 7)).pack(side="right")

        chat_frame = tk.Frame(center, bg="#020208")
        chat_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.chat_box = tk.Text(chat_frame, bg="#0a0a0f", fg="#22d3ee", font=("JetBrains Mono", 10),
                                wrap="word", borderwidth=0, highlightthickness=0,
                                padx=12, pady=12, state="disabled")
        self.chat_box.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(chat_frame, command=self.chat_box.yview, bg="#020208", troughcolor="#020208")
        scrollbar.pack(side="right", fill="y")
        self.chat_box.config(yscrollcommand=scrollbar.set)

        input_frame = tk.Frame(center, bg="#020208", padx=8, pady=8, highlightbackground="#22c55e", highlightthickness=1)
        input_frame.pack(fill="x", padx=6, pady=6)

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(input_frame, textvariable=self.input_var, bg="#0a0a0f", fg="#86efac",
                                    font=("JetBrains Mono", 10), insertbackground="#22c55e", borderwidth=1, relief="solid")
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0,6))
        self.input_entry.bind("<Return>", lambda e: self.send_prompt())
        self.input_entry.focus_set()

        tk.Button(input_frame, text="TRANSMIT", command=self.send_prompt,
                  bg="#22c55e", fg="#020208", font=("JetBrains Mono", 9, "bold"), borderwidth=0, padx=12, pady=6).pack(side="left", padx=2)

        tk.Button(input_frame, text="🎤", command=self.voice_input,
                  bg="#020208", fg="#22c55e", font=("JetBrains Mono", 10), borderwidth=1, relief="solid", padx=8, pady=4).pack(side="left", padx=2)

        # Right
        right = tk.Frame(main, bg="#020208", width=300, highlightbackground="#22c55e", highlightthickness=1)
        right.pack(side="right", fill="y", padx=(4,0))
        right.pack_propagate(False)

        # Hybrid status panel
        hybrid_frame = tk.Frame(right, bg="#020208", padx=8, pady=8, highlightbackground="#f59e0b", highlightthickness=1)
        hybrid_frame.pack(fill="x", padx=6, pady=6)
        tk.Label(hybrid_frame, text="HYBRID MODE • ONLINE/OFFLINE", bg="#020208", fg="#f59e0b", font=("JetBrains Mono", 9)).pack(anchor="w")
        self.hybrid_detail = tk.Label(hybrid_frame, text="Checking...", bg="#020208", fg="#e2e8f0", font=("JetBrains Mono", 8), justify="left", anchor="w")
        self.hybrid_detail.pack(fill="x", pady=4)
        tk.Button(hybrid_frame, text="CHECK ONLINE", command=self.check_online, bg="#020208", fg="#f59e0b", font=("JetBrains Mono", 8), borderwidth=1, relief="solid", padx=6, pady=2).pack(fill="x", pady=2)
        tk.Button(hybrid_frame, text="SET ONLINE=OPENAI OFFLINE=MOCK", command=lambda: self.set_hybrid("openai", "mock"), bg="#020208", fg="#22c55e", font=("JetBrains Mono", 7), borderwidth=1, relief="solid").pack(fill="x", pady=1)
        tk.Button(hybrid_frame, text="SET ONLINE=OLLAMA OFFLINE=OLLAMA", command=lambda: self.set_hybrid("ollama", "ollama"), bg="#020208", fg="#22d3ee", font=("JetBrains Mono", 7), borderwidth=1, relief="solid").pack(fill="x", pady=1)
        tk.Label(hybrid_frame, text="When online, JARVIS stays interactive — you decide:", bg="#020208", fg="#94a3b8", font=("JetBrains Mono", 7)).pack(anchor="w", pady=(6,2))
        tk.Button(hybrid_frame, text="1. FULL STACK ONLINE", command=lambda: self.decide_mode("1"), bg="#022c22", fg="#22c55e", font=("JetBrains Mono", 8, "bold"), borderwidth=1, relief="solid").pack(fill="x", pady=1)
        tk.Button(hybrid_frame, text="2. BASIC OFFLINE LOCAL EVEN ONLINE", command=lambda: self.decide_mode("2"), bg="#422006", fg="#f59e0b", font=("JetBrains Mono", 7, "bold"), borderwidth=1, relief="solid").pack(fill="x", pady=1)

        task_frame = tk.Frame(right, bg="#020208", padx=8, pady=8, highlightbackground="#22c55e", highlightthickness=1)
        task_frame.pack(fill="x", padx=6, pady=6)
        tk.Label(task_frame, text=f"TASK MATRIX • TODAY • {datetime.now().date()}", bg="#020208", fg="#22c55e", font=("JetBrains Mono", 8)).pack(anchor="w")
        self.task_list = tk.Listbox(task_frame, bg="#0a0a0f", fg="#86efac", font=("JetBrains Mono", 9), height=6, borderwidth=1, highlightthickness=0)
        self.task_list.pack(fill="x", pady=4)
        for t in self.tasks:
            self.task_list.insert("end", f"✓ {t}")

        task_entry_frame = tk.Frame(task_frame, bg="#020208")
        task_entry_frame.pack(fill="x", pady=2)
        self.task_entry = tk.Entry(task_entry_frame, bg="#0a0a0f", fg="#86efac", font=("JetBrains Mono", 8), insertbackground="#22c55e")
        self.task_entry.pack(side="left", fill="x", expand=True, padx=(0,4))
        self.task_entry.bind("<Return>", lambda e: self.add_task())
        tk.Button(task_entry_frame, text="ADD", command=self.add_task, bg="#020208", fg="#22c55e", font=("JetBrains Mono", 7), borderwidth=1, relief="solid", padx=4).pack(side="right")

        lab_frame = tk.Frame(right, bg="#020208", padx=8, pady=8, highlightbackground="#22d3ee", highlightthickness=1)
        lab_frame.pack(fill="x", padx=6, pady=4)
        tk.Label(lab_frame, text="LAB SYSTEMS", bg="#020208", fg="#22d3ee", font=("JetBrains Mono", 9)).pack(anchor="w")
        for lab in ["💡 LAB LIGHTS ON • 80% • BLUE", "🎵 AUDIO PLAYING • LO-FI", "🔋 ARC 97.3% • STABLE", "🛡️ SECURITY PERIMETER SECURE", "💾 MEMORY FAISS • 342 VECS", "🧠 FOCUS READY • BODY DOUBLE", "🌐 HYBRID AUTO • ONLINE/OFFLINE"]:
            tk.Label(lab_frame, text=lab, bg="#020208", fg="#94a3b8", font=("JetBrains Mono", 8), anchor="w").pack(fill="x")

        adhd_frame = tk.Frame(right, bg="#020208", padx=8, pady=8, highlightbackground="#a78bfa", highlightthickness=1)
        adhd_frame.pack(fill="x", padx=6, pady=4)
        tk.Label(adhd_frame, text="ADHD CO-PILOT • TODAY", bg="#020208", fg="#a78bfa", font=("JetBrains Mono", 9)).pack(anchor="w")
        stats_grid = tk.Frame(adhd_frame, bg="#020208")
        stats_grid.pack(fill="x", pady=4)
        stats = [("TASKS", str(len(self.tasks) or len(self.mits))), ("MITS MAX", "3"), ("FOCUS", "25M"), ("WINS", "∞")]
        for i, (label, val) in enumerate(stats):
            r, c = divmod(i, 2)
            cell = tk.Frame(stats_grid, bg="#0a0a0f", padx=6, pady=6, highlightbackground="#a78bfa", highlightthickness=1)
            cell.grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            tk.Label(cell, text=val, bg="#0a0a0f", fg="#a78bfa", font=("JetBrains Mono", 14, "bold")).pack()
            tk.Label(cell, text=label, bg="#0a0a0f", fg="#64748b", font=("JetBrains Mono", 7)).pack()
        stats_grid.columnconfigure(0, weight=1)
        stats_grid.columnconfigure(1, weight=1)

        pers_frame = tk.Frame(right, bg="#020208", padx=8, pady=8, highlightbackground="#22c55e", highlightthickness=1)
        pers_frame.pack(fill="x", padx=6, pady=4)
        tk.Label(pers_frame, text="PERSONALIZATION", bg="#020208", fg="#64748b", font=("JetBrains Mono", 8)).pack(anchor="w")
        name_frame = tk.Frame(pers_frame, bg="#020208")
        name_frame.pack(fill="x", pady=4)
        tk.Label(name_frame, text="Name:", bg="#020208", fg="#94a3b8", font=("JetBrains Mono", 8)).pack(side="left")
        self.name_entry = tk.Entry(name_frame, bg="#0a0a0f", fg="#86efac", font=("JetBrains Mono", 9), width=12)
        self.name_entry.insert(0, self.user_name)
        self.name_entry.pack(side="left", padx=4)
        tk.Button(name_frame, text="SET", command=self.save_name, bg="#020208", fg="#22c55e", font=("JetBrains Mono", 7), borderwidth=1, relief="solid", padx=4).pack(side="left")
        tk.Label(pers_frame, text=f"Name used: Good morning {self.user_name}", bg="#020208", fg="#475569", font=("JetBrains Mono", 7)).pack(anchor="w")

        self.status_var = tk.StringVar(value="Ready — Hybrid Online/Offline — Checking network — SHILATECH")
        status_bar = tk.Label(self, textvariable=self.status_var, bg="#020208", fg="#22c55e", font=("JetBrains Mono", 8),
                              anchor="w", padx=12, pady=4, highlightbackground="#22c55e", highlightthickness=1)
        status_bar.pack(fill="x", side="bottom")

        self.update_clock()
        self.after(500, self.good_morning)
        self.after(1000, self.check_online)
        self.after(60000, self.keep_alive)  # Keep-alive prevents disappearing

    def load_name(self):
        try:
            home = get_home()
            name_file = home / "user_name.txt"
            if name_file.exists():
                return name_file.read_text().strip() or "Eugene"
        except:
            pass
        return "Eugene"

    def save_name(self):
        name = self.name_entry.get().strip() or "Eugene"
        self.user_name = name
        try:
            home = get_home()
            (home / "user_name.txt").write_text(name)
        except:
            pass
        self.status_var.set(f"Name set to {name} — Good morning {name}")
        self.add_message("assistant", f"Name updated to {name}, Sir. Good morning {name}.")

    def load_mits(self):
        try:
            home = get_home()
            mits_file = home / "adhd" / "plans.json"
            if mits_file.exists():
                import json
                data = json.loads(mits_file.read_text())
                if data and isinstance(data, list) and len(data) > 0:
                    last = data[-1]
                    if isinstance(last, dict) and "mits" in last:
                        return last["mits"][:3]
        except:
            pass
        return ["Q4 Planning Brief", "Client Email Response", "Lab Diagnostics"]

    def load_tasks(self):
        try:
            home = get_home()
            tasks_file = home / "adhd" / "quick_capture.json"
            if tasks_file.exists():
                import json
                data = json.loads(tasks_file.read_text())
                if isinstance(data, list):
                    return [d.get("text", str(d)) for d in data[-5:]]
        except:
            pass
        return []

    def add_mit(self):
        text = self.mit_entry.get().strip()
        if not text:
            return
        self.mits.append(text)
        self.mits = self.mits[-3:]
        self.mit_list.delete(0, "end")
        for mit in self.mits:
            self.mit_list.insert("end", f"• {mit}")
        self.mit_entry.delete(0, "end")
        self.status_var.set(f"MIT added: {text}")

    def add_task(self):
        text = self.task_entry.get().strip()
        if not text:
            return
        self.tasks.append(text)
        self.task_list.insert("end", f"✓ {text}")
        self.task_entry.delete(0, "end")
        self.status_var.set(f"Task added: {text}")

    def update_clock(self):
        try:
            if getattr(self, '_is_closing', False):
                return
            now = datetime.now()
            if hasattr(self, 'time_label') and self.time_label.winfo_exists():
                self.time_label.config(text=now.strftime("%H:%M:%S %Y-%m-%d"))
            import random
            power = 97 + random.uniform(-0.5, 0.8)
            if hasattr(self, 'arc_label') and self.arc_label.winfo_exists():
                self.arc_label.config(text=f"◉ {power:.1f}%")
            if 'logging' in globals() and logging:
                logging.debug("Clock tick %s", now)
        except Exception as e:
            try:
                if 'logging' in globals() and logging:
                    logging.error("update_clock failed: %s", e)
            except:
                pass
        finally:
            try:
                if not getattr(self, '_is_closing', False):
                    self.after(1000, self.update_clock)
            except:
                pass

    def on_close(self):
        try:
            if 'logging' in globals() and logging:
                logging.info("Close requested - user clicked X")
            result = messagebox.askyesnocancel(
                "JARVIS SHILATECH - Stay Open?",
                "JARVIS is about to close, Sir.\n\nYes = Quit\nNo = Minimize to taskbar (stays running)\nCancel = Stay open\n\nIf window disappears after a while, check ~/.jarvis/jarvis.log and docs/DISAPPEARING_FIX.md"
            )
            if result is None:
                if 'logging' in globals() and logging:
                    logging.info("Close cancelled - staying open")
                return
            elif result is False:
                if 'logging' in globals() and logging:
                    logging.info("Minimizing to taskbar, not closing")
                self.iconify()
                self.status_var.set("Minimized to taskbar — JARVIS still running, Sir. Click taskbar to restore.")
                return
            else:
                if 'logging' in globals() and logging:
                    logging.info("User confirmed quit")
                self._is_closing = True
                self.quit()
                self.destroy()
        except Exception as e:
            try:
                if 'logging' in globals() and logging:
                    logging.error("on_close failed: %s", e)
            except:
                pass

    def keep_alive(self):
        try:
            if getattr(self, '_is_closing', False):
                return
            if 'logging' in globals() and logging:
                logging.info("Keep-alive ping - JARVIS still running, Sir.")
            try:
                if not self.winfo_viewable():
                    if 'logging' in globals() and logging:
                        logging.warning("Window not viewable, deiconifying")
                    self.deiconify()
            except:
                pass
        except Exception as e:
            if 'logging' in globals() and logging:
                logging.error("keep_alive failed: %s", e)
        finally:
            try:
                if not getattr(self, '_is_closing', False):
                    self._keep_alive_id = self.after(60000, self.keep_alive)
            except:
                pass


    def decide_mode(self, choice):
        try:
            from jarvis.core.network import get_auto_status
            from jarvis.tools.network_tools import HybridModeTool
            status = get_auto_status()
            tool = HybridModeTool()
            if not status['network']['online']:
                self.add_message('assistant', f"Offline, Sir — already Basic Local. Nothing leaves device. SHILATECH secure. {status['selected']['engine']} {status['selected']['mode']}")
                return
            res = tool._run(action='decide', choice=choice)
            self.add_message('assistant', res[:500])
            if choice == '2':
                self.online_label.config(text='🌐 ONLINE • BASIC LOCAL • SHILATECH — you decided, Sir', fg='#f59e0b')
                self.status_var.set('Online but Basic Local even though online — private, SHILATECH secure — you decided, Sir')
            else:
                self.online_label.config(text=f"🌐 ONLINE {status['selected']['engine'].upper()} FULL STACK — you decided", fg='#22c55e')
                self.status_var.set('Online Full Stack — you decided, Sir — SHILATECH')
            self.check_online()
        except Exception as e:
            self.add_message('assistant', f"Decide failed: {e}")

    def check_online(self):
        def worker():
            try:
                if getattr(self, '_is_closing', False):
                    return
                if HAS_JARVIS:
                    JarvisConfig, get_agent, list_agents, list_engines, EngineType, list_tools, get_auto_status = IMPORTS
                    status = get_auto_status()
                    online = status["network"]["online"]
                    engine = status["selected"]["engine"]
                    mode = status["selected"]["mode"]
                    latency = status["network"].get("latency_ms")
                    reason = status["selected"]["reason"]

                    self.online_status = {"online": online, "engine": engine, "mode": mode, "latency": latency}

                    def update_ui():
                        if online:
                            self.online_dot.config(fg="#22c55e")
                            self.online_label.config(text=f"🌐 ONLINE {engine.upper()} {latency}ms" if latency else f"🌐 ONLINE {engine.upper()}", fg="#22c55e")
                            self.hybrid_label.config(text=f"HYBRID: {mode} — {engine}", fg="#22c55e")
                            self.center_status.config(text=f"MAIN HUD • {mode} • {engine.upper()} • VOICE: ○ STANDBY • {latency}ms" if latency else f"MAIN HUD • {mode} • {engine.upper()}")
                            self.hybrid_detail.config(text=f"Online: {engine}\nMode: {mode}\nLatency: {latency}ms\n{reason[:80]}...")
                            self.status_var.set(f"Ready — {mode} — {engine} — {latency}ms — Good morning {self.user_name}")
                        else:
                            self.online_dot.config(fg="#ef4444")
                            self.online_label.config(text="📴 OFFLINE BASIC", fg="#fca5a5")
                            self.hybrid_label.config(text=f"HYBRID: OFFLINE — {engine} BASIC", fg="#ef4444")
                            self.center_status.config(text=f"MAIN HUD • OFFLINE BASIC • {engine.upper()} • VOICE: ○ STANDBY")
                            self.hybrid_detail.config(text=f"Offline: {engine}\nMode: {mode}\n{reason[:80]}...")
                            self.status_var.set(f"Offline — {engine} basic — Mock + local — Go online for full stack")

                    self.after(0, update_ui)
                else:
                    self.after(0, lambda: self.online_label.config(text="MOCK — No JARVIS", fg="#94a3b8"))
            except Exception as e:
                self.after(0, lambda: self.status_var.set(f"Online check failed: {e}"))

        threading.Thread(target=worker, daemon=True).start()
        self.after(30000, self.check_online)  # recheck every 30 sec

    def set_hybrid(self, online_engine, offline_engine):
        try:
            if HAS_JARVIS:
                JarvisConfig, _, _, _, _, _, _ = IMPORTS
                cfg = JarvisConfig.load()
                cfg.auto.online_engine = online_engine
                cfg.auto.offline_engine = offline_engine
                cfg.save()
                self.add_message("assistant", f"Hybrid set: online={online_engine} offline={offline_engine}, Sir. Saved to ~/.jarvis/config.toml [auto]\n\nNow checking...")
                self.check_online()
            else:
                self.add_message("assistant", "Need JARVIS installed for hybrid config — pip install -e .")
        except Exception as e:
            self.add_message("assistant", f"Failed to set hybrid: {e}")

    def good_morning(self):
        hour = datetime.now().hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        date_str = datetime.now().strftime("%A, %B %d")
        time_str = datetime.now().strftime("%I:%M %p")
        mit_text = "\n".join([f"{i+1}. {m}" for i, m in enumerate(self.mits)])
        online_text = f"Hybrid: {self.online_status.get('mode','CHECKING')} via {self.online_status.get('engine','auto')} — Online full stack when online, basic when offline, Sir."

        msg = f"""{greeting}, {self.user_name}. It's {time_str} on {date_str}.

Arc reactor at 97.3% — kidding, Sir, we're at 100%. All systems nominal. Lab secure, perimeter clear.

{online_text}

Today's Alignment — 3 MITs to make today a win:
{mit_text}

Schedule: You have 3 meetings today, including Q4 planning at 2 PM. I've prepared a brief — shall I display it?

Energy: Based on your pattern, you're usually high focus 10-11am. Recommend tackling MIT 1 then.

What would you like to do first, Sir?

• Say "Show my tasks" for full list
• "Focus on Q4 brief" to start Pomodoro with body double
• "Brain dump" if mind feels full
• "network_status" to check hybrid online/offline
• "System diagnostics" for full report"""

        self.add_message("assistant", msg)

    def add_message(self, role, content):
        self.chat_box.config(state="normal")
        prefix = f"{self.user_name.upper()}" if role == "user" else "JARVIS"
        time_str = datetime.now().strftime("%H:%M")
        self.chat_box.insert("end", f"\n{prefix} • {time_str} • {'ENCRYPTED' if role=='assistant' else ''}\n", role)
        self.chat_box.insert("end", f"{content}\n", role + "_content")
        self.chat_box.insert("end", "\n" + "─"*60 + "\n", "sep")
        self.chat_box.tag_config("user", foreground="#86efac", font=("JetBrains Mono", 9, "bold"))
        self.chat_box.tag_config("assistant", foreground="#22d3ee", font=("JetBrains Mono", 9, "bold"))
        self.chat_box.tag_config("user_content", foreground="#86efac", font=("JetBrains Mono", 10))
        self.chat_box.tag_config("assistant_content", foreground="#e2e8f0", font=("JetBrains Mono", 10))
        self.chat_box.tag_config("sep", foreground="#1e293b", font=("JetBrains Mono", 8))
        self.chat_box.config(state="disabled")
        self.chat_box.see("end")

    def send_prompt(self, preset=None):
        prompt = preset or self.input_var.get().strip()
        if not prompt:
            return
        if not preset:
            self.input_var.set("")
        self.add_message("user", prompt)
        self.status_var.set(f"JARVIS processing: {prompt[:40]}...")

        def worker():
            try:
                if HAS_JARVIS:
                    JarvisConfig, get_agent, list_agents, list_engines, EngineType, list_tools, get_auto_status = IMPORTS
                    cfg = JarvisConfig.load()
                    # Use auto engine if hybrid enabled
                    if cfg.auto.enabled:
                        cfg.engine.type = EngineType.AUTO
                    lower = prompt.lower()
                    is_adhd = any(k in lower for k in ["brain dump", "break down", "focus on", "mit", "overwhelm", "energy", "win", "plan my day"])
                    agent_name = "adhd_coach" if is_adhd else "ironman"
                    agent = get_agent(agent_name, config=cfg)
                    resp = agent.run(prompt, context="")
                    self.after(0, lambda: self.add_message("assistant", resp.content))
                    self.after(0, lambda: self.status_var.set(f"Ready — {agent_name} — {len(list_tools())} tools — {self.online_status.get('mode','')}"))
                else:
                    mock_resp = f"""Mock response for: {prompt}

Good morning {self.user_name}, Sir. Mock engine offline, but I'm here. Hybrid: {self.online_status.get('mode','CHECKING')}.

Today's Alignment:
{chr(10).join([f'{i+1}. {m}' for i, m in enumerate(self.mits)])}

System: All nominal. Arc reactor 97.3%. Lab secure.

(Install JARVIS: pip install -e .[all] for real AI)"""
                    self.after(0, lambda: self.add_message("assistant", mock_resp))
                    self.after(0, lambda: self.status_var.set("Ready — Mock offline — pip install -e . for real AI"))
            except Exception as e:
                err = f"Error, Sir. Systems glitching: {e}\n\n{traceback.format_exc()[:500]}"
                self.after(0, lambda: self.add_message("assistant", err))
                self.after(0, lambda: self.status_var.set(f"Error: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def quick_protocol(self, cmd):
        if cmd.endswith(" "):
            self.input_var.set(cmd)
            self.input_entry.focus_set()
        else:
            self.send_prompt(cmd)

    def switch_mode(self, mode):
        self.status_var.set(f"Switched to {mode} mode — frontend has 6 modes, desktop is HUD mode")
        self.add_message("assistant", f"{mode} mode active, Sir. Hybrid: {self.online_status.get('mode','')} via {self.online_status.get('engine','')}.")

    def voice_input(self):
        self.status_var.set("Voice: Listening... (mock — type instead, or use frontend HUD for real mic)")
        self.add_message("assistant", f"Voice input — mock, Sir. In frontend HUD real mic works via Web Audio API + SpeechRecognition.\n\nClick 🎤 in HUD to speak: 'Good morning {self.user_name}'\n\nFor desktop real voice: pip install faster-whisper + kokoro")

    def toggle_autostart(self):
        try:
            if HAS_JARVIS:
                from jarvis.startup.autostart import AutostartManager
                mgr = AutostartManager()
                if mgr.is_enabled():
                    mgr.disable()
                    self.status_var.set("Autostart DISABLED — JARVIS won't start on boot")
                    messagebox.showinfo("Autostart", "Autostart disabled, Sir. JARVIS won't start on boot.")
                else:
                    mgr.enable(mode="ironman")
                    self.status_var.set("Autostart ENABLED — Good morning Eugene on boot")
                    messagebox.showinfo("Autostart", f"Autostart enabled, Sir. JARVIS will start on boot with Good Morning {self.user_name}.\n\nLocation: {mgr.get_location()}")
            else:
                self.status_var.set("Autostart: Need JARVIS installed — pip install -e .")
                messagebox.showinfo("Autostart", "Need JARVIS installed for autostart.\n\npip install -e .")
        except Exception as e:
            messagebox.showerror("Autostart Error", f"Failed: {e}\n\n{traceback.format_exc()[:500]}")


def main():
    try:
        app = IronManHUDApp()
        app.update_idletasks()
        w = app.winfo_width()
        h = app.winfo_height()
        x = (app.winfo_screenwidth() // 2) - (w // 2)
        y = (app.winfo_screenheight() // 2) - (h // 2)
        app.geometry(f"{w}x{h}+{x}+{y}")
        app.mainloop()
    except Exception as e:
        print(f"Failed to start: {e}\n{traceback.format_exc()}")
        try:
            messagebox.showerror("JARVIS Error", f"Failed to start:\n{e}\n\n{traceback.format_exc()[:1000]}")
        except:
            pass
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
