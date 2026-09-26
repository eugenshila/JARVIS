"""JARVIS Desktop GUI — Standalone executable that stays open — Iron Man Circular HUD v0.1.10.1

This is built with PyInstaller --windowed so it doesn't need console and stays open.
Uses Tkinter which is included in standard Python.
Responsive Iron Man HUD: central blue ring 13, visible voice controls, function dock, clap-wake button, and auto voice init.

Fixes MSI not upgrading + way off green fallback UI: self-contained CircularHUDApp, no external app.py dependency, always Iron HUD.
"""

import sys
import os
from pathlib import Path
import traceback
import math
import threading
import logging
import subprocess
import time
from datetime import datetime

# Setup logging
try:
    log_dir = Path.home() / ".jarvis"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "jarvis.log"
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler(sys.stdout)])
    logging.info("JARVIS Iron Man Circular HUD Desktop starting - SHILATECH v0.1.10.1")
except:
    logging = None

# Ensure src on path for jarvis core (optional)
def get_base_paths():
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
        exe_dir = Path(sys.executable).parent
        return [base, exe_dir, base / "src", exe_dir / "src"]
    else:
        ROOT = Path(__file__).parent.parent.parent.parent
        SRC = ROOT / "src"
        return [ROOT, SRC]

for p in get_base_paths():
    try:
        if str(p) not in sys.path and p.exists():
            sys.path.insert(0, str(p))
    except:
        pass

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)

# Try import jarvis core (optional, for chat)
try:
    from jarvis.core.config import JarvisConfig
    from jarvis.agents.registry import get_agent
    from jarvis.core.types import EngineType
    HAS_JARVIS = True
except:
    HAS_JARVIS = False
    JarvisConfig = None

import tkinter as tk
from tkinter import messagebox

class ModernCircularHUDApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("J.A.R.V.I.S — MARK XLII — SHILATECH — Iron Man HUD — Voice + Clap Wake — v0.1.10.1")
        # Fit common laptop screens (1366x768) so the voice/clap controls are visible.
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1400, max(1000, screen_w - 70))
        win_h = min(850, max(620, screen_h - 90))
        if win_w > screen_w - 20:
            win_w = max(900, screen_w - 20)
        if win_h > screen_h - 20:
            win_h = max(600, screen_h - 50)
        self.compact = win_w < 1320 or win_h < 760
        self.left_panel_width = 210 if self.compact else 240
        self.right_panel_width = 230 if self.compact else 260
        self.chat_height = 5 if self.compact else 10
        self.canvas_size = min(560, max(340, win_h - (285 if self.compact else 290)))
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(980, 600)
        self.configure(bg="#020208")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._is_closing = False
        self._rot = 0
        self._arc_power = 97.3
        self.voice_enabled = True
        self.clap_enabled = False
        self.user_name = "Eugene"

        # Top bar
        top = tk.Frame(self, bg="black", padx=8, pady=4, highlightbackground="#0e7490", highlightthickness=1)
        top.pack(fill="x")
        left_top = tk.Frame(top, bg="black")
        left_top.pack(side="left")
        tk.Label(left_top, text="J.A.R.V.I.S", bg="black", fg="#22d3ee", font=("JetBrains Mono", 11, "bold")).pack(side="left")
        tk.Label(left_top, text=" MARK XLII", bg="black", fg="#0891b2", font=("JetBrains Mono", 8), borderwidth=1, relief="solid", padx=3).pack(side="left", padx=6)
        self.time_top_label = tk.Label(left_top, text=datetime.now().strftime("%H:%M:%S %Y-%m-%d"), bg="black", fg="#64748b", font=("JetBrains Mono", 9))
        self.time_top_label.pack(side="left", padx=10)
        tk.Label(left_top, text="SHILATECH • Malibu Point 10880 • v0.1.10.1 IRON", bg="black", fg="#22d3ee", font=("JetBrains Mono", 8)).pack(side="left", padx=8)

        right_top = tk.Frame(top, bg="black")
        right_top.pack(side="right")
        self.online_dot = tk.Label(right_top, text="●", bg="black", fg="#22c55e", font=("JetBrains Mono", 10))
        self.online_dot.pack(side="left")
        self.online_label = tk.Label(right_top, text="ONLINE • IRON HUD", bg="black", fg="#22c55e", font=("JetBrains Mono", 9))
        self.online_label.pack(side="left", padx=4)
        tk.Button(right_top, text="🎤", command=self.voice_input, bg="black", fg="#22d3ee", font=("JetBrains Mono", 8), relief="solid", borderwidth=1, padx=4).pack(side="left", padx=2)
        tk.Button(right_top, text="🔊", command=self.test_voice, bg="#022c22", fg="#22c55e", font=("JetBrains Mono", 8), relief="solid", borderwidth=1, padx=4).pack(side="left", padx=2)
        tk.Button(right_top, text="👏", command=self.toggle_clap_wake, bg="#111827", fg="#f59e0b", font=("JetBrains Mono", 8), relief="solid", borderwidth=1, padx=4).pack(side="left", padx=2)
        tk.Label(right_top, text=f"USER: {self.user_name.upper()}", bg="black", fg="#94a3b8", font=("JetBrains Mono", 8)).pack(side="left", padx=8)
        self.arc_label_top = tk.Label(right_top, text=f"ARC {self._arc_power:.1f}%", bg="#083344", fg="#22d3ee", font=("JetBrains Mono", 8), borderwidth=1, relief="solid", padx=4)
        self.arc_label_top.pack(side="left", padx=4)

        # Main
        main = tk.Frame(self, bg="#020208")
        main.pack(fill="both", expand=True)

        # Left panel
        left = tk.Frame(main, bg="black", width=self.left_panel_width, padx=6 if self.compact else 8, pady=6 if self.compact else 8, highlightbackground="#0e7490", highlightthickness=1)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        dev_frame = tk.LabelFrame(left, text="SYSTEM • DEVICE SPECIFICATIONS", bg="black", fg="#0891b2", font=("JetBrains Mono", 8), padx=6, pady=6)
        dev_frame.pack(fill="x", pady=4)
        for label, val in [("Device", "DESKTOP-3D8CN02"), ("CPU", "i5-6300U @ 2.40GHz"), ("RAM", "8.00 GB"), ("System", "64-bit x64"), ("OS", "Windows 11 Pro"), ("Engine", "MOCK+OLLAMA"), ("HUD", "IRON v0.1.10.1")]:
            row = tk.Frame(dev_frame, bg="black")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, bg="black", fg="#64748b", font=("JetBrains Mono", 8), width=10, anchor="w").pack(side="left")
            tk.Label(row, text=val, bg="black", fg="#cbd5e1", font=("JetBrains Mono", 8), anchor="w").pack(side="left", fill="x", expand=True)

        mit_frame = tk.LabelFrame(left, text="TODAY'S ALIGNMENT • 3 MITS", bg="black", fg="#22d3ee", font=("JetBrains Mono", 8), padx=6, pady=6)
        mit_frame.pack(fill="x", pady=6)
        for mit in ["• Deep Work 2h", "• JARVIS Iron HUD", "• SHILATECH Secure"]:
            tk.Label(mit_frame, text=mit, bg="black", fg="#86efac", font=("JetBrains Mono", 8), anchor="w").pack(fill="x")
        tk.Label(mit_frame, text=f"Good morning {self.user_name}, Sir. Iron HUD online.", bg="black", fg="#475569", font=("JetBrains Mono", 7), wraplength=200, justify="left").pack(anchor="w", pady=4)

        sec_frame = tk.LabelFrame(left, text="SECURITY • SHILATECH", bg="black", fg="#f59e0b", font=("JetBrains Mono", 8), padx=6, pady=6)
        sec_frame.pack(fill="x", pady=6)
        for txt in ["🔒 Local-first, private", "📴 Offline: nothing leaves", "🌐 Online: prompt only", "🏠 Ollama local LLM", "🛡️ No telemetry", "✅ IRON HUD v0.1.10.1"]:
            tk.Label(sec_frame, text=txt, bg="black", fg="#94a3b8", font=("JetBrains Mono", 7), anchor="w").pack(fill="x", pady=1)

        tk.Label(left, text="JARVIS v0.1.10.1 IRON\nCircular HUD 13 72 ticks\n60 segments 24 blocks\nSHILATECH • Malibu Point", bg="black", fg="#22d3ee", font=("JetBrains Mono", 7), justify="left").pack(side="bottom", anchor="w", pady=8)

        # Right panel
        right = tk.Frame(main, bg="black", width=self.right_panel_width, padx=6 if self.compact else 8, pady=6 if self.compact else 8, highlightbackground="#0e7490", highlightthickness=1)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        decision_frame = tk.LabelFrame(right, text="🌐 ONLINE — IRON HUD v0.1.10.1", bg="black", fg="#22d3ee", font=("JetBrains Mono", 8), padx=6, pady=6)
        decision_frame.pack(fill="x", pady=4)
        tk.Label(decision_frame, text="Iron Man Circular HUD active\nSame interface online/offline", bg="black", fg="#94a3b8", font=("JetBrains Mono", 7), wraplength=220, justify="left").pack(anchor="w")
        tk.Button(decision_frame, text="1. FULL STACK ONLINE", command=lambda: self.add_message("system", "FULL STACK ONLINE — OpenAI if key else Ollama local"), bg="#022c22", fg="#22c55e", font=("JetBrains Mono", 8, "bold"), borderwidth=1, relief="solid").pack(fill="x", pady=2)
        tk.Button(decision_frame, text="2. BASIC OFFLINE LOCAL", command=lambda: self.add_message("system", "BASIC OFFLINE — Nothing leaves device"), bg="#422006", fg="#f59e0b", font=("JetBrains Mono", 7, "bold"), borderwidth=1, relief="solid").pack(fill="x", pady=2)

        weather_frame = tk.LabelFrame(right, text="WEATHER • NAIROBI", bg="black", fg="#22d3ee", font=("JetBrains Mono", 8), padx=6, pady=6)
        weather_frame.pack(fill="x", pady=4)
        tk.Label(weather_frame, text="56°F", bg="black", fg="#7dd3fc", font=("JetBrains Mono", 18, "bold")).pack(anchor="w")
        tk.Label(weather_frame, text="Partly Cloudy", bg="black", fg="#cbd5e1", font=("JetBrains Mono", 9)).pack(anchor="w")
        tk.Label(weather_frame, text="High 74° • Low 60°", bg="black", fg="#64748b", font=("JetBrains Mono", 7)).pack(anchor="w")
        tk.Label(weather_frame, text="Precipitation: 10% • Humidity: 65% • Wind: 5 mph\nSHILATECH v0.1.10.1 IRON", bg="black", fg="#475569", font=("JetBrains Mono", 6), wraplength=220).pack(anchor="w", pady=2)

        sys_frame = tk.LabelFrame(right, text="SYSTEM • IRON", bg="black", fg="#22d3ee", font=("JetBrains Mono", 8), padx=6, pady=6)
        sys_frame.pack(fill="x", pady=4)
        for k, v in [("Engine", "MOCK+OLLAMA"), ("Mode", "IRON HUD"), ("Security", "SHILATECH"), ("Version", "v0.1.10.1")]:
            row = tk.Frame(sys_frame, bg="black")
            row.pack(fill="x")
            tk.Label(row, text=k, bg="black", fg="#64748b", font=("JetBrains Mono", 7), width=10, anchor="w").pack(side="left")
            tk.Label(row, text=v, bg="black", fg="#22c55e", font=("JetBrains Mono", 7)).pack(side="left")

        function_frame = tk.LabelFrame(right, text="VOICE + FUNCTIONS", bg="black", fg="#f59e0b", font=("JetBrains Mono", 8), padx=6, pady=6)
        function_frame.pack(fill="x", pady=4)
        function_buttons = [
            ("🎤 MIC LISTEN", self.voice_input, "#0e7490"),
            ("🔊 TEST VOICE", self.test_voice, "#166534"),
            ("👏 CLAP WAKE", self.toggle_clap_wake, "#92400e"),
            ("🧰 SHOW TOOLS", self.show_tools, "#1e3a8a"),
            ("🩺 DOCTOR", self.run_doctor, "#312e81"),
            ("⚡ GOOD MORNING", self.good_morning, "#083344"),
        ]
        for i, (label, cmd, bg) in enumerate(function_buttons):
            button = tk.Button(function_frame, text=label, command=cmd, bg=bg, fg="#e0f2fe", font=("JetBrains Mono", 7, "bold"), borderwidth=1, relief="solid", padx=2, pady=2)
            button.grid(row=i // 2, column=i % 2, sticky="ew", padx=1, pady=1)
            if "CLAP" in label:
                self.clap_button = button
        function_frame.columnconfigure(0, weight=1)
        function_frame.columnconfigure(1, weight=1)
        tk.Label(function_frame, text="These are controls, not just chat: mic, speaker, clap wake, tools, doctor.", bg="black", fg="#64748b", font=("JetBrains Mono", 6), wraplength=self.right_panel_width - 24, justify="left").grid(row=3, column=0, columnspan=2, sticky="ew", pady=(3,0))

        # Center — Circular HUD
        center = tk.Frame(main, bg="#020208")
        center.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        self.canvas = tk.Canvas(center, width=self.canvas_size, height=self.canvas_size, bg="#020208", highlightthickness=0)
        self.canvas.pack(pady=10)

        self.bottom_info = tk.Label(center, text="Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • 🌐 IRON HUD v0.1.10.1 • ONLINE SECURE • ENCRYPTED", bg="#020208", fg="#475569", font=("JetBrains Mono", 8))
        self.bottom_info.pack()

        chat_frame = tk.LabelFrame(center, text=f"CHAT • Good morning {self.user_name} • Voice 🔊 ON • SHILATECH v0.1.10.1 IRON", bg="black", fg="#22d3ee", font=("JetBrains Mono", 8), padx=6, pady=6)
        chat_frame.pack(fill="both", expand=True, pady=8)

        self.chat_box = tk.Text(chat_frame, bg="#020208", fg="#7dd3fc", font=("JetBrains Mono", 8 if self.compact else 9), wrap="word", height=self.chat_height, borderwidth=1, highlightbackground="#0e7490", highlightthickness=1)
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
        self.mic_button = tk.Button(input_row, text="🎤 MIC", command=self.voice_input, bg="black", fg="#22d3ee", font=("JetBrains Mono", 8 if self.compact else 9), borderwidth=1, relief="solid", padx=5)
        self.mic_button.pack(side="left", padx=2)
        self.voice_button = tk.Button(input_row, text="🔊 VOICE ON", command=self.toggle_voice, bg="#022c22", fg="#22c55e", font=("JetBrains Mono", 7 if self.compact else 8), borderwidth=1, relief="solid", padx=5)
        self.voice_button.pack(side="left", padx=2)
        tk.Button(input_row, text="👏", command=self.toggle_clap_wake, bg="#111827", fg="#f59e0b", font=("JetBrains Mono", 8), borderwidth=1, relief="solid", padx=5).pack(side="left", padx=2)
        tk.Button(input_row, text="TRANSMIT", command=self.send_prompt, bg="#0891b2", fg="black", font=("JetBrains Mono", 8 if self.compact else 9, "bold"), padx=8).pack(side="left", padx=2)

        bottom = tk.Frame(self, bg="black", padx=8, pady=2, highlightbackground="#0e7490", highlightthickness=1)
        bottom.pack(fill="x", side="bottom")
        tk.Label(bottom, text="JARVIS v0.1.10.1 IRON Circular HUD 13 72 ticks 60 segments • SHILATECH", bg="black", fg="#22d3ee", font=("JetBrains Mono", 7)).pack(side="left")
        self.bottom_right = tk.Label(bottom, text=f"Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • IRON v0.1.10.1 • {datetime.now().strftime('%H:%M:%S')}", bg="black", fg="#475569", font=("JetBrains Mono", 7))
        self.bottom_right.pack(side="right")

        self.draw_circular_hud()
        self.update_clock()
        self.after(500, self.good_morning)
        self.after(60000, self.keep_alive)

    def on_close(self):
        if self._is_closing:
            return
        result = messagebox.askyesnocancel("JARVIS SHILATECH v0.1.10.1", "Close JARVIS Iron HUD?\n\nYes = Quit\nNo = Minimize to taskbar\nCancel = Stay open")
        if result is True:
            self._is_closing = True
            if logging:
                logging.info("User closed Iron HUD")
            self.destroy()
        elif result is False:
            self.iconify()
        else:
            pass

    def keep_alive(self):
        try:
            if not self._is_closing:
                self._arc_power = max(85, min(100, self._arc_power + (0.5 - 0.5) * 0.1))
                self.after(60000, self.keep_alive)
        except:
            pass

    def update_clock(self):
        try:
            if not self._is_closing:
                now = datetime.now()
                self.time_top_label.config(text=now.strftime("%H:%M:%S %Y-%m-%d"))
                self.bottom_right.config(text=f"Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • IRON v0.1.10.1 • {now.strftime('%H:%M:%S')} • {now.strftime('%Y-%m-%d')}")
                self.after(1000, self.update_clock)
        except:
            pass

    def add_message(self, role, text):
        try:
            self.chat_box.insert("end", f"\n[{role.upper()}] {text}\n", role)
            self.chat_box.see("end")
        except:
            pass

    def good_morning(self):
        try:
            now = datetime.now()
            time_str = now.strftime("%I:%M %p")
            date_str = now.strftime("%A, %B %d, %Y")
            msg = f"Good morning, {self.user_name}, Sir. It's {time_str} on {date_str}. Arc reactor at {self._arc_power:.1f}%. Iron Man Circular HUD v0.1.10.1 online — 13 central, 72 ticks, 60 small segments, 24 blocks, 16 inner, 6-layer glow, voice auto-init. SHILATECH secure. I speak both online and offline."
            self.add_message("assistant", msg)
            self.after(1500, lambda: self.speak(msg))
        except Exception as e:
            if logging:
                logging.error(f"good_morning failed: {e}")

    def speak(self, text):
        # Speak without requiring Python voice packages. On Windows the MSI uses
        # built-in System.Speech first; pyttsx3/win32com are optional fallbacks.
        try:
            if not self.voice_enabled:
                return
            clean = str(text)[:700].replace("```", " ").replace("*", "").replace("#", "")
            clean = clean.replace("•", " ").replace("—", " ").replace("'@", " ").replace("@'", " ")

            def _speak():
                try:
                    ps_script = f'''
Add-Type -AssemblyName System.Speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.Rate = 0
$speak.Volume = 100
$text = @'
{clean}
'@
$speak.Speak($text)
'''
                    completed = subprocess.run(
                        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"],
                        input=ps_script,
                        text=True,
                        capture_output=True,
                        timeout=25,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    if completed.returncode == 0:
                        return
                    if logging:
                        logging.warning("PowerShell SAPI TTS returned %s: %s", completed.returncode, completed.stderr[:200])
                except Exception as e:
                    if logging:
                        logging.warning("PowerShell SAPI TTS unavailable: %s", e)

                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 180)
                    voices = engine.getProperty('voices')
                    for v in voices:
                        name = getattr(v, 'name', '').lower()
                        vid = getattr(v, 'id', '').lower()
                        if 'british' in name or 'uk' in name or 'english' in vid:
                            engine.setProperty('voice', v.id)
                            break
                    engine.say(clean[:500])
                    engine.runAndWait()
                    return
                except Exception as e:
                    if logging:
                        logging.warning("pyttsx3 TTS unavailable: %s", e)

                try:
                    import win32com.client
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    speaker.Speak(clean[:500])
                except Exception as e:
                    if logging:
                        logging.warning("win32com SAPI TTS unavailable: %s", e)

            threading.Thread(target=_speak, daemon=True).start()
        except Exception as e:
            if logging:
                logging.error("speak failed: %s", e)

    def test_voice(self):
        self.add_message("system", "🔊 Voice test triggered from the visible function dock. If Windows audio is enabled you should hear JARVIS now.")
        self.speak("Voice online, Sir. This build has visible microphone, voice, tools, doctor, and clap wake controls.")

    def toggle_voice(self):
        self.voice_enabled = not self.voice_enabled
        status = f"Voice {'ON 🔊' if self.voice_enabled else 'OFF 🔇'} — Iron HUD v0.1.10.1 speaks using Windows built-in SAPI or pyttsx3."
        self.add_message("system", status)
        if hasattr(self, 'voice_button'):
            self.voice_button.config(
                text="🔊 VOICE ON" if self.voice_enabled else "🔇 VOICE OFF",
                bg="#022c22" if self.voice_enabled else "#1f2937",
                fg="#22c55e" if self.voice_enabled else "#94a3b8",
            )
        if self.voice_enabled:
            self.speak("Voice enabled, Sir. Iron Man HUD online, SHILATECH secure.")

    def voice_input(self):
        self.add_message("system", "🎤 Mic listen started — speak clearly for up to 7 seconds. If Windows speech recognition is unavailable, type in chat instead.")
        self.input_entry.focus()

        def worker():
            recognized = ""
            error = ""
            try:
                ps_script = r'''
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$recognizer = $null
foreach ($cultureName in @('en-US','en-GB')) {
  try {
    $culture = [System.Globalization.CultureInfo]::GetCultureInfo($cultureName)
    $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
    break
  } catch { }
}
if ($null -eq $recognizer) { $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine }
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$recognizer.LoadGrammar($grammar)
$recognizer.SetInputToDefaultAudioDevice()
$result = $recognizer.Recognize([TimeSpan]::FromSeconds(7))
if ($null -ne $result) { Write-Output $result.Text }
$recognizer.Dispose()
'''
                completed = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"],
                    input=ps_script,
                    text=True,
                    capture_output=True,
                    timeout=15,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                recognized = (completed.stdout or "").strip()
                error = (completed.stderr or "").strip()
            except Exception as e:
                error = str(e)

            if not recognized:
                try:
                    from jarvis.speech.voice_io import VoiceIO
                    vio = VoiceIO()
                    recognized = vio.listen(timeout=5, phrase_time_limit=5) or ""
                except Exception as e:
                    if not error:
                        error = str(e)

            if recognized:
                self.after(0, lambda: self.add_message("system", f"🎤 Heard: {recognized}"))
                self.after(0, lambda: self.send_prompt(recognized))
            else:
                msg = "No speech was recognized. Check microphone privacy permissions, then try 🎤 again or type your prompt."
                if error:
                    msg += f"\nDetail: {error[:220]}"
                self.after(0, lambda: self.add_message("system", msg))

        threading.Thread(target=worker, daemon=True).start()

    def _set_clap_button(self):
        if hasattr(self, 'clap_button'):
            self.clap_button.config(
                text="👏 CLAP ON" if self.clap_enabled else "👏 CLAP WAKE",
                bg="#b45309" if self.clap_enabled else "#92400e",
                fg="#fff7ed" if self.clap_enabled else "#e0f2fe",
            )

    def toggle_clap_wake(self):
        self.clap_enabled = not getattr(self, 'clap_enabled', False)
        self._set_clap_button()
        if self.clap_enabled:
            self.add_message("system", "👏 Clap wake enabled — listening for a loud double clap. This is now visible in the function dock, not hidden in chat.")
            self.speak("Clap wake enabled, Sir.")
            threading.Thread(target=self._clap_monitor, daemon=True).start()
        else:
            self.add_message("system", "👏 Clap wake disabled.")

    def _clap_monitor(self):
        try:
            import numpy as np
            import sounddevice as sd
        except Exception as e:
            self.clap_enabled = False
            self.after(0, self._set_clap_button)
            self.after(0, lambda: self.add_message("system", f"👏 Clap wake button is available, but live clap detection needs the sounddevice/numpy audio modules bundled or installed. Detail: {e}"))
            return

        last_hit = 0.0
        hits = []
        samplerate = 16000
        block = int(samplerate * 0.20)
        try:
            with sd.InputStream(channels=1, samplerate=samplerate, blocksize=block, dtype='float32') as stream:
                while getattr(self, 'clap_enabled', False) and not getattr(self, '_is_closing', False):
                    data, _overflowed = stream.read(block)
                    peak = float(np.max(np.abs(data))) if data is not None else 0.0
                    now = time.time()
                    if peak > 0.45 and now - last_hit > 0.25:
                        hits = [t for t in hits if now - t < 1.2]
                        hits.append(now)
                        last_hit = now
                        if len(hits) >= 2:
                            hits.clear()
                            self.after(0, lambda p=peak: self._on_clap_detected(p))
                    time.sleep(0.03)
        except Exception as e:
            self.clap_enabled = False
            self.after(0, self._set_clap_button)
            self.after(0, lambda: self.add_message("system", f"👏 Clap monitor stopped: {e}. Check microphone permissions, Sir."))

    def _on_clap_detected(self, peak):
        self.add_message("system", f"👏 Double clap detected (peak {peak:.2f}) — JARVIS awake. Ask a question or press 🎤.")
        self.speak("Yes, Sir. JARVIS is awake.")
        try:
            self.deiconify()
            self.lift()
            self.input_entry.focus()
        except Exception:
            pass

    def show_tools(self):
        tools = ["voice", "mic_listen", "clap_wake", "chat", "doctor", "network_status", "hybrid_mode", "ironman_agent", "memory", "search_tools", "device_tools", "startup_tools"]
        try:
            from jarvis.tools.registry import list_tools
            registered = list_tools()
            if registered:
                tools = registered[:24]
        except Exception:
            pass
        self.add_message("system", "🧰 Available functions are visible now — not only chat:\n" + "\n".join(f"• {tool}" for tool in tools))

    def run_doctor(self):
        checks = [
            f"Python: {sys.version.split()[0]}",
            f"Frozen MSI EXE: {getattr(sys, 'frozen', False)}",
            f"JARVIS core import: {HAS_JARVIS}",
            "Voice: Windows System.Speech fallback enabled",
            f"Clap wake: {'enabled' if getattr(self, 'clap_enabled', False) else 'available'}",
            f"Screen fit: compact={self.compact}, canvas={self.canvas_size}px",
        ]
        self.add_message("system", "🩺 JARVIS Doctor\n" + "\n".join(f"• {c}" for c in checks))

    def send_prompt(self, prompt=None):
        try:
            if prompt is None:
                prompt = self.input_var.get().strip()
                self.input_var.set("")
            if not prompt:
                return
            self.add_message("user", prompt)
            if HAS_JARVIS:
                try:
                    cfg = JarvisConfig.load()
                    cfg.engine.type = EngineType.MOCK
                    agent = get_agent("simple", config=cfg)
                    resp = agent.run(prompt, context="")
                    self.add_message("assistant", resp.content)
                    self.speak(resp.content[:400])
                except Exception as e:
                    self.add_message("assistant", f"Mock response: You said '{prompt}'. JARVIS Iron HUD v0.1.10.1 online, Sir. SHILATECH secure. (Error: {e})")
            else:
                self.add_message("assistant", f"You said: {prompt}\n\nJARVIS Iron Man Circular HUD v0.1.10.1 — central blue ring 13, 72 ticks with numbers, 60 small rectangular segments outer, 24 larger blocks middle, 16 inner opposite, 6-layer glow, 3 prongs Iron HUD with glow and circles, core pulsing 28±4, 8 data points, Trash 44 items 248.95 MB, weather 56°F Nairobi, SHILATECH secure. Voice speaks both online and offline, Sir.")
                self.speak(f"You said {prompt}. Iron HUD v0.1.10.1 online.")
        except Exception as e:
            self.add_message("system", f"Error: {e}\n{traceback.format_exc()[:500]}")

    def draw_circular_hud(self):
        try:
            if getattr(self, '_is_closing', False):
                return
            self.canvas.delete("all")
            cx = cy = self.canvas_size // 2
            rot = self._rot
            base = min(240, max(130, self.canvas_size // 2 - 40))

            self.canvas.create_rectangle(0, 0, self.canvas_size, self.canvas_size, fill="#020208", outline="")
            for i in range(0, self.canvas_size, 40):
                self.canvas.create_line(i, 0, i, self.canvas_size, fill="#0a0a0f", width=1)
                self.canvas.create_line(0, i, self.canvas_size, i, fill="#0a0a0f", width=1)

            self.canvas.create_oval(cx-base-30, cy-base-30, cx+base+30, cy+base+30, outline="#1e293b", width=3)
            self.canvas.create_oval(cx-base-20, cy-base-20, cx+base+20, cy+base+20, outline="#334155", width=1)
            self.canvas.create_oval(cx-base-12, cy-base-12, cx+base+12, cy+base+12, outline="#0e7490", width=1)

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
                    rx = cx + math.cos(angle) * (r2 + 12)
                    ry = cy + math.sin(angle) * (r2 + 12)
                    self.canvas.create_text(rx, ry, text=str(i), fill="#334155", font=("JetBrains Mono", 6))

            for i in range(60):
                angle = (i / 60) * 2 * math.pi + rot * 0.01
                r = base - 8
                seg_w = 4
                x1 = cx + math.cos(angle) * (r - seg_w)
                y1 = cy + math.sin(angle) * (r - seg_w)
                x2 = cx + math.cos(angle) * (r + seg_w)
                y2 = cy + math.sin(angle) * (r + seg_w)
                alpha = 0.3 + 0.7 * (math.sin(rot*0.05 + i*0.2) * 0.5 + 0.5)
                color = "#0891b2" if i % 3 == 0 else "#0e7490"
                if alpha > 0.6:
                    self.canvas.create_line(x1, y1, x2, y2, fill=color, width=2)

            for i in range(24):
                angle = (i / 24) * 2 * math.pi + rot * 0.015
                seg_len = 0.18
                r = base - 28
                x1 = cx + math.cos(angle) * r
                y1 = cy + math.sin(angle) * r
                x2 = cx + math.cos(angle + seg_len) * r
                y2 = cy + math.sin(angle + seg_len) * r
                color = "#22d3ee" if i % 4 == 0 else "#0e7490" if i % 2 == 0 else "#1e3a5f"
                width = 4 if i % 4 == 0 else 2
                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width)
                self.canvas.create_oval(x2-1, y2-1, x2+1, y2+1, fill=color, outline="")

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

            for glow in range(6):
                r = base - 70 - glow*1.5
                self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#22d3ee", width=1)
            self.canvas.create_oval(cx-base+70, cy-base+70, cx+base-70, cy+base-70, outline="#22d3ee", width=3)
            self.canvas.create_oval(cx-base+75, cy-base+75, cx+base-75, cy+base-75, outline="#7dd3fc", width=1, dash=(2,4))

            for i in range(3):
                angle = (i / 3) * 2 * math.pi + rot * 0.05
                r1 = 35
                r2 = base - 85
                x1 = cx + math.cos(angle) * r1
                y1 = cy + math.sin(angle) * r1
                x2 = cx + math.cos(angle) * r2
                y2 = cy + math.sin(angle) * r2
                self.canvas.create_line(x1, y1, x2, y2, fill="#0e7490", width=6)
                self.canvas.create_line(x1, y1, x2, y2, fill="#22d3ee", width=3)
                self.canvas.create_line(x1, y1, x2, y2, fill="#ffffff", width=1)
                self.canvas.create_oval(x2-4, y2-4, x2+4, y2+4, fill="#22d3ee", outline="#ffffff", width=1)
                mid_r = (r1 + r2) / 2
                mx = cx + math.cos(angle) * mid_r
                my = cy + math.sin(angle) * mid_r
                self.canvas.create_oval(mx-2, my-2, mx+2, my+2, fill="#7dd3fc", outline="")

            for i in range(6):
                angle = (i / 6) * 2 * math.pi + rot * 0.03
                r1 = base - 70
                r2 = base - 55
                x1 = cx + math.cos(angle) * r1
                y1 = cy + math.sin(angle) * r1
                x2 = cx + math.cos(angle) * r2
                y2 = cy + math.sin(angle) * r2
                self.canvas.create_line(x1, y1, x2, y2, fill="#334155", width=1)

            pulse = 28 + math.sin(rot * 0.08) * 4
            for g in range(4):
                r = pulse + g*3
                self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#22d3ee", width=1)
            self.canvas.create_oval(cx-pulse, cy-pulse, cx+pulse, cy+pulse, fill="#22d3ee", outline="#7dd3fc", width=2)
            self.canvas.create_oval(cx-12, cy-12, cx+12, cy+12, fill="white", outline="#22d3ee", width=1)
            self.canvas.create_oval(cx-6, cy-6, cx+6, cy+6, fill="#7dd3fc", outline="")
            self.canvas.create_text(cx, cy, text="13", fill="black", font=("JetBrains Mono", 12, "bold"))

            self.canvas.create_oval(cx-45, cy-45, cx+45, cy+45, outline="#e2e8f0", width=1)
            self.canvas.create_oval(cx-55, cy-55, cx+55, cy+55, outline="#334155", width=1, dash=(3,3))
            self.canvas.create_oval(cx-35, cy-35, cx+35, cy+35, outline="#0e7490", width=1)

            for i in range(8):
                angle = (i / 8) * 2 * math.pi + rot * 0.02
                r = base - 120
                x = cx + math.cos(angle) * r
                y = cy + math.sin(angle) * r
                color = "#22d3ee" if i % 2 == 0 else "#7dd3fc"
                size = 3 if i % 2 == 0 else 2
                self.canvas.create_oval(x-size, y-size, x+size, y+size, fill=color, outline="")
                x2 = cx + math.cos(angle) * (r + 8)
                y2 = cy + math.sin(angle) * (r + 8)
                self.canvas.create_line(x, y, x2, y2, fill="#334155", width=1)

            self.canvas.create_text(70, 60, text="99% - Strength", fill="#22d3ee", font=("JetBrains Mono", 8, "bold"), anchor="w")
            self.canvas.create_text(70, 75, text="Home WiFi - Source", fill="#64748b", font=("JetBrains Mono", 7), anchor="w")
            self.canvas.create_text(70, 95, text="Jarvis list", fill="#475569", font=("JetBrains Mono", 7), anchor="w")
            self.canvas.create_text(70, 110, text="• backup themes\n• backup control\n• warning control\n• system diagnostics\n• network status", fill="#334155", font=("JetBrains Mono", 6), justify="left", anchor="w")
            self.canvas.create_text(70, 170, text="SYSTEM • ONLINE\nEngine: OLLAMA\nMode: IRON v0.1.10.1\nLatency: 33ms\nSHILATECH SECURE", fill="#0e7490", font=("JetBrains Mono", 6), justify="left", anchor="w")

            self.canvas.create_text(self.canvas_size-70, 60, text="WEATHER • NAIROBI", fill="#0e7490", font=("JetBrains Mono", 7), anchor="e")
            self.canvas.create_text(self.canvas_size-70, 80, text="56°F", fill="#7dd3fc", font=("JetBrains Mono", 16, "bold"), anchor="e")
            self.canvas.create_text(self.canvas_size-70, 95, text="Partly Cloudy", fill="#cbd5e1", font=("JetBrains Mono", 8), anchor="e")
            self.canvas.create_text(self.canvas_size-70, 108, text="High 74° • Low 60°", fill="#64748b", font=("JetBrains Mono", 7), anchor="e")
            self.canvas.create_text(self.canvas_size-70, 125, text="Precipitation: 10%\nHumidity: 65%\nWind: 5 mph\nSHILATECH v0.1.10.1", fill="#475569", font=("JetBrains Mono", 6), justify="right", anchor="e")

            self.canvas.create_text(cx, self.canvas_size-20, text="Trash - 44 items • Size - 248.95 MB • Source - AC Line • Power - 90% • IRON v0.1.10.1 • ONLINE SECURE • ENCRYPTED • 33ms • SHILATECH", fill="#334155", font=("JetBrains Mono", 7))

            self._rot += 1
            if not self._is_closing:
                self.after(50, self.draw_circular_hud)
        except Exception as e:
            if logging:
                logging.error(f"draw_circular_hud failed: {e} {traceback.format_exc()}")
            if not self._is_closing:
                self.after(100, self.draw_circular_hud)

def main():
    try:
        app = ModernCircularHUDApp()
        app.update_idletasks()
        w = app.winfo_width()
        h = app.winfo_height()
        x = (app.winfo_screenwidth() // 2) - (w // 2)
        y = (app.winfo_screenheight() // 2) - (h // 2)
        app.geometry(f"{w}x{h}+{x}+{y}")
        app.mainloop()
    except Exception as e:
        print(f"Failed to start Iron HUD: {e}\n{traceback.format_exc()}")
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("JARVIS Iron HUD Error", f"Failed to start Iron HUD v0.1.10.1:\n{e}\n\n{traceback.format_exc()[:1000]}\n\nTry python app.py")
            root.destroy()
        except:
            pass
        input("Press Enter to exit... SHILATECH Iron HUD v0.1.10.1")

if __name__ == "__main__":
    main()
