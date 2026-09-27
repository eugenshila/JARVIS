"""
JARVIS Desktop — Circular HUD like Bing screenshot — SHILATECH — Stays Open + Voice + Hybrid Interactive

Matches screenshot you sent: central blue ring 13, 72 ticks, 16 segments, weather 56°F, Trash 44 items Size 248.95 MB
Same interface local and online, only ONLINE/OFFLINE badge changes, you decide Full vs Basic when online.

Fixes disappearing: logging to ~/.jarvis/jarvis.log, keep-alive every 60s, WM_DELETE_WINDOW confirmation, robust after() callbacks.

Run: python app.py
"""

import sys
import os
import threading
import traceback
import logging
import math
import random
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Logging to debug disappearing + stays then disappears
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
    logging.info("JARVIS Circular HUD Desktop starting - SHILATECH v0.1.9.5 - logging to %s", log_file)
except Exception as e:
    print(f"Logging setup failed: {e}")
    logging = None

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
    from tkinter import messagebox
    HAS_TK = True
except ImportError:
    HAS_TK = False
    print("Tkinter not available. On Windows reinstall Python with tcl/tk. On Linux: sudo apt install python3-tk")
    sys.exit(1)


class CircularHUDApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("J.A.R.V.I.S — MARK XLII — SHILATECH — Personal AI — Hybrid Online/Offline — Voice — Circular HUD — Stays Open")
        self.geometry("1400x850")
        self.minsize(1200, 700)
        self.configure(bg="#020208")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._is_closing = False
        self._rot = 0
        self._arc_power = 97.3
        self._forced_mode = "auto"  # auto, full, basic

        def log_excepthook(exc_type, exc_value, exc_traceback):
            err = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            try:
                if logging:
                    logging.error("Uncaught exception: %s", err)
            except:
                pass
            try:
                messagebox.showerror("JARVIS Error - Staying Open", f"Error but staying open, Sir:\n{exc_value}\n\nSee ~/.jarvis/jarvis.log\n{err[:500]}")
            except:
                pass
        sys.excepthook = log_excepthook

        self.user_name = self.load_name()
        self.mits = self.load_mits()
        self.online_status = {"online": True, "engine": "auto", "mode": "CHECKING", "latency": None}

        # Top bar — Chrome-like from screenshot
        top = tk.Frame(self, bg="black", padx=8, pady=4, highlightbackground="#0e7490", highlightthickness=1)
        top.pack(fill="x")
        left_top = tk.Frame(top, bg="black")
        left_top.pack(side="left")
        tk.Label(left_top, text="J.A.R.V.I.S", bg="black", fg="#22d3ee", font=("JetBrains Mono", 11, "bold")).pack(side="left")
        tk.Label(left_top, text=" MARK XLII", bg="black", fg="#0891b2", font=("JetBrains Mono", 8), borderwidth=1, relief="solid", padx=3).pack(side="left", padx=6)
        self.time_top_label = tk.Label(left_top, text=datetime.now().strftime("%H:%M:%S %Y-%m-%d"), bg="black", fg="#64748b", font=("JetBrains Mono", 9))
        self.time_top_label.pack(side="left", padx=10)
        tk.Label(left_top, text="SHILATECH • Malibu Point 10880", bg="black", fg="#475569", font=("JetBrains Mono", 8)).pack(side="left", padx=8)

        right_top = tk.Frame(top, bg="black")
        right_top.pack(side="right")
        self.online_dot = tk.Label(right_top, text="●", bg="black", fg="#22c55e", font=("JetBrains Mono", 10))
        self.online_dot.pack(side="left")
        self.online_label = tk.Label(right_top, text="CHECKING... ONLINE", bg="black", fg="#22c55e", font=("JetBrains Mono", 9))
        self.online_label.pack(side="left", padx=4)
        self.decide_btn = tk.Button(right_top, text="CLICK TO DECIDE", command=self.toggle_decision, bg="#022c22", fg="#22c55e", font=("JetBrains Mono", 8), relief="solid", borderwidth=1, padx=6)
        self.decide_btn.pack(side="left", padx=6)
        tk.Label(right_top, text=f"USER: {self.user_name.upper()}", bg="black", fg="#94a3b8", font=("JetBrains Mono", 8)).pack(side="left", padx=8)
        self.arc_label_top = tk.Label(right_top, text=f"ARC {self._arc_power:.1f}%", bg="#083344", fg="#22d3ee", font=("JetBrains Mono", 8), borderwidth=1, relief="solid", padx=4)
        self.arc_label_top.pack(side="left", padx=4)

        # Main flex
        main = tk.Frame(self, bg="#020208")
        main.pack(fill="both", expand=True)

        # Left panel — Device specs + MITs + Security
        left = tk.Frame(main, bg="black", width=240, padx=8, pady=8, highlightbackground="#0e7490", highlightthickness=1)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        # Device specs
        dev_frame = tk.LabelFrame(left, text="SYSTEM • DEVICE SPECIFICATIONS", bg="black", fg="#0891b2", font=("JetBrains Mono", 8), padx=6, pady=6)
        dev_frame.pack(fill="x", pady=4)
        specs = [
            ("Device", "DESKTOP-3D8CN02"),
            ("CPU", "i5-6300U @ 2.40GHz"),
            ("RAM", "8.00 GB (7.41 usable)"),
            ("System", "64-bit x64"),
            ("OS", "Windows 11 Pro 21H2"),
            ("Engine", "CHECKING..."),
        ]
        self.spec_labels = {}
        for label, val in specs:
            row = tk.Frame(dev_frame, bg="black")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, bg="black", fg="#64748b", font=("JetBrains Mono", 8), width=10, anchor="w").pack(side="left")
            l = tk.Label(row, text=val, bg="black", fg="#cbd5e1", font=("JetBrains Mono", 8), anchor="w")
            l.pack(side="left", fill="x", expand=True)
            self.spec_labels[label] = l

        # MITs
        mit_frame = tk.LabelFrame(left, text="TODAY'S ALIGNMENT • 3 MITS", bg="black", fg="#22d3ee", font=("JetBrains Mono", 8), padx=6, pady=6)
        mit_frame.pack(fill="x", pady=6)
        self.mit_listbox = tk.Listbox(mit_frame, bg="#0a0a0f", fg="#86efac", font=("JetBrains Mono", 9), height=4, borderwidth=1, highlightthickness=0)
        self.mit_listbox.pack(fill="x", pady=4)
        for mit in self.mits:
            self.mit_listbox.insert("end", f"• {mit}")
        mit_entry_row = tk.Frame(mit_frame, bg="black")
        mit_entry_row.pack(fill="x", pady=2)
        self.mit_entry = tk.Entry(mit_entry_row, bg="#0a0a0f", fg="#86efac", font=("JetBrains Mono", 8))
        self.mit_entry.pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(mit_entry_row, text="ADD", command=self.add_mit, bg="black", fg="#22d3ee", font=("JetBrains Mono", 7), borderwidth=1, relief="solid").pack(side="left")
        tk.Label(mit_frame, text=f"Good morning {self.user_name}, Sir. 3 MITs to make today a win.", bg="black", fg="#475569", font=("JetBrains Mono", 7), wraplength=200, justify="left").pack(anchor="w", pady=2)
        tk.Button(mit_frame, text="RE-ALIGN DAY", command=lambda: self.send_prompt(f"plan my day MITs: {', '.join(self.mits)}"), bg="#022c22", fg="#22c55e", font=("JetBrains Mono", 8), borderwidth=1, relief="solid").pack(fill="x", pady=2)

        # Security
        sec_frame = tk.LabelFrame(left, text="SECURITY • DATA PROTECTION", bg="black", fg="#f59e0b", font=("JetBrains Mono", 8), padx=6, pady=6)
        sec_frame.pack(fill="x", pady=6)
        for txt in ["🔒 Local-first, private by default", "📴 Offline: nothing leaves device", "🌐 Online: only prompt sent to OpenAI if key", "🏠 Ollama local: LLM stays device even online", "🛡️ No telemetry, Apache 2.0"]:
            tk.Label(sec_frame, text=txt, bg="black", fg="#94a3b8", font=("JetBrains Mono", 7), anchor="w").pack(fill="x", pady=1)

        tk.Label(left, text="JARVIS v0.1.9 • Hybrid Online/Offline\nLocal-first • Auto Engine • Voice ready\nSHILATECH • Malibu Point 10880", bg="black", fg="#334155", font=("JetBrains Mono", 7), justify="left").pack(side="bottom", anchor="w", pady=8)

        # Right panel
        right = tk.Frame(main, bg="black", width=260, padx=8, pady=8, highlightbackground="#0e7490", highlightthickness=1)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # Decision panel — interactive when online
        self.decision_frame = tk.LabelFrame(right, text="🌐 ONLINE — INTERACTIVE DECISION — SHILATECH", bg="black", fg="#22d3ee", font=("JetBrains Mono", 8), padx=6, pady=6)
        self.decision_frame.pack(fill="x", pady=4)
        tk.Label(self.decision_frame, text="Network: Online — Same circular interface, you decide:", bg="black", fg="#94a3b8", font=("JetBrains Mono", 7), wraplength=220, justify="left").pack(anchor="w")
        tk.Button(self.decision_frame, text="1. FULL STACK ONLINE", command=lambda: self.decide_mode("1"), bg="#022c22", fg="#22c55e", font=("JetBrains Mono", 8, "bold"), borderwidth=1, relief="solid").pack(fill="x", pady=2)
        tk.Label(self.decision_frame, text="OpenAI if key HTTPS else Ollama local, full search, best quality, Badge ONLINE FULL STACK", bg="black", fg="#475569", font=("JetBrains Mono", 6), wraplength=220, justify="left").pack(fill="x")
        tk.Button(self.decision_frame, text="2. BASIC OFFLINE LOCAL EVEN ONLINE", command=lambda: self.decide_mode("2"), bg="#422006", fg="#f59e0b", font=("JetBrains Mono", 7, "bold"), borderwidth=1, relief="solid").pack(fill="x", pady=2)
        tk.Label(self.decision_frame, text="Nothing leaves device, private SHILATECH secure, same circular interface only badge changes", bg="black", fg="#475569", font=("JetBrains Mono", 6), wraplength=220, justify="left").pack(fill="x")

        # Weather like screenshot
        weather_frame = tk.LabelFrame(right, text="WEATHER • NAIROBI", bg="black", fg="#22d3ee", font=("JetBrains Mono", 8), padx=6, pady=6)
        weather_frame.pack(fill="x", pady=4)
        tk.Label(weather_frame, text="56°F", bg="black", fg="#7dd3fc", font=("JetBrains Mono", 18, "bold")).pack(anchor="w")
        tk.Label(weather_frame, text="Partly Cloudy", bg="black", fg="#cbd5e1", font=("JetBrains Mono", 9)).pack(anchor="w")
        tk.Label(weather_frame, text="High 74° • Low 60°", bg="black", fg="#64748b", font=("JetBrains Mono", 7)).pack(anchor="w")
        tk.Label(weather_frame, text="Precipitation: 10% • Humidity: 65% • Wind: 5 mph", bg="black", fg="#475569", font=("JetBrains Mono", 6), wraplength=220).pack(anchor="w", pady=2)

        # System
        sys_frame = tk.LabelFrame(right, text="SYSTEM • ONLINE/OFFLINE", bg="black", fg="#22d3ee", font=("JetBrains Mono", 8), padx=6, pady=6)
        sys_frame.pack(fill="x", pady=4)
        self.sys_labels = {}
        for k in ["Engine", "Mode", "Security", "Data"]:
            row = tk.Frame(sys_frame, bg="black")
            row.pack(fill="x")
            tk.Label(row, text=k, bg="black", fg="#64748b", font=("JetBrains Mono", 7), width=10, anchor="w").pack(side="left")
            l = tk.Label(row, text="CHECKING...", bg="black", fg="#22c55e", font=("JetBrains Mono", 7))
            l.pack(side="left")
            self.sys_labels[k] = l

        # Quick protocols
        qp_frame = tk.LabelFrame(right, text="QUICK PROTOCOLS", bg="black", fg="#64748b", font=("JetBrains Mono", 8), padx=6, pady=6)
        qp_frame.pack(fill="x", pady=4)
        btns = [
            ("DECIDE FULL", lambda: self.decide_mode("1")),
            ("DECIDE BASIC", lambda: self.decide_mode("2")),
            ("ONLINE CHECK", lambda: self.send_prompt("network_status status")),
            ("HYBRID MODE", lambda: self.send_prompt("hybrid_mode status")),
            ("GOOD MORNING", lambda: self.send_prompt(f"Good morning {self.user_name}")),
            ("SECURITY", lambda: self.send_prompt("How is my data secure?")),
        ]
        grid = tk.Frame(qp_frame, bg="black")
        grid.pack(fill="x")
        for i, (label, cmd) in enumerate(btns):
            r, c = divmod(i, 2)
            b = tk.Button(grid, text=label, command=cmd, bg="black", fg="#0891b2" if "DECIDE" not in label else "#22c55e" if "FULL" in label else "#f59e0b", font=("JetBrains Mono", 7), borderwidth=1, relief="solid", padx=2, pady=2)
            b.grid(row=r, column=c, padx=1, pady=1, sticky="ew")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        # Center — Circular HUD like screenshot
        center = tk.Frame(main, bg="#020208")
        center.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        # Canvas for circular HUD — matches IronManCircularHUD.tsx
        self.canvas_size = 560
        self.canvas = tk.Canvas(center, width=self.canvas_size, height=self.canvas_size, bg="#020208", highlightthickness=0)
        self.canvas.pack(pady=10)

        # Bottom info like screenshot
        self.bottom_info = tk.Label(center, text="Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • 🌐 ONLINE SECURE • ENCRYPTED", bg="#020208", fg="#475569", font=("JetBrains Mono", 8))
        self.bottom_info.pack()

        # Chat under circle — like Iron Man interactive
        chat_frame = tk.LabelFrame(center, text=f"CHAT • Good morning {self.user_name} • Voice 🔊 ON • SHILATECH", bg="black", fg="#22d3ee", font=("JetBrains Mono", 8), padx=6, pady=6)
        chat_frame.pack(fill="both", expand=True, pady=8)

        self.chat_box = tk.Text(chat_frame, bg="#020208", fg="#7dd3fc", font=("JetBrains Mono", 9), wrap="word", height=10, borderwidth=1, highlightbackground="#0e7490", highlightthickness=1)
        self.chat_box.pack(fill="both", expand=True, pady=2)
        self.chat_box.tag_config("user", foreground="#86efac")
        self.chat_box.tag_config("assistant", foreground="#7dd3fc")
        self.chat_box.tag_config("system", foreground="#f59e0b")

        input_row = tk.Frame(chat_frame, bg="black")
        input_row.pack(fill="x", pady=4)
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(input_row, textvariable=self.input_var, bg="#0a0a0f", fg="#7dd3fc", font=("JetBrains Mono", 9), insertbackground="#22d3ee")
        self.input_entry.pack(side="left", fill="x", expand=True, padx=2)
        self.input_entry.bind("<Return>", lambda e: self.send_prompt())
        tk.Button(input_row, text="🎤", command=self.voice_input, bg="black", fg="#22d3ee", font=("JetBrains Mono", 9), borderwidth=1, relief="solid", padx=6).pack(side="left", padx=2)
        tk.Button(input_row, text="🔊 VOICE ON", command=self.toggle_voice, bg="#022c22", fg="#22c55e", font=("JetBrains Mono", 8), borderwidth=1, relief="solid", padx=6).pack(side="left", padx=2)
        tk.Button(input_row, text="TRANSMIT", command=self.send_prompt, bg="#0891b2", fg="black", font=("JetBrains Mono", 9, "bold"), padx=10).pack(side="left", padx=2)

        # Bottom bar like screenshot
        bottom = tk.Frame(self, bg="black", padx=8, pady=2, highlightbackground="#0e7490", highlightthickness=1)
        bottom.pack(fill="x", side="bottom")
        tk.Label(bottom, text="Jarvis Iron Man Wallpaper 4K • Jarvis Iron Man Quotes • Jarvis Iron Man Hologram", bg="black", fg="#334155", font=("JetBrains Mono", 7)).pack(side="left")
        self.bottom_right = tk.Label(bottom, text="Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • 📴 OFFLINE SECURE • LOCAL ONLY • 03:01:00 • 2026-09-26", bg="black", fg="#475569", font=("JetBrains Mono", 7))
        self.bottom_right.pack(side="right")

        self.voice_enabled = True
        self.draw_circular_hud()
        self.update_clock()
        self.after(500, self.good_morning)
        self.after(1000, self.check_online)
        self.after(60000, self.keep_alive)

    def draw_circular_hud(self):
        try:
            if getattr(self, '_is_closing', False):
                return
            self.canvas.delete("all")
            cx = cy = self.canvas_size // 2
            rot = self._rot
            base = 240

            # Background with subtle grid
            self.canvas.create_rectangle(0, 0, self.canvas_size, self.canvas_size, fill="#020208", outline="")
            # Grid lines
            for i in range(0, self.canvas_size, 40):
                self.canvas.create_line(i, 0, i, self.canvas_size, fill="#0a0a0f", width=1)
                self.canvas.create_line(0, i, self.canvas_size, i, fill="#0a0a0f", width=1)

            # Outer housing 2 rings - chrome like screenshot
            self.canvas.create_oval(cx-base-30, cy-base-30, cx+base+30, cy+base+30, outline="#1e293b", width=3)
            self.canvas.create_oval(cx-base-20, cy-base-20, cx+base+20, cy+base+20, outline="#334155", width=1)
            self.canvas.create_oval(cx-base-12, cy-base-12, cx+base+12, cy+base+12, outline="#0e7490", width=1)

            # 72 tick marks like screenshot - major every 6 with numbers
            for i in range(72):
                angle = (i / 72) * 2 * math.pi - math.pi/2
                is_major = i % 6 == 0
                r1 = base + (12 if is_major else 6)
                r2 = base + (22 if is_major else 14)
                x1 = cx + math.cos(angle) * r1
                y1 = cy + math.sin(angle) * r1
                x2 = cx + math.cos(angle) * r2
                y2 = cy + math.sin(angle) * r2
                color = "#22d3ee" if is_major else "#475569"
                width = 2 if is_major else 1
                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width)
                if is_major:
                    # Number label
                    rx = cx + math.cos(angle) * (r2 + 12)
                    ry = cy + math.sin(angle) * (r2 + 12)
                    self.canvas.create_text(rx, ry, text=str(i), fill="#334155", font=("JetBrains Mono", 6))

            # 60 small rectangular segments - outer segmented ring like screenshot (more modern)
            for i in range(60):
                angle = (i / 60) * 2 * math.pi + rot * 0.01
                r = base - 8
                seg_w = 4
                # Small rectangle as line with thickness
                x1 = cx + math.cos(angle) * (r - seg_w)
                y1 = cy + math.sin(angle) * (r - seg_w)
                x2 = cx + math.cos(angle) * (r + seg_w)
                y2 = cy + math.sin(angle) * (r + seg_w)
                alpha = 0.3 + 0.7 * (math.sin(rot*0.05 + i*0.2) * 0.5 + 0.5)
                color = "#0891b2" if i % 3 == 0 else "#0e7490"
                if alpha > 0.6:
                    self.canvas.create_line(x1, y1, x2, y2, fill=color, width=2)

            # 24 larger blocks middle ring - like screenshot segmented blocks
            for i in range(24):
                angle = (i / 24) * 2 * math.pi + rot * 0.015
                seg_len = 0.18
                r = base - 28
                x1 = cx + math.cos(angle) * r
                y1 = cy + math.sin(angle) * r
                x2 = cx + math.cos(angle + seg_len) * r
                y2 = cy + math.sin(angle + seg_len) * r
                # Alternate colors for modern look
                color = "#22d3ee" if i % 4 == 0 else "#0e7490" if i % 2 == 0 else "#1e3a5f"
                width = 4 if i % 4 == 0 else 2
                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width)
                # Small gap
                # Add small dot at end
                self.canvas.create_oval(x2-1, y2-1, x2+1, y2+1, fill=color, outline="")

            # 16 segmented inner ring rotating opposite - more modern
            for i in range(16):
                angle = (i / 16) * 2 * math.pi - rot * 0.02
                seg_len = 0.25
                r = base - 50
                x1 = cx + math.cos(angle) * r
                y1 = cy + math.sin(angle) * r
                x2 = cx + math.cos(angle + seg_len) * r
                y2 = cy + math.sin(angle + seg_len) * r
                color = "#7dd3fc" if i % 2 == 0 else "#22d3ee"
                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=3)

            # Inner blue glowing ring with multi-layer glow - modern like screenshot
            # Glow layers
            for glow in range(6):
                alpha = 1 - glow*0.15
                width = 6 - glow
                r = base - 70 - glow*1.5
                # Use stipple for glow effect
                self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#22d3ee", width=1)

            self.canvas.create_oval(cx-base+70, cy-base+70, cx+base-70, cy+base-70, outline="#22d3ee", width=3)
            # Inner glow ring
            self.canvas.create_oval(cx-base+75, cy-base+75, cx+base-75, cy+base-75, outline="#7dd3fc", width=1, dash=(2,4))


            # 3 rotating energy prongs gradient white->cyan - more modern with glow and inner lines
            for i in range(3):
                angle = (i / 3) * 2 * math.pi + rot * 0.05
                r1 = 35
                r2 = base - 85
                x1 = cx + math.cos(angle) * r1
                y1 = cy + math.sin(angle) * r1
                x2 = cx + math.cos(angle) * r2
                y2 = cy + math.sin(angle) * r2
                # Outer glow
                self.canvas.create_line(x1, y1, x2, y2, fill="#0e7490", width=6)
                # Main prong white->cyan gradient simulated with 2 lines
                self.canvas.create_line(x1, y1, x2, y2, fill="#22d3ee", width=3)
                self.canvas.create_line(x1, y1, x2, y2, fill="#ffffff", width=1)
                # Small circle at end
                self.canvas.create_oval(x2-4, y2-4, x2+4, y2+4, fill="#22d3ee", outline="#ffffff", width=1)
                # Inner line
                mid_r = (r1 + r2) / 2
                mx = cx + math.cos(angle) * mid_r
                my = cy + math.sin(angle) * mid_r
                self.canvas.create_oval(mx-2, my-2, mx+2, my+2, fill="#7dd3fc", outline="")

            # Additional 6 small prongs for more modern look like screenshot
            for i in range(6):
                angle = (i / 6) * 2 * math.pi + rot * 0.03
                r1 = base - 70
                r2 = base - 55
                x1 = cx + math.cos(angle) * r1
                y1 = cy + math.sin(angle) * r1
                x2 = cx + math.cos(angle) * r2
                y2 = cy + math.sin(angle) * r2
                self.canvas.create_line(x1, y1, x2, y2, fill="#334155", width=1)

            # Inner core pulsing blue 28±4 - more modern with multiple layers like screenshot
            pulse = 28 + math.sin(rot * 0.08) * 4
            # Outer glow core
            for g in range(4):
                r = pulse + g*3
                self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#22d3ee", width=1)
            self.canvas.create_oval(cx-pulse, cy-pulse, cx+pulse, cy+pulse, fill="#22d3ee", outline="#7dd3fc", width=2)
            # Inner white core
            self.canvas.create_oval(cx-12, cy-12, cx+12, cy+12, fill="white", outline="#22d3ee", width=1)
            self.canvas.create_oval(cx-6, cy-6, cx+6, cy+6, fill="#7dd3fc", outline="")

            # Number 13 like screenshot - more prominent
            self.canvas.create_text(cx, cy, text="13", fill="black", font=("JetBrains Mono", 12, "bold"))

            # Inner small rings - multiple like screenshot for modern look
            self.canvas.create_oval(cx-45, cy-45, cx+45, cy+45, outline="#e2e8f0", width=1)
            self.canvas.create_oval(cx-55, cy-55, cx+55, cy+55, outline="#334155", width=1, dash=(3,3))
            self.canvas.create_oval(cx-35, cy-35, cx+35, cy+35, outline="#0e7490", width=1)

            # 8 data points around - more like screenshot
            for i in range(8):
                angle = (i / 8) * 2 * math.pi + rot * 0.02
                r = base - 120
                x = cx + math.cos(angle) * r
                y = cy + math.sin(angle) * r
                color = "#22d3ee" if i % 2 == 0 else "#7dd3fc"
                size = 3 if i % 2 == 0 else 2
                self.canvas.create_oval(x-size, y-size, x+size, y+size, fill=color, outline="")
                # Small line outward
                x2 = cx + math.cos(angle) * (r + 8)
                y2 = cy + math.sin(angle) * (r + 8)
                self.canvas.create_line(x, y, x2, y2, fill="#334155", width=1)

            # Overlays like screenshot — left/right data - more modern and detailed
            # Left side
            self.canvas.create_text(70, 60, text="99% - Strength", fill="#22d3ee", font=("JetBrains Mono", 8, "bold"), anchor="w")
            self.canvas.create_text(70, 75, text="Home WiFi - Source", fill="#64748b", font=("JetBrains Mono", 7), anchor="w")
            self.canvas.create_text(70, 95, text="Jarvis list", fill="#475569", font=("JetBrains Mono", 7), anchor="w")
            self.canvas.create_text(70, 110, text="• backup themes\n• backup control\n• warning control\n• system diagnostics\n• network status", fill="#334155", font=("JetBrains Mono", 6), justify="left", anchor="w")
            self.canvas.create_text(70, 170, text="SYSTEM • ONLINE\nEngine: OLLAMA\nMode: FULL STACK\nLatency: 33ms\nSHILATECH SECURE", fill="#0e7490", font=("JetBrains Mono", 6), justify="left", anchor="w")

            # Right side - weather like screenshot more modern
            self.canvas.create_text(self.canvas_size-70, 60, text="WEATHER • NAIROBI", fill="#0e7490", font=("JetBrains Mono", 7), anchor="e")
            self.canvas.create_text(self.canvas_size-70, 80, text="56°F", fill="#7dd3fc", font=("JetBrains Mono", 16, "bold"), anchor="e")
            self.canvas.create_text(self.canvas_size-70, 95, text="Partly Cloudy", fill="#cbd5e1", font=("JetBrains Mono", 8), anchor="e")
            self.canvas.create_text(self.canvas_size-70, 108, text="High 74° • Low 60°", fill="#64748b", font=("JetBrains Mono", 7), anchor="e")
            self.canvas.create_text(self.canvas_size-70, 125, text="Precipitation: 10%\nHumidity: 65%\nWind: 5 mph\nSHILATECH", fill="#475569", font=("JetBrains Mono", 6), justify="right", anchor="e")

            # Bottom extra data like screenshot
            self.canvas.create_text(cx, self.canvas_size-20, text="Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • ONLINE SECURE • ENCRYPTED • 33ms • SHILATECH", fill="#334155", font=("JetBrains Mono", 7))


            self._rot += 1
            self._arc_power = 94 + random.random() * 6

        except Exception as e:
            if logging:
                logging.error("draw_circular_hud failed: %s", e)
        finally:
            try:
                if not getattr(self, '_is_closing', False):
                    self.after(50, self.draw_circular_hud)
            except:
                pass

    def load_name(self):
        try:
            home = get_home()
            name_file = home / "user_name.txt"
            if name_file.exists():
                return name_file.read_text().strip() or "Eugene"
        except:
            pass
        return "Eugene"

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
        self.mit_listbox.delete(0, "end")
        for mit in self.mits:
            self.mit_listbox.insert("end", f"• {mit}")
        self.mit_entry.delete(0, "end")

    def update_clock(self):
        try:
            if getattr(self, '_is_closing', False):
                return
            now = datetime.now()
            if hasattr(self, 'time_top_label') and self.time_top_label.winfo_exists():
                self.time_top_label.config(text=now.strftime("%H:%M:%S %Y-%m-%d") + " • SHILATECH")
            if hasattr(self, 'arc_label_top') and self.arc_label_top.winfo_exists():
                self.arc_label_top.config(text=f"ARC {self._arc_power:.1f}%")
            if hasattr(self, 'bottom_right') and self.bottom_right.winfo_exists():
                self.bottom_right.config(text=f"Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • {'🌐 ONLINE' if self.online_status.get('online') else '📴 OFFLINE'} SECURE • {now.strftime('%H:%M:%S')} • {now.strftime('%Y-%m-%d')}")
        except Exception as e:
            if logging:
                logging.error("update_clock failed: %s", e)
        finally:
            try:
                if not getattr(self, '_is_closing', False):
                    self.after(1000, self.update_clock)
            except:
                pass

    def keep_alive(self):
        try:
            if getattr(self, '_is_closing', False):
                return
            if logging:
                logging.info("Keep-alive ping - Circular HUD still running, Sir.")
            try:
                if not self.winfo_viewable():
                    if logging:
                        logging.warning("Window not viewable, deiconifying")
                    self.deiconify()
            except:
                pass
        except Exception as e:
            if logging:
                logging.error("keep_alive failed: %s", e)
        finally:
            try:
                if not getattr(self, '_is_closing', False):
                    self.after(60000, self.keep_alive)
            except:
                pass

    def on_close(self):
        try:
            if logging:
                logging.info("Close requested")
            result = messagebox.askyesnocancel(
                "JARVIS SHILATECH Circular HUD - Stay Open?",
                "JARVIS is about to close, Sir.\n\nYes = Quit\nNo = Minimize to taskbar (stays running)\nCancel = Stay open\n\nCircular HUD like screenshot with voice + hybrid interactive"
            )
            if result is None:
                return
            elif result is False:
                self.iconify()
                return
            else:
                self._is_closing = True
                self.quit()
                self.destroy()
        except Exception as e:
            if logging:
                logging.error("on_close failed: %s", e)

    def toggle_decision(self):
        try:
            if not self.online_status.get("online"):
                self.add_message("system", "Offline, Sir — already Basic Local. Nothing leaves device. SHILATECH secure.")
                return
            # Toggle decision frame visibility
            self.decision_frame.lift()
            self.add_message("system", "🌐 ONLINE — Interactive Decision — SHILATECH\n\nSame circular interface, Sir. You decide:\n\n1. Full Stack Online — openai if key HTTPS encrypted else ollama local, full search, best quality, Badge ONLINE FULL STACK\n2. Basic Offline Local Even Though Online — mock/ollama local, nothing leaves device, private, SHILATECH secure, Badge ONLINE BASIC LOCAL\n\nClick buttons on right panel to decide.")
        except Exception as e:
            self.add_message("system", f"Decision toggle failed: {e}")

    def decide_mode(self, choice):
        try:
            from jarvis.core.network import get_auto_status
            from jarvis.tools.network_tools import HybridModeTool
            status = get_auto_status()
            tool = HybridModeTool()
            if not status['network']['online']:
                self.add_message('system', f"Offline, Sir — already Basic Local. Nothing leaves device. SHILATECH secure. {status['selected']['engine']} {status['selected']['mode']}")
                return
            res = tool.run(action='decide', choice=choice)
            self.add_message('system', res[:800])
            if choice == '2':
                self._forced_mode = "basic"
                self.online_label.config(text='🌐 ONLINE • BASIC LOCAL • SHILATECH — you decided', fg='#f59e0b')
                self.online_dot.config(fg='#f59e0b')
            else:
                self._forced_mode = "full"
                self.online_label.config(text=f"🌐 ONLINE {status['selected']['engine'].upper()} FULL STACK — you decided", fg='#22c55e')
                self.online_dot.config(fg='#22c55e')
            self.check_online()
        except Exception as e:
            self.add_message('system', f"Decide failed: {e}")

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
                        try:
                            if online:
                                if self._forced_mode == "basic":
                                    self.online_dot.config(fg="#f59e0b")
                                    self.online_label.config(text=f"🌐 ONLINE • BASIC LOCAL • SHILATECH", fg="#f59e0b")
                                    self.sys_labels["Engine"].config(text=f"{engine.upper()} • BASIC LOCAL", fg="#f59e0b")
                                    self.sys_labels["Mode"].config(text="BASIC LOCAL EVEN ONLINE", fg="#f59e0b")
                                    self.sys_labels["Security"].config(text="🔒 SECURE • SHILATECH", fg="#22c55e")
                                    self.sys_labels["Data"].config(text="LOCAL ONLY • PRIVATE", fg="#22c55e")
                                    self.bottom_info.config(text=f"Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • 🌐 ONLINE BASIC LOCAL • SHILATECH SECURE")
                                    self.spec_labels["Engine"].config(text=f"{engine.upper()} • BASIC LOCAL EVEN ONLINE", fg="#f59e0b")
                                else:
                                    self.online_dot.config(fg="#22c55e")
                                    self.online_label.config(text=f"🌐 ONLINE {engine.upper()} {latency}ms" if latency else f"🌐 ONLINE {engine.upper()} • FULL STACK", fg="#22c55e")
                                    self.sys_labels["Engine"].config(text=engine.upper(), fg="#22c55e")
                                    self.sys_labels["Mode"].config(text="FULL STACK" if "full" in mode else mode.upper(), fg="#22c55e")
                                    self.sys_labels["Security"].config(text="🔒 SECURE • ENCRYPTED", fg="#22c55e")
                                    self.sys_labels["Data"].config(text="ENCRYPTED • SHILATECH" if "openai" in engine else "LOCAL ONLY" if "ollama" in engine else "SECURE", fg="#22c55e")
                                    self.bottom_info.config(text=f"Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • 🌐 ONLINE SECURE • ENCRYPTED • {latency}ms" if latency else "Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • 🌐 ONLINE SECURE")
                                    self.spec_labels["Engine"].config(text=f"{engine.upper()} • ONLINE FULL STACK", fg="#22c55e")
                            else:
                                self.online_dot.config(fg="#ef4444")
                                self.online_label.config(text="📴 OFFLINE • BASIC • SHILATECH", fg="#fca5a5")
                                self.sys_labels["Engine"].config(text=f"{engine.upper()} • OFFLINE", fg="#fca5a5")
                                self.sys_labels["Mode"].config(text="BASIC LOCAL", fg="#f59e0b")
                                self.sys_labels["Security"].config(text="🔒 SECURE • LOCAL ONLY", fg="#22c55e")
                                self.sys_labels["Data"].config(text="LOCAL ONLY • PRIVATE", fg="#22c55e")
                                self.bottom_info.config(text="Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • 📴 OFFLINE SECURE • LOCAL ONLY • SHILATECH")
                                self.spec_labels["Engine"].config(text=f"{engine.upper()} • OFFLINE BASIC", fg="#f59e0b")
                        except Exception as e:
                            if logging:
                                logging.error("update_ui failed: %s", e)

                    self.after(0, update_ui)
                else:
                    self.after(0, lambda: self.online_label.config(text="MOCK — No JARVIS", fg="#94a3b8"))
            except Exception as e:
                self.after(0, lambda: self.online_label.config(text=f"CHECK FAILED: {e}", fg="#fca5a5"))

        threading.Thread(target=worker, daemon=True).start()
        try:
            if not getattr(self, '_is_closing', False):
                self.after(30000, self.check_online)
        except:
            pass

    def good_morning(self):
        try:
            hour = datetime.now().hour
            greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
            date_str = datetime.now().strftime("%A, %B %d")
            time_str = datetime.now().strftime("%I:%M %p")
            mit_text = "\n".join([f"{i+1}. {m}" for i, m in enumerate(self.mits)])
            online_text = f"Hybrid: {self.online_status.get('mode','CHECKING')} via {self.online_status.get('engine','auto')} — Online full stack when online, basic when offline, Sir. SHILATECH."

            msg = f"""{greeting}, {self.user_name}. It's {time_str} on {date_str}.

Arc reactor at {self._arc_power:.1f}% — All systems nominal. Lab secure, perimeter clear. SHILATECH.

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
• "hybrid_mode interactive" to decide Full Stack vs Basic Local even though online
• Voice: Click 🎤 to speak — offline browser API + pyttsx3/kokoro offline backend speaks both online/offline

🔊 Voice: ON — JARVIS speaks both online & offline, Sir. Circular HUD like screenshot — same interface local and online, only badge changes.

SHILATECH • Malibu Point 10880"""

            self.add_message("assistant", msg)
            # Voice initialization - auto-speak Good Morning with TTS both online/offline
            try:
                if getattr(self, 'voice_enabled', True):
                    voice_text = f"{greeting}, {self.user_name}. It's {time_str} on {date_str}. Arc reactor at {self._arc_power:.1f} percent. All systems nominal. Lab secure. Today's alignment {len(self.mits)} MITs to make today a win. SHILATECH secure. I speak both online and offline, Sir."
                    self.after(1500, lambda: self.speak(voice_text))
                    if logging:
                        logging.info("Voice auto-initialized, speaking Good Morning: %s", voice_text[:80])
            except Exception as ve:
                if logging:
                    logging.error("Voice auto-speak failed: %s", ve)
        except Exception as e:
            if logging:
                logging.error("good_morning failed: %s", e)

    def add_message(self, role, content):
        try:
            self.chat_box.config(state="normal")
            prefix = f"{self.user_name.upper()}" if role == "user" else "JARVIS" if role == "assistant" else "SYSTEM"
            time_str = datetime.now().strftime("%H:%M")
            tag = role if role in ["user", "assistant", "system"] else "assistant"
            self.chat_box.insert("end", f"\n{prefix} • {time_str} • {'ENCRYPTED' if role=='assistant' else 'SHILATECH'}\n", tag)
            self.chat_box.insert("end", f"{content}\n", tag)
            self.chat_box.config(state="disabled")
            self.chat_box.see("end")
        except Exception as e:
            if logging:
                logging.error("add_message failed: %s", e)

    def send_prompt(self, prompt=None):
        try:
            if prompt is None:
                prompt = self.input_var.get().strip()
            if not prompt:
                return
            self.add_message("user", prompt)
            self.input_var.set("")
            self.chat_box.config(state="normal")
            self.chat_box.insert("end", f"\nJARVIS • {datetime.now().strftime('%H:%M')} • THINKING...\n", "assistant")
            self.chat_box.config(state="disabled")

            def worker():
                try:
                    if HAS_JARVIS:
                        JarvisConfig, get_agent, list_agents, list_engines, EngineType, list_tools, get_auto_status = IMPORTS
                        cfg = JarvisConfig.load()
                        if cfg.auto.enabled:
                            cfg.engine.type = EngineType.AUTO
                        lower = prompt.lower()
                        is_adhd = any(k in lower for k in ["brain dump", "break down", "focus on", "mit", "overwhelm", "energy", "win", "plan my day"])
                        agent_name = "adhd_coach" if is_adhd else "ironman"
                        agent = get_agent(agent_name, config=cfg)
                        resp = agent.run(prompt, context="")
                        self.after(0, lambda: self.add_message("assistant", resp.content))
                    else:
                        mock_resp = f"""Mock response for: {prompt}

Good morning {self.user_name}, Sir. Mock engine offline, but I'm here. Hybrid: {self.online_status.get('mode','CHECKING')}.

Today's Alignment:
{chr(10).join([f'{i+1}. {m}' for i, m in enumerate(self.mits)])}

System: All nominal. Arc reactor {self._arc_power:.1f}%. Lab secure. SHILATECH.

(Install JARVIS: pip install -e .[all] for real AI)"""
                        self.after(0, lambda: self.add_message("assistant", mock_resp))
                except Exception as e:
                    self.after(0, lambda: self.add_message("assistant", f"Error: {e}\n{traceback.format_exc()[:500]}"))

            threading.Thread(target=worker, daemon=True).start()
        except Exception as e:
            if logging:
                logging.error("send_prompt failed: %s", e)

    def speak(self, text):
        # Voice speaks both online/offline - pyttsx3 offline + Windows SAPI
        if not getattr(self, 'voice_enabled', True):
            return
        try:
            # Try pyttsx3 offline
            import pyttsx3
            def tts_thread():
                try:
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 180)
                    # Try British voice
                    voices = engine.getProperty('voices')
                    for v in voices:
                        if 'british' in v.name.lower() or 'uk' in v.name.lower() or 'english' in v.name.lower():
                            engine.setProperty('voice', v.id)
                            break
                    # Clean text for speech
                    clean = text[:400].replace('```',' ').replace('*','').replace('#','').replace('•','').replace('—',' ')
                    engine.say(clean)
                    engine.runAndWait()
                except Exception as e:
                    if logging:
                        logging.error("TTS pyttsx3 failed: %s", e)
                    # Fallback to Windows SAPI via win32com
                    try:
                        import win32com.client
                        speaker = win32com.client.Dispatch("SAPI.SpVoice")
                        speaker.Speak(text[:400])
                    except:
                        try:
                            import subprocess
                            subprocess.run(["espeak", text[:400]], timeout=5)
                        except:
                            pass
            threading.Thread(target=tts_thread, daemon=True).start()
            if logging:
                logging.info("Speaking: %s", text[:100])
        except Exception as e:
            if logging:
                logging.error("Speak failed: %s", e)
            # Fallback: try Windows PowerShell SAPI
            try:
                import subprocess
                ps_cmd = f'Add-Type -AssemblyName System.Speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak("{text[:200].replace(chr(34), "")}");'
                threading.Thread(target=lambda: subprocess.run(["powershell", "-Command", ps_cmd], timeout=10), daemon=True).start()
            except:
                pass

    def voice_input(self):
        self.add_message("system", "🎤 Voice input — listening, Sir. SHILATECH voice uses offline API.\n\nIn frontend circular HUD real mic works via Web Audio API + SpeechRecognition browser offline.\n\nDesktop: pip install faster-whisper + sounddevice for real mic, or type.\n\nTry: 'Good morning Eugene', 'network_status', 'hybrid_mode interactive'")
        # Try real STT if available
        try:
            from jarvis.speech.voice_io import VoiceIO
            vio = VoiceIO()
            self.add_message("system", f"STT: {vio.stt_engine} — TTS: {vio.tts_engine} — VoiceIO ready, Sir. Say something...")
            def listen_thread():
                try:
                    text = vio.listen(timeout=5, phrase_time_limit=5)
                    if text:
                        self.after(0, lambda: self.send_prompt(text))
                except Exception as e:
                    self.after(0, lambda: self.add_message("system", f"Listen failed: {e}, type instead, Sir."))
            threading.Thread(target=listen_thread, daemon=True).start()
        except Exception as e:
            self.add_message("system", f"Voice deps missing: {e}. Install: pip install -e .[voice] for faster-whisper offline. For now type, Sir.")

    def toggle_voice(self):
        self.voice_enabled = not getattr(self, 'voice_enabled', True)
        status = f"Voice {'ON 🔊' if self.voice_enabled else 'OFF 🔇'} — JARVIS speaks both online & offline, Sir."
        self.add_message("system", status + f"\n\n{'Browser speechSynthesis offline + pyttsx3/kokoro offline backend speaks' if self.voice_enabled else 'Muted — click again to enable'}")
        if self.voice_enabled:
            self.speak(f"Voice enabled, Sir. Good morning {self.user_name}. Circular HUD online, SHILATECH secure. I speak both online and offline.")
        if logging:
            logging.info("Voice toggled: %s", self.voice_enabled)



def main():
    try:
        app = CircularHUDApp()
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
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("JARVIS Circular HUD Error - Staying Open", f"Failed to start circular HUD:\n{e}\n\n{traceback.format_exc()[:1000]}\n\nTry:\n- python app.py from CMD to see error\n- Frontend: cd frontend && npm run dev\n- Check ~/.jarvis/jarvis.log\n- See docs/FIX_STAYS_THEN_DISAPPEARS.md")
            root.destroy()
        except:
            pass
        input("Press Enter to exit... SHILATECH Circular HUD")


if __name__ == "__main__":
    main()
