"""JARVIS Daemon — runs on boot, says Good Morning Eugene, aligns tasks, stays in system tray.

This is the always-on JARVIS like Iron Man movie:
- Starts on boot via autostart
- Says Good Morning Eugene with TTS
- Shows notification with today's MITs
- Stays in system tray
- Global hotkey: Ctrl+Shift+J to summon HUD
- Periodic check-ins for ADHD

Usage:
  python -m jarvis.startup.daemon --mode ironman --name Eugene
  jarvis daemon --mode hud --name Eugene
"""

from __future__ import annotations

import os
import sys
import time
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from jarvis.core.config import get_home


class JARVISDaemon:
    def __init__(self, mode: str = "ironman", user_name: str = "Eugene", engine: str = "mock", voice: bool = True):
        self.mode = mode
        self.user_name = user_name
        self.engine = engine
        self.voice_enabled = voice
        self.home = get_home()
        self.running = False
        self.tray_icon = None

    def start(self):
        """Start daemon — Good Morning + system tray + hotkey."""
        self.running = True
        
        print(f"JARVIS Daemon starting — Mode: {self.mode}, User: {self.user_name}, Voice: {self.voice_enabled}")
        
        # 1. Morning greeting with TTS
        self.morning_greeting()
        
        # 2. System tray (if available)
        try:
            self.start_tray()
        except Exception as e:
            print(f"Tray not available: {e}, running without tray")
            # Fallback: just keep running and do periodic check-ins
            self.run_loop()

    def morning_greeting(self):
        """Good morning Eugene with tasks, plus TTS and notification."""
        try:
            from jarvis.startup.greeting import get_greeting
            g = get_greeting(self.user_name)
            greeting_text = g.get_greeting()
            
            print("\n" + "="*60)
            print(greeting_text)
            print("="*60 + "\n")
            
            # TTS if enabled
            if self.voice_enabled:
                try:
                    self.speak_greeting(greeting_text)
                except Exception as e:
                    print(f"TTS failed: {e}")
            
            # Desktop notification
            try:
                self.show_notification(f"Good morning, {self.user_name}", self._extract_mits_summary(greeting_text))
            except Exception as e:
                print(f"Notification failed: {e}")
                
        except Exception as e:
            print(f"Greeting failed: {e}")
            # Fallback
            now = datetime.now()
            print(f"Good morning, {self.user_name}. It's {now.strftime('%I:%M %p')}. All systems nominal, Sir.")

    def _extract_mits_summary(self, greeting: str) -> str:
        """Extract MITs for notification."""
        lines = greeting.split("\n")
        mits = []
        in_mits = False
        for line in lines:
            if "MITs" in line or "Alignment" in line:
                in_mits = True
                continue
            if in_mits and line.strip() and line[0].isdigit():
                mits.append(line.strip())
                if len(mits) >= 3:
                    break
            if in_mits and "Schedule" in line:
                break
        
        if mits:
            return "Today's MITs:\n" + "\n".join(mits[:3])
        return "Ready for tasks, Sir."

    def speak_greeting(self, text: str):
        """Speak greeting with TTS."""
        # Short version for TTS (first 2 lines)
        short_text = ". ".join(text.split(".")[:3]) + "."
        short_text = short_text[:300]  # Limit for TTS
        
        try:
            # Try kokoro (best quality)
            from jarvis.speech.voice_io import VoiceIO
            vio = VoiceIO()
            vio.speak(short_text)
            return
        except:
            pass
        
        try:
            # Try pyttsx3
            import pyttsx3
            engine = pyttsx3.init()
            # Try to set British voice
            voices = engine.getProperty('voices')
            for voice in voices:
                if 'british' in voice.name.lower() or 'english' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
            engine.setProperty('rate', 180)
            engine.say(short_text)
            engine.runAndWait()
            return
        except:
            pass
        
        try:
            # Try espeak (Linux)
            import subprocess
            subprocess.run(["espeak", "-v", "en", short_text], timeout=10)
            return
        except:
            pass
        
        print("No TTS available, install: pip install pyttsx3 or kokoro")

    def show_notification(self, title: str, message: str):
        """Show desktop notification."""
        system = os.name
        try:
            # Try plyer (cross-platform)
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="JARVIS",
                timeout=10
            )
            return
        except:
            pass
        
        try:
            # Linux notify-send
            import subprocess
            subprocess.run(["notify-send", title, message, "-i", "utilities-terminal", "-t", "10000"], timeout=5)
            return
        except:
            pass
        
        try:
            # Windows via win10toast or powershell
            import subprocess
            ps_cmd = f'Add-Type -AssemblyName System.Windows.Forms; $n = New-Object System.Windows.Forms.NotifyIcon; $n.Icon = [System.Drawing.SystemIcons]::Information; $n.BalloonTipTitle = "{title}"; $n.BalloonTipText = "{message}"; $n.Visible = $true; $n.ShowBalloonTip(10000)'
            subprocess.run(["powershell", "-Command", ps_cmd], timeout=5)
            return
        except:
            pass

    def start_tray(self):
        """Start system tray icon."""
        try:
            import pystray
            from PIL import Image, ImageDraw
            
            # Create icon image (arc reactor style)
            def create_icon():
                size = 64
                img = Image.new('RGBA', (size, size), (0,0,0,0))
                draw = ImageDraw.Draw(img)
                # Outer glow
                draw.ellipse([2,2,size-2,size-2], fill=(34,197,94,100), outline=(34,197,94,255), width=2)
                # Inner
                draw.ellipse([16,16,size-16,size-16], fill=(34,197,94,200), outline=(255,255,255,255), width=1)
                draw.ellipse([26,26,size-26,size-26], fill=(255,255,255,230))
                return img
            
            icon_image = create_icon()
            
            def on_clicked(icon, item):
                action = str(item)
                if "Show HUD" in action:
                    self.show_hud()
                elif "Good Morning" in action:
                    self.morning_greeting()
                elif "Tasks" in action:
                    self.show_tasks()
                elif "Focus" in action:
                    self.start_focus()
                elif "Quit" in action:
                    icon.stop()
                    self.running = False
                    os._exit(0)
            
            menu = pystray.Menu(
                pystray.MenuItem(f"Good Morning, {self.user_name}", on_clicked),
                pystray.MenuItem("Show Iron Man HUD", on_clicked),
                pystray.MenuItem("Today's Tasks", on_clicked),
                pystray.MenuItem("Focus 25m", on_clicked),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit JARVIS", on_clicked)
            )
            
            self.tray_icon = pystray.Icon("JARVIS", icon_image, f"JARVIS — {self.user_name}", menu)
            
            # Run tray in separate thread
            tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            tray_thread.start()
            
            print("System tray started — JARVIS in tray, Sir.")
            self.run_loop()
            
        except ImportError as e:
            print(f"pystray/Pillow not available: {e}, install: pip install pystray Pillow")
            self.run_loop()
        except Exception as e:
            print(f"Tray failed: {e}")
            self.run_loop()

    def run_loop(self):
        """Main loop — periodic check-ins for ADHD."""
        print("JARVIS daemon running — periodic check-ins enabled")
        
        last_check = time.time()
        check_interval = 60 * 25  # 25 min Pomodoro check-in
        
        try:
            while self.running:
                time.sleep(1)
                
                # Periodic ADHD check-in every 25 min
                if time.time() - last_check > check_interval:
                    last_check = time.time()
                    self.adhd_checkin()
                    
        except KeyboardInterrupt:
            print("\nJARVIS daemon shutting down, Sir.")
            self.running = False

    def adhd_checkin(self):
        """ADHD check-in — gentle nudge."""
        messages = [
            f"Check-in, {self.user_name}. How's MIT 1 going? Need breakdown?",
            f"25 min passed, Sir. Water? Break? Log win?",
            f"Still with me, {self.user_name}? 2 more min counts.",
            f"Body double check-in: How's focus? Need dopamine menu?",
        ]
        import random
        msg = random.choice(messages)
        print(f"\n[JARVIS Check-in] {msg}\n")
        try:
            self.show_notification(f"JARVIS Check-in", msg)
        except:
            pass

    def show_hud(self):
        """Show Iron Man HUD."""
        try:
            # Try to open frontend
            import webbrowser
            webbrowser.open("http://localhost:5173")
            print("Opened HUD at http://localhost:5173 — run 'jarvis serve' if not running")
        except:
            pass
        
        # Also try desktop GUI
        try:
            import subprocess
            subprocess.Popen([sys.executable, "app.py"], cwd=str(Path(__file__).parent.parent.parent.parent))
        except Exception as e:
            print(f"Failed to show HUD: {e}")

    def show_tasks(self):
        """Show today's tasks."""
        try:
            from jarvis.startup.greeting import get_greeting
            g = get_greeting(self.user_name)
            print(g._get_tasks_alignment())
        except Exception as e:
            print(f"Failed to show tasks: {e}")

    def start_focus(self):
        """Start focus session."""
        try:
            from jarvis.tools.registry import get_tool
            tool = get_tool("focus")
            if tool:
                print(tool.run(task="MIT 1", duration=25))
            else:
                print("Focus tool not available")
        except Exception as e:
            print(f"Focus failed: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="JARVIS Daemon — Autostart + Good Morning Eugene + System Tray")
    parser.add_argument("--mode", default="ironman", help="Mode: ironman, adhd, hud, gui, server")
    parser.add_argument("--name", default="Eugene", help="User name")
    parser.add_argument("--engine", default="mock", help="Engine: mock, ollama, openai")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice greeting")
    args = parser.parse_args()

    daemon = JARVISDaemon(mode=args.mode, user_name=args.name, engine=args.engine, voice=not args.no_voice)
    daemon.start()


if __name__ == "__main__":
    main()
