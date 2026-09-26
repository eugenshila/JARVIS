"""Run with python app.py. No external packages required."""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from client import generate
from prompts import load_prompts


class Jarvis(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jarvis · Desktop assistant")
        self.geometry("1050x730")
        self.minsize(720, 540)
        self.configure(bg="#111827")
        self.prompts = load_prompts(Path("__starter_only__"))
        self.selection = tk.StringVar(value="Meeting brief (starter)")
        self.status = tk.StringVar(value="Ready · Paste meeting details to begin")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", padding=8)
        style.configure("TCombobox", padding=5)

        top = tk.Frame(self, bg="#111827", padx=18, pady=14)
        top.pack(fill="x")
        tk.Label(top, text="JARVIS", bg="#111827", fg="#75e0a7", font=("Segoe UI", 20, "bold")).pack(side="left")
        ttk.Button(top, text="Open prompt folder", command=self.open_folder).pack(side="right")
        tk.Label(self, text="Choose a prompt", bg="#111827", fg="white", anchor="w", padx=18).pack(fill="x")
        self.picker = ttk.Combobox(self, textvariable=self.selection, values=list(self.prompts), state="readonly")
        self.picker.pack(fill="x", padx=18, pady=(4, 14))
        self.picker.bind("<<ComboboxSelected>>", lambda _: self.show_prompt())

        panes = tk.PanedWindow(self, orient="horizontal", bg="#111827", sashwidth=7)
        panes.pack(fill="both", expand=True, padx=18)
        left = tk.Frame(panes, bg="#111827")
        right = tk.Frame(panes, bg="#111827")
        panes.add(left, minsize=300)
        panes.add(right, minsize=300)
        self.prompt_box = self.editor(left, "Prompt (editable)", height=11)
        self.context_box = self.editor(left, "Meeting details / task context", height=13)
        self.output_box = self.editor(right, "Response", height=28)
        self.show_prompt()

        actions = tk.Frame(self, bg="#111827", padx=18, pady=12)
        actions.pack(fill="x")
        self.run_button = ttk.Button(actions, text="Generate brief", command=self.run)
        self.run_button.pack(side="left")
        ttk.Button(actions, text="Copy prompt + context", command=self.copy_prompt).pack(side="left", padx=8)
        ttk.Button(actions, text="Copy response", command=self.copy_response).pack(side="left")
        tk.Label(self, textvariable=self.status, bg="#111827", fg="#a7b8c8", anchor="w", padx=18, pady=8).pack(fill="x")

    def editor(self, parent, label, height):
        tk.Label(parent, text=label, bg="#111827", fg="white", anchor="w").pack(fill="x", pady=(0, 4))
        box = tk.Text(parent, height=height, wrap="word", undo=True, bg="#1f2937", fg="#f3f4f6",
                      insertbackground="white", relief="flat", padx=12, pady=10, font=("Segoe UI", 10))
        box.pack(fill="both", expand=True, pady=(0, 14), padx=5)
        return box

    def open_folder(self):
        folder = filedialog.askdirectory(title="Select extracted prompt library folder")
        if folder:
            self.prompts = load_prompts(Path(folder))
            self.picker["values"] = list(self.prompts)
            self.selection.set(next(iter(self.prompts)))
            self.show_prompt()
            self.status.set(f"Loaded {len(self.prompts) - 1} prompts from {folder}")

    def show_prompt(self):
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", self.prompts[self.selection.get()])

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

    def run(self):
        prompt, context = self.input_text()
        if not prompt:
            messagebox.showwarning("Missing prompt", "Select or enter a prompt first.")
            return
        self.run_button.config(state="disabled")
        self.status.set("Generating response…")

        def worker():
            try:
                result = generate(prompt, context)
                self.after(0, lambda: self.complete(result, None))
            except Exception as error:
                self.after(0, lambda msg=str(error): self.complete(None, msg))

        threading.Thread(target=worker, daemon=True).start()

    def complete(self, result, error):
        self.run_button.config(state="normal")
        if error:
            self.status.set(error)
            messagebox.showerror("Jarvis", error)
            return
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", result)
        self.status.set("Response ready")


if __name__ == "__main__":
    Jarvis().mainloop()
