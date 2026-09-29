# The awareness layer (Tier 3)

Seven additions: seeing the screen, hearing a wake word without wrecking the
audio thread, not answering itself, speaking unprompted without becoming
intolerable, following topics without becoming a tracker, and finding a
writable directory on a real install.

Design credit as before — shapes adapted from FatihMakes' Mark-XXXIX-OR and
Mark-LV; no code copied (unlicensed / CC BY-NC 4.0, both incompatible with our
Apache-2.0).

---

## 12. Screen and camera capture — `core/capture.py`

**The budget is the design.** A raw 4K screenshot is ~8 MB of PNG, ~11 MB once
base64'd into a request body, and a vision model spends seconds just receiving
it — to answer "what error is on my screen?", which a 640x360 JPEG answers
equally well. Every capture is downscaled to **640x360, JPEG q55** (~40 KB) by
`_downscale_and_save` before it goes anywhere.

**Consent is explicit and off by default.** Reading the screen means reading
whatever is on it: password managers, private messages, other people's data.
That is not something to enable because a model asked. Requires
`JARVIS_ALLOW_CAPTURE=1` or `jarvis capture --enable`, and the refusal *says
why* rather than just failing. Every capture is written to
`~/.jarvis/captures` so the user can see what was taken, and only the newest
10 are kept.

Tools: `screen_capture`, `camera_capture`, `capture_settings` — the first two
marked `requires_approval`, so they also route through the Tier 1 confirmation
gate. The camera is always released in a `finally`, so the webcam light never
stays on. API: `GET /capture`, `POST /capture/screen`. CLI: `jarvis capture`.

## 13. Wake word — `speech/wake.py`

Two disciplines, both tested:

1. **Zero cost when off.** `openwakeword` (and the ONNX runtime it drags in)
   is imported *inside* `start()`, never at module scope. A test asserts the
   module is not in `sys.modules` after importing ours.
2. **Zero work on the audio thread.** `feed()` does nothing but a non-blocking
   queue push; inference runs on a background thread. When the queue is full
   the **oldest** block is dropped rather than blocking the caller — detecting
   a wake word slightly late is survivable, stuttering the capture stream is
   not. A test feeds 3× the queue depth and asserts it never waits and that
   the newest block survived.

A throwing `on_wake` callback cannot kill the listener, and the backlog is
cleared after a hit so one utterance cannot fire twice.

## 14. Echo suppression — `speech/echo.py`

Writing audio to a device returns when the buffer *accepts* it, not when the
room is finished with it. Stream the mic through that gap and the assistant
hears its own last sentence and answers itself.

**Why a loudness threshold cannot work:** "the mic is louder than the echo"
needs to know how loud the echo is, which depends on speaker volume, mic
placement, the room, headphones, a hand over the mic. One tuned number is
wrong for almost everyone.

Instead, two signals that need no per-machine tuning:

1. **Content.** Both streams reduce to 8 log-spaced band energies, and recent
   output is **subtracted** from the mic block rather than compared with it.
   Pure echo cancels to nearly nothing; a second voice survives, because its
   formants sit in bands where ours were weak. A test pins the case a level
   threshold gets wrong: *same loudness, different voice* → not echo.
2. **A learned echo gain.** Every confident echo updates a running mic/output
   ratio, so the system calibrates to the real room within a few seconds and
   re-calibrates when conditions change.

numpy is optional; without it this degrades to the plain tail gate rather than
failing to import.

## 15. Proactive engine — `agents/proactive.py`

Owns *when* to speak unprompted, and nothing else — the model still decides
what to say. Gates in order: **enabled** (off by default), **quiet hours**,
**silence** (15 min), **cooldown** (20 min), **not busy**, **daily cap** (6).

Non-repetition has two mechanisms: the focus rotates through
`priorities → monitors → calendar → wellbeing` so consecutive nudges are never
about the same thing, and a hash of each delivered message is remembered so
the same opener is not sent twice.

The prompt gives the model an explicit way out: reply `NOTHING` and it is not
delivered. An assistant that must produce a nudge will produce small talk.

## 16. Topic monitor — `tools/monitor_tools.py`

"Keep an eye on X" → stored, checked at most once a day, only unseen headlines
reported (deduplicated by normalised hash, so re-worded coverage of the same
story stays quiet).

Three deliberate limits: **nothing is ever monitored implicitly** (there is no
"we noticed you mentioned X" path into the list), a **cap of 10 topics**, and a
**blocklist** — crypto, forex and day-trading topics are refused in several
spellings and scripts. An assistant that volunteers price moves is a trading
nag that manufactures urgency, and the person most harmed is whoever asked for
it at 2am. Refusing is the feature; the user can still ask directly.

## 17 + 18. Paths — `core/paths.py`

**Frozen builds.** Under PyInstaller (the Windows MSI), `__file__` points into
a temp extraction directory that is deleted on exit. Anything resolving
bundled resources relative to `__file__` works in a checkout and silently
breaks in the MSI. `is_frozen()`, `base_dir()` and `resource_dir()` (which
honours `sys._MEIPASS`) handle both.

**Writable directories.** "Write next to the executable" fails on a real
install: `C:\Program Files` is not user-writable and a signed .app bundle is
read-only. `uploads_dir()` walks `~/Downloads/JARVIS Uploads` →
`~/Documents/JARVIS Uploads` → `~/.jarvis/uploads` → app dir → temp, and
`_writable()` **verifies by writing a probe file and deleting it** rather than
assuming. Overridable with `JARVIS_UPLOADS_DIR`.

`POST /upload` uses the chain, caps at 500 MB, strips the path from the
supplied filename, and reports which file-processor verbs apply.

---

## Optional dependencies

```
pip install -e ".[capture]"    # mss, pillow, opencv-python
pip install -e ".[wakeword]"   # openwakeword, sounddevice, numpy
pip install -e ".[files]"      # pypdf, python-docx, pillow
```

None are required. Every feature reports a clear install hint when its
dependency is absent, and none of them are imported at module load.

## Tests

`tests/test_awareness_layer.py` — 45 tests: consent refusal and its wording,
4K downscaled to exactly 640x360 under 200 KB, capture pruning, the
`openwakeword`-not-imported assertion, `feed()` never blocking and dropping
oldest, detection on the worker thread, echo vs a second voice at equal
loudness, self-calibration, every proactive gate, focus rotation, repeat
detection, crypto refusal across spellings, headline dedupe, frozen-path
resolution, and the writability probe.

Full suite: **188 passing.**
