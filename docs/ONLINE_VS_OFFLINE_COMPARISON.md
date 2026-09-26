# JARVIS Voice + Online vs Offline Comparison — SHILATECH

**Question:** "i need jarvis to speak to me whether online or offline i know i can be able to do alot of things when its online, what is the comparison between the 2"

**Answer:** Yes — JARVIS speaks to you both online and offline, Sir. Same circular interface. Different capabilities.

---

## 🔊 Voice — Works Both Online and Offline ✅

**You asked: need JARVIS to speak whether online or offline**

**Yes — implemented 3 layers:**

### Frontend Circular HUD (IronManCircularHUD.tsx) — Browser TTS, always works
- `speechSynthesis` API — built into Chrome/Edge/Firefox, offline, no internet needed
- British voice preferred if available
- Button: `🔊 VOICE ON` / `🔇` — toggle
- When speaking: `🔊 SPEAKING` pulsing green
- Mic: `🎤` button → `webkitSpeechRecognition` / `SpeechRecognition` — browser offline API, click to speak
- `speak(reply)` called after every `send()` — assistant response spoken automatically when voice enabled
- Works both online and offline, same interface

### Backend Python (voice_io.py) — Offline-first
- **STT (Speech-to-Text) you speak to JARVIS:**
  - `faster-whisper (offline local)` — best, runs on CPU, no internet, `pip install faster-whisper sounddevice soundfile`
  - `whisper (offline)` — OpenAI Whisper local
  - `speech_recognition` — fallback
  - `mock (type to talk)` — always works, type instead

- **TTS (Text-to-Speech) JARVIS speaks to you:**
  - `kokoro (neural, offline)` — best quality neural, offline, `pip install kokoro`
  - `pyttsx3 (offline)` — classic offline, `pip install pyttsx3`, rate 180, British voice if available
  - `espeak / espeak-ng (offline)` — Linux `apt install espeak`
  - `mock (text only)` — prints `🔊 JARVIS: text` always

- **CLI:**
```bash
jarvis ironman --voice --engine auto   # voice loop with wake word "jarvis"
jarvis voice --engine auto             # same, alias
jarvis daemon --mode ironman --name Eugene  # autostart Good Morning Eugene with TTS + notification + tray
```

- **Daemon (daemon.py) — Autostart Good Morning:**
  - On boot: `Good morning Eugene` + 3 MITs alignment
  - TTS: tries VoiceIO → pyttsx3 British → espeak
  - Notification: plyer / notify-send / PowerShell
  - System tray: arc reactor icon, menu Show HUD / Good Morning / Tasks / Focus 25m / Quit
  - Periodic ADHD check-in every 25 min Pomodoro

**So voice works offline, Sir. No internet needed for JARVIS to speak.**

---

## 🌐 Online vs 📴 Offline — Full Comparison for i5-6300U 8GB SHILATECH

Same circular interface both — only badge changes. You decide interactive when online.

| Feature | 📴 OFFLINE BASIC (Local Only) | 🌐 ONLINE FULL STACK | Notes for your machine |
|---------|-------------------------------|----------------------|------------------------|
| **Interface** | Circular HUD 560px, 72 ticks, blue glow, number 13, left device specs, right weather, bottom Trash 44 items Size 248.95 MB | Same circular HUD, identical | Only badge changes: OFFLINE BASIC vs ONLINE FULL STACK • CLICK TO DECIDE |
| **Badge** | `📴 OFFLINE • BASIC • SHILATECH` red | `🌐 ONLINE OPENAI • FULL STACK • CLICK TO DECIDE` green pulsing | Clickable → decision modal |
| **Engine** | `mock` always works OR `ollama tinyllama` 1.1B offline | `openai` (best for 8GB) OR `ollama` local even online | Auto picks best: online check 8.8.8.8:53 socket |
| **LLM Quality** | mock: keyword heuristic, canned responses, fast 0ms | openai gpt-4o-mini: best quality, reasoning, code, 1-2 sec | For i5-6300U 8GB: openai best (no RAM), mock always works |
| **LLM Speed** | mock: instant, tinyllama: ~8-10 tokens/sec on i5-6300U | openai: ~30-50 tokens/sec streaming, no local RAM | offline slower but private |
| **RAM Usage** | mock: ~50MB, tinyllama: ~1.5GB | openai: ~50MB (LLM in cloud, no RAM), ollama tinyllama online: ~1.5GB local | Your 8GB: openai recommended |
| **What You Can Do — Basic Offline** | • Good morning Eugene + 3 MITs alignment<br/>• Brain dump → tasks<br/>• Focus 25m Pomodoro<br/>• ADHD coach, body double<br/>• Wins, energy log, dopamine menu<br/>• Calendar mock 3 events / email mock 3<br/>• Memory keyword search local<br/>• Faces local<br/>• Voice pyttsx3/kokoro offline<br/>• All tools 50 but mock search | Same as offline PLUS... | Offline already powerful |
| **What You Can Do — Extra Online** | — | • Real web search Tavily/DDGS — "weather Nairobi" live<br/>• Deep research agent — multi-step search + synthesis<br/>• OpenAI best code assistant<br/>• Real Google Calendar/Gmail via OAuth (Google API, not us)<br/>• Memory FAISS semantic search (better than keyword)<br/>• News, stocks, live data<br/>• Better reasoning for Q4 planning, client emails | Online = more data, best quality |
| **Search** | mock only — returns mock results | Tavily (if TAVILY_API_KEY) or DDGS free — real web | Online search only thing that needs internet |
| **Memory** | keyword fallback local ~/.jarvis/memory — works | FAISS vector local + semantic — better recall | Both local, not sent to cloud unless context added |
| **Calendar / Email** | calendar.json / emails.json mock 3 — local | Google Calendar/Gmail OAuth real + mock fallback | Google token local ~/.jarvis/google_token.json |
| **Voice STT** | faster-whisper offline local — works offline | Same faster-whisper offline — STT always local, even online | STT never needs internet |
| **Voice TTS** | pyttsx3 offline / kokoro offline / espeak offline — speaks offline | Same pyttsx3/kokoro offline — TTS always local, even online + browser speechSynthesis offline | JARVIS speaks both online/offline, Sir |
| **Data Privacy** | NOTHING leaves device — 100% private, SHILATECH secure | Only prompt you type sent to OpenAI API if you set OPENAI_API_KEY HTTPS encrypted. Or Ollama local — LLM stays device even online, only search queries go online | You control: --interactive to decide Basic even online |
| **Security** | 🔒 LOCAL ONLY • SECURE | 🔒 ENCRYPTED • SECURE — OpenAI API data not used to train by default, no telemetry | No data to eugenshila/JARVIS server |
| **Network** | No internet, check_online fails, auto picks offline_engine | Online via socket 8.8.8.8:53 + latency ms | Auto detection every 30 sec |
| **Decision When Online** | Already basic — no decision needed | Interactive modal: 1. Full Stack Online (green recommended) 2. Basic Offline Local Even Though Online (amber private) — you decide from HUD click or CLI --interactive | Same circular interface |
| **Autostart** | `jarvis daemon --mode ironman --name Eugene --engine mock` — Good Morning + TTS + tray + 25min check-ins | `jarvis daemon --mode ironman --name Eugene --engine auto` — same but full stack when online | Good morning Eugene, Sir |
| **For i5-6300U 8GB** | mock always works, tinyllama 1.1B if `ollama pull tinyllama` ~1.5GB RAM | openai best — no local RAM, best quality, recommended. Or ollama phi3:mini 3.8B if you have RAM | Skip vLLM needs NVIDIA GPU, MLX needs Mac |

