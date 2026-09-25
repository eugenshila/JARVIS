"""JARVIS Desktop GUI — Standalone executable that stays open.

This is built with PyInstaller --windowed so it doesn't need console and stays open.
Uses Tkinter which is included in standard Python.
"""

import sys
import os
from pathlib import Path
import traceback

# Ensure we can find modules
ROOT = Path(__file__).parent.parent.parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main():
    try:
        # Try to run the enhanced app.py
        print("Starting JARVIS Desktop...")
        
        # Check Tkinter
        try:
            import tkinter as tk
            print(f"Tkinter available: {tk.TkVersion}")
        except ImportError as e:
            # Show error in messagebox if possible, else console
            error_msg = f"Tkinter not available: {e}\n\nOn Windows, reinstall Python from python.org and check 'tcl/tk and IDLE'.\nOn Linux: sudo apt install python3-tk"
            print(error_msg)
            try:
                import tkinter.messagebox as mb
                mb.showerror("JARVIS - Tkinter Missing", error_msg)
            except:
                pass
            input("Press Enter to exit...")
            return

        # Import and run app
        try:
            import app
            print("Launching app.py...")
            app.main()
        except ImportError:
            # Fallback: try src layout
            from jarvis.core.config import JarvisConfig
            from jarvis.agents.registry import get_agent, list_agents
            from jarvis.engine.registry import list_engines
            from jarvis.core.types import EngineType
            
            # Simple fallback GUI if app.py not found
            import tkinter as tk
            from tkinter import ttk, messagebox
            
            root = tk.Tk()
            root.title("JARVIS - Personal AI")
            root.geometry("900x600")
            root.configure(bg="#0f172a")
            
            # Simple UI
            tk.Label(root, text="JARVIS", bg="#0f172a", fg="#22c55e", font=("Segoe UI", 24, "bold")).pack(pady=20)
            tk.Label(root, text="Personal AI, On Personal Devices", bg="#0f172a", fg="#94a3b8").pack()
            
            frame = tk.Frame(root, bg="#0f172a", padx=20, pady=20)
            frame.pack(fill="both", expand=True)
            
            tk.Label(frame, text="Prompt:", bg="#0f172a", fg="white").pack(anchor="w")
            prompt_box = tk.Text(frame, height=5, bg="#1e293b", fg="white")
            prompt_box.pack(fill="x", pady=5)
            prompt_box.insert("1.0", "Hello, what can you do? Explain JARVIS in 2 sentences.")
            
            tk.Label(frame, text="Response:", bg="#0f172a", fg="white").pack(anchor="w", pady=(10,0))
            response_box = tk.Text(frame, height=15, bg="#1e293b", fg="white")
            response_box.pack(fill="both", expand=True, pady=5)
            
            def generate():
                prompt = prompt_box.get("1.0", "end").strip()
                if not prompt:
                    return
                response_box.delete("1.0", "end")
                response_box.insert("1.0", "Generating with mock engine (offline)...\n\n")
                try:
                    cfg = JarvisConfig.load()
                    cfg.engine.type = EngineType.MOCK
                    agent = get_agent("simple", config=cfg)
                    resp = agent.run(prompt, context="")
                    response_box.delete("1.0", "end")
                    response_box.insert("1.0", resp.content)
                except Exception as e:
                    response_box.delete("1.0", "end")
                    response_box.insert("1.0", f"Error: {e}\n\n{traceback.format_exc()}")
            
            ttk.Button(frame, text="Generate (Offline Mock)", command=generate).pack(pady=10)
            ttk.Button(frame, text="Doctor", command=lambda: messagebox.showinfo("Doctor", f"Engines: {list_engines()}\nAgents: {list_agents()}")).pack()
            
            tk.Label(root, text="Offline mode: mock engine works without internet or API key", bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 9)).pack(pady=5)
            
            root.mainloop()
            
    except Exception as e:
        error = f"Failed to start JARVIS Desktop:\n{e}\n\n{traceback.format_exc()}"
        print(error)
        try:
            import tkinter.messagebox as mb
            mb.showerror("JARVIS Error", error)
        except:
            pass
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
