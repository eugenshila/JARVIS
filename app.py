"""JARVIS Desktop — Enhanced GUI with full OpenJarvis stack support.

Run with: python app.py
No external packages required for basic mode, but enhanced features use the jarvis package.
"""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import sys
import os

# Ensure src is on path
ROOT = Path(__file__).parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from prompts import load_prompts, STARTER, BUILTIN_PROMPTS

try:
    from jarvis.core.config import JarvisConfig, PRESETS
    from jarvis.agents.registry import get_agent, list_agents
    from jarvis.engine.registry import list_engines
    from jarvis.core.types import EngineType
    HAS_JARVIS = True
except ImportError:
    HAS_JARVIS = False
    JarvisConfig = None

# Fallback client
try:
    from client import generate as legacy_generate
except ImportError:
    legacy_generate = None


class Jarvis(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JARVIS · Personal AI, On Personal Devices")
        self.geometry("1180x800")
        self.minsize(800, 600)
        self.configure(bg="#0f172a")

        # Config
        self.config_obj = JarvisConfig.load() if HAS_JARVIS else None
        self.prompts = {**BUILTIN_PROMPTS, **load_prompts(Path("__starter_only__"))}
        self.selection = tk.StringVar(value="Meeting brief (starter)")
        self.agent_var = tk.StringVar(value=self.config_obj.preset if self.config_obj else "chat-simple")
        self.engine_var = tk.StringVar(value=self.config_obj.engine.type.value if self.config_obj else "openai")
        self.model_var = tk.StringVar(value=self.config_obj.engine.model if self.config_obj else "gpt-4o-mini")
        self.status = tk.StringVar(value="Ready · Local-first Personal AI · Paste details to begin")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", padding=8, font=("Segoe UI", 9))
        style.configure("TCombobox", padding=5)
        style.configure("Accent.TButton", background="#22c55e")

        self._build_ui()
        self.show_prompt()

    def _build_ui(self):
        # Top bar
        top = tk.Frame(self, bg="#0f172a", padx=18, pady=12)
        top.pack(fill="x")
        tk.Label(top, text="JARVIS", bg="#0f172a", fg="#22c55e", font=("Segoe UI", 22, "bold")).pack(side="left")
        tk.Label(top, text="Personal AI, On Personal Devices", bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 10)).pack(side="left", padx=(12,0), pady=(6,0))

        right_top = tk.Frame(top, bg="#0f172a")
        right_top.pack(side="right")
        ttk.Button(right_top, text="Open prompt folder", command=self.open_folder).pack(side="left", padx=4)
        ttk.Button(right_top, text="Doctor", command=self.run_doctor).pack(side="left", padx=4)
        ttk.Button(right_top, text="Server", command=self.start_server).pack(side="left", padx=4)

        # Controls row
        ctrl = tk.Frame(self, bg="#0f172a", padx=18, pady=4)
        ctrl.pack(fill="x")

        tk.Label(ctrl, text="Agent:", bg="#0f172a", fg="white", font=("Segoe UI", 9)).pack(side="left")
        agents = list_agents() if HAS_JARVIS else ["chat-simple", "meeting-brief"]
        self.agent_combo = ttk.Combobox(ctrl, textvariable=self.agent_var, values=agents, state="readonly", width=18)
        self.agent_combo.pack(side="left", padx=(6,12))

        tk.Label(ctrl, text="Engine:", bg="#0f172a", fg="white").pack(side="left")
        engines = list_engines() if HAS_JARVIS else ["openai", "mock"]
        self.engine_combo = ttk.Combobox(ctrl, textvariable=self.engine_var, values=engines, state="readonly", width=12)
        self.engine_combo.pack(side="left", padx=(6,12))

        tk.Label(ctrl, text="Model:", bg="#0f172a", fg="white").pack(side="left")
        self.model_entry = ttk.Entry(ctrl, textvariable=self.model_var, width=22)
        self.model_entry.pack(side="left", padx=(6,12))

        tk.Label(ctrl, text="Prompt:", bg="#0f172a", fg="white").pack(side="left", padx=(12,6))
        self.picker = ttk.Combobox(ctrl, textvariable=self.selection, values=list(self.prompts), state="readonly", width=28)
        self.picker.pack(side="left", fill="x", expand=True)
        self.picker.bind("<<ComboboxSelected>>", lambda _: self.show_prompt())

        # Main panes
        panes = tk.PanedWindow(self, orient="horizontal", bg="#0f172a", sashwidth=6)
        panes.pack(fill="both", expand=True, padx=18, pady=8)

        left = tk.Frame(panes, bg="#0f172a")
        right = tk.Frame(panes, bg="#0f172a")
        panes.add(left, minsize=350)
        panes.add(right, minsize=350)

        self.prompt_box = self.editor(left, "Prompt / Skill (editable)", height=10)
        self.context_box = self.editor(left, "Meeting details / Task context / Files", height=14)
        self.output_box = self.editor(right, "Response · Streaming output", height=28)

        # Actions
        actions = tk.Frame(self, bg="#0f172a", padx=18, pady=10)
        actions.pack(fill="x")

        self.run_button = ttk.Button(actions, text="▶ Generate", command=self.run, style="Accent.TButton")
        self.run_button.pack(side="left")

        ttk.Button(actions, text="Copy prompt+context", command=self.copy_prompt).pack(side="left", padx=8)
        ttk.Button(actions, text="Copy response", command=self.copy_response).pack(side="left")
        ttk.Button(actions, text="Clear", command=self.clear).pack(side="left", padx=8)
        ttk.Button(actions, text="Save to memory", command=self.save_memory).pack(side="left", padx=8)

        # Status
        tk.Label(self, textvariable=self.status, bg="#0f172a", fg="#94a3b8", anchor="w", padx=18, pady=6, font=("Segoe UI", 9)).pack(fill="x")

    def editor(self, parent, label, height):
        tk.Label(parent, text=label, bg="#0f172a", fg="#e2e8f0", anchor="w", font=("Segoe UI", 9, "bold")).pack(fill="x", pady=(0,4))
        box = tk.Text(parent, height=height, wrap="word", undo=True, bg="#1e293b", fg="#f1f5f9",
                      insertbackground="white", relief="flat", padx=12, pady=10, font=("Segoe UI", 10),
                      selectbackground="#334155")
        box.pack(fill="both", expand=True, pady=(0,12), padx=2)
        return box

    def open_folder(self):
        folder = filedialog.askdirectory(title="Select extracted prompt library folder")
        if folder:
            loaded = load_prompts(Path(folder))
            self.prompts.update(loaded)
            self.picker["values"] = list(self.prompts)
            self.selection.set(next(iter(self.prompts)))
            self.show_prompt()
            self.status.set(f"Loaded {len(loaded)} prompts from {folder}")

    def show_prompt(self):
        self.prompt_box.delete("1.0", "end")
        content = self.prompts.get(self.selection.get(), STARTER)
        self.prompt_box.insert("1.0", content)

    def input_text(self):
        return self.prompt_box.get("1.0", "end").strip(), self.context_box.get("1.0", "end").strip()

    def copy_prompt(self):
        prompt, context = self.input_text()
        self.clipboard_clear()
        self.clipboard_append(f"{prompt}\n\nContext:\n{context}")
        self.status.set("Prompt and context copied")

    def copy_response(self):
        self.clipboard_clear()
        self.clipboard_append(self.output_box.get("1.0", "end").strip())
        self.status.set("Response copied")

    def clear(self):
        self.context_box.delete("1.0", "end")
        self.output_box.delete("1.0", "end")
        self.status.set("Cleared")

    def save_memory(self):
        text = self.output_box.get("1.0", "end").strip() or self.context_box.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Empty", "Nothing to save to memory")
            return
        if HAS_JARVIS:
            try:
                from jarvis.memory.store import MemoryStore
                store = MemoryStore()
                entry = store.add(text[:2000])
                self.status.set(f"Saved to memory: {entry.id}")
                messagebox.showinfo("Memory", f"Saved {entry.id}")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        else:
            messagebox.showinfo("Memory", "Memory store not available (install jarvis package)")

    def run_doctor(self):
        if not HAS_JARVIS:
            messagebox.showinfo("Doctor", "Install jarvis package: pip install -e .")
            return
        import io
        from contextlib import redirect_stdout
        # Quick check
        cfg = JarvisConfig.load()
        has_key = bool(os.environ.get("OPENAI_API_KEY"))
        msg = (
            f"Home: {cfg.home}\n"
            f"Config: {cfg.config_path} ({'exists' if cfg.config_path.exists() else 'missing'})\n"
            f"Preset: {cfg.preset}\n"
            f"Engine: {cfg.engine.type.value} / {cfg.engine.model}\n"
            f"API Key: {'set' if has_key else 'not set (use mock)'}\n"
            f"Agents: {', '.join(list_agents())}\n"
        )
        messagebox.showinfo("JARVIS Doctor", msg)

    def start_server(self):
        def _run():
            try:
                import uvicorn
                uvicorn.run("jarvis.server.api:app", host="0.0.0.0", port=8000)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Server", str(e)))
        threading.Thread(target=_run, daemon=True).start()
        self.status.set("Server starting at http://localhost:8000 — docs at /docs")

    def run(self):
        prompt, context = self.input_text()
        if not prompt:
            messagebox.showwarning("Missing prompt", "Select or enter a prompt first.")
            return
        self.run_button.config(state="disabled")
        self.status.set(f"Generating with {self.agent_var.get()} via {self.engine_var.get()} ({self.model_var.get()})...")

        def worker():
            try:
                result = self._generate(prompt, context)
                self.after(0, lambda: self.complete(result, None))
            except Exception as error:
                self.after(0, lambda msg=str(error): self.complete(None, msg))

        threading.Thread(target=worker, daemon=True).start()

    def _generate(self, prompt: str, context: str) -> str:
        if HAS_JARVIS:
            cfg = JarvisConfig.load()
            # override from UI
            try:
                cfg.engine.type = EngineType(self.engine_var.get())
            except Exception:
                pass
            cfg.engine.model = self.model_var.get()
            cfg.preset = self.agent_var.get()
            agent = get_agent(self.agent_var.get(), config=cfg)
            resp = agent.run(prompt, context=context)
            return resp.content
        else:
            if legacy_generate:
                return legacy_generate(prompt, context)
            return f"[No engine] Prompt: {prompt}\nContext: {context}\n\nInstall package: pip install -e ."

    def complete(self, result, error):
        self.run_button.config(state="normal")
        if error:
            self.status.set(error)
            messagebox.showerror("JARVIS", error)
            return
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", result)
        self.status.set(f"Response ready · {len(result)} chars · Engine {self.engine_var.get()}")


def main():
    app = Jarvis()
    app.mainloop()


if __name__ == "__main__":
    main()
