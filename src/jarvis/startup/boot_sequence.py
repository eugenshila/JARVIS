"""Cinematic JARVIS boot screen inspired by the supplied HUD reference."""
from __future__ import annotations
import threading, time, tkinter as tk
from jarvis.startup.morning_brief import build_brief, voice_script
from jarvis.voice import speak

def run_boot_sequence(user_name: str = "Eugene", tasks: list[str] | None = None, seconds: float = 7.0) -> dict:
    brief={"time":"--:--","date":"BOOTING","greeting":"Good morning","user":user_name,
           "weather":{"city":"Nairobi","temp":0,"condition":"Initializing"},"markets":[],"news":[],"tasks":tasks or []}
    try:
        root=tk.Tk()
        root.title("J.A.R.V.I.S — SHILATECH BOOT")
        root.configure(bg="#020509")
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        status=tk.StringVar(value="INITIALIZING J.A.R.V.I.S CORE")
        clock=tk.StringVar(value="")
        weather=tk.StringVar(value="WEATHER  •  CONNECTING")
        markets=tk.StringVar(value="MARKETS  •  CONNECTING")
        news=tk.StringVar(value="LATEST NEWS  •  CONNECTING")
        tasks_var=tk.StringVar(value="TASKS  •  LOADING")
        canvas=tk.Canvas(root,bg="#020509",highlightthickness=0)
        canvas.pack(fill="both",expand=True)
        def draw():
            canvas.delete("all"); w=root.winfo_width(); h=root.winfo_height(); cx,cy=w//2,h//2
            for r in (310,270,235,195):
                canvas.create_oval(cx-r,cy-r,cx+r,cy+r,outline="#0e7490" if r<300 else "#164e63",width=2)
            canvas.create_oval(cx-155,cy-155,cx+155,cy+155,outline="#22d3ee",width=5)
            canvas.create_text(cx,cy-38,text="J.A.R.V.I.S",fill="#e2e8f0",font=("Segoe UI Light",32))
            canvas.create_text(cx,cy+5,text="SHILATECH",fill="#22d3ee",font=("Consolas",12,"bold"))
            canvas.create_text(cx,cy+34,text="PERSONAL AI SYSTEM",fill="#64748b",font=("Consolas",9))
            canvas.create_text(55,45,text="JARVIS SYSTEM BOOT",anchor="nw",fill="#22d3ee",font=("Consolas",15,"bold"))
            canvas.create_text(55,73,textvariable=status,anchor="nw",fill="#94a3b8",font=("Consolas",10))
            canvas.create_text(w-55,45,textvariable=clock,anchor="ne",fill="#64748b",font=("Consolas",11))
            for y,title,var in [(120,"WEATHER",weather),(235,"PRIORITY TASKS",tasks_var),(350,"MARKET WATCH",markets),(465,"LATEST NEWS",news)]:
                canvas.create_rectangle(45,y,w//2-335,y+85,outline="#164e63",width=1)
                canvas.create_text(60,y+12,text=title,anchor="nw",fill="#22d3ee",font=("Consolas",9,"bold"))
                canvas.create_text(60,y+36,textvariable=var,anchor="nw",fill="#cbd5e1",font=("Consolas",9),width=w//2-430)
            canvas.create_text(w-55,h-35,text="LOCAL-FIRST • OLLAMA • VOICE • SECURE",anchor="se",fill="#334155",font=("Consolas",8))
        def tick():
            clock.set(time.strftime("%H:%M:%S  •  %Y-%m-%d"))
            draw(); root.after(500,tick)
        def load():
            nonlocal brief
            try:
                status.set("CONNECTING TO WEATHER / MARKETS / NEWS")
                brief=build_brief(user_name,tasks)
                w=brief["weather"]; 
                weather.set(f'{w["city"]}  •  {w.get("temp","--")}°C  •  {w.get("condition","Unavailable")}  •  rain {w.get("rain","--")}%')
                tasks_var.set("  •  ".join(tasks[:3]) if tasks else "No priority tasks configured")
                market_lines=[f'{x["label"]}: {x.get("pct",0):+.1f}%' for x in brief["markets"] if "pct" in x]
                markets.set("   |   ".join(market_lines) if market_lines else "Market data unavailable")
                news_titles=[x["title"] for x in brief["news"][:2]]
                news.set("   |   ".join(news_titles) if news_titles else "Headlines unavailable")
                status.set("SYSTEMS NOMINAL  •  OLLAMA READY  •  VOICE READY")
                speak(voice_script(brief))
            except Exception as exc:
                status.set(f"BOOT CONTINUES  •  {exc}")
        threading.Thread(target=load,daemon=True).start()
        start=time.monotonic()
        def finish():
            if time.monotonic()-start >= seconds:
                try: root.destroy()
                except Exception: pass
            else: root.after(200,finish)
        tick(); finish(); root.mainloop()
    except Exception:
        try:
            brief=build_brief(user_name,tasks)
            speak(voice_script(brief))
        except Exception:
            pass
    return brief