### Recommended Setup for You (Eugene, Nairobi, DESKTOP-3D8CN02)

```powershell
# 1. Offline Basic — always works, voice offline, 100% private
jarvis ask --engine mock "Good morning Eugene"
# Voice: jarvis ironman --voice --engine mock
# HUD: npm run dev → circular HUD offline badge

# 2. Online Full Stack — best quality for 8GB, voice still offline
$env:OPENAI_API_KEY="sk-..."  # from platform.openai.com/api-keys
$env:TAVILY_API_KEY="tvly-..." # optional for real search
jarvis hybrid --action set --online-engine openai --offline-engine mock
jarvis ask --engine auto --interactive "Good morning Eugene"
# Decision: 1 Full Stack Online (openai) vs 2 Basic Local even online
# Voice: jarvis ironman --voice --engine auto --interactive

# 3. Most Private Even Online — LLM stays local even online
ollama pull tinyllama  # 1.1B best for 8GB
ollama serve
jarvis hybrid --action set --online-engine ollama --offline-engine ollama
jarvis ask --engine auto "Good morning Eugene"
# LLM stays on your i5-6300U even online, only search goes online, voice offline
```

### Voice Comparison Detail

| Voice Feature | Offline | Online | Implementation |
|---------------|---------|--------|----------------|
| JARVIS speaks response | Yes — pyttsx3/kokoro/espeak offline + browser speechSynthesis offline | Yes — same offline TTS + browser speechSynthesis offline | `speak()` in voice_io.py + frontend `speak()` in circular HUD |
| You speak to JARVIS (STT) | Yes — faster-whisper offline local + browser webkitSpeechRecognition offline | Yes — same faster-whisper offline local, STT never needs internet | `listen()` in voice_io.py + `toggleListen()` in circular HUD |
| Wake word "Jarvis" | Yes — local detection in voice loop | Yes — same local | `interactive_voice_loop` checks wake_word.lower() in lower |
| Good Morning TTS on boot | Yes — daemon speaks Good Morning Eugene + 3 MITs | Yes — same | `daemon.py speak_greeting()` |
| Quality | pyttsx3 robotic but works, kokoro neural high quality offline | Same offline quality — no cloud TTS needed, private | No ElevenLabs cloud unless you add |
| Install | `pip install pyttsx3` or `pip install kokoro faster-whisper sounddevice soundfile` | Same | No API key needed for voice |

**Bottom line:** JARVIS speaks to you whether online or offline, Sir. Voice is offline-first, private, SHILATECH. Online just gives you best LLM quality + real search + Google integration, same circular interface, you decide interactive when online.

---

## Files Updated for Voice + Comparison

- `frontend/src/pages/IronManCircularHUD.tsx` — added `voiceEnabled`, `isListening`, `isSpeaking` states, `speak()` using speechSynthesis British voice, `toggleListen()` using webkitSpeechRecognition, voice buttons 🎤 + 🔊 VOICE ON/OFF + SPEAKING pulsing, greeting shows voice status, `send()` calls `speak(reply)`
- `frontend/src/pages/IronManHUD.tsx` — already had voice waveform + speechSynthesis
- `src/jarvis/speech/voice_io.py` — offline-first STT faster-whisper + TTS pyttsx3/kokoro/espeak
- `src/jarvis/startup/daemon.py` — autostart Good Morning Eugene + TTS + tray
- `docs/ONLINE_VS_OFFLINE_COMPARISON.md` — this file
- Build: 38 modules 251.40kB 71.78kB gzip

**SHILATECH • Malibu Point 10880 • Voice works online/offline, Sir.**
