# The orchestration layer (Tier 2)

Six additions that sit on top of the reliability layer: plan work, queue it,
run it with recovery, keep the model warm, remember who the user is, and stop
handing the whole API to anyone on the LAN.

Design credit as before: shapes adapted from FatihMakes' Mark-XXXIX-OR and
Mark-LV; no code copied (unlicensed / CC BY-NC 4.0 respectively, both
incompatible with our Apache-2.0).

---

## 6 + 7. Plan → queue → execute

### `agents/planner.py`

A goal becomes a short JSON plan of validated tool calls.

**The tool catalogue is generated, not written.** The obvious way to build the
planner prompt is to type the tool list into it — which is what the assistants
this came from do, and their prompt has already drifted: it documents
parameters that no longer exist and omits tools that do. Here
`tool_catalogue()` renders the live `ToolSpec` JSON schemas, so a tool's
arguments can never be described wrongly and a newly discovered tool is
plannable the moment it is added.

Plans are then validated against those same specs *before anything runs*:

| Rejected | Message |
|---|---|
| unknown tool | `unknown tool 'frobnicate'` |
| invented argument | `file_read has no argument(s) pathh; valid: path` |
| missing required arg | `file_read is missing required argument(s) path` |
| non-JSON output | `planner did not return valid JSON` |

`Plan.needs_approval` is true when any step touches a `requires_approval`
tool, so the HUD can show the plan before it starts.

### `core/task_queue.py`

Priority queue + worker threads. `HIGH` jumps the queue; equal priorities are
strictly FIFO so nothing waiting can be starved. Every task carries a
`threading.Event` cancel flag — pending tasks never run, running tasks see
`task.cancelled` between steps. `task.note()` reports progress, and
`snapshot()` is what the HUD polls for "working on 3 things". Finished tasks
are trimmed so a long session cannot grow forever, and a throwing
`on_complete` callback cannot kill the worker.

### `agents/executor.py`

Runs a plan and handles reality disagreeing with it, using the Tier 1
classifier: **RETRY** within budget, **SKIP** and carry on, **REPLAN** the
*remainder* of the goal once with the failure as context, or **ABORT**.
Cancellation is checked between steps. Steps never reference each other's
output as parameters (the planner is told not to write such plans); results
accumulate in a transcript that a replan receives.

```
jarvis do "summarise the quarterly report and save it to my desktop"
jarvis do --dry-run "..."      # show the plan, run nothing
jarvis do --background "..."   # queue it
jarvis tasks                   # what is running
```

`POST /plan`, `POST /tasks`, `GET /tasks`, `GET /tasks/{id}`,
`DELETE /tasks/{id}`.

## 8. Ollama KV-prefix warmup — `engine/ollama.py`

Ollama caches the attention state of a prompt *prefix* between requests.
Warming up with the same system prompt real requests will use means those few
hundred tokens are evaluated once at startup rather than on the user's first
question — the difference between ~15s and ~1s to first token on low-spec
hardware.

```python
engine.warmup(agent.static_system_prompt())
```

`num_predict: 1` (we want the prefix evaluated, not an answer), `keep_alive`
so the model stays resident, idempotent per prompt, and a failed warmup
returns `False` rather than raising — it is a missed optimisation, not an
error. `BaseAgent.static_system_prompt()` deliberately excludes anything
per-request, because that would invalidate the cached prefix.

## 11. Always-injected profile memory — `memory/profile.py`

The vector store answers "what do I know about X?". It cannot answer "who am I
talking to?", because that question is never asked — it has to be in the
system prompt before the user speaks. JARVIS could hold a thousand memories
and still not know the user's name.

So there are two layers now: recall stays in the vector store; a small curated
profile is injected into every system prompt by `BaseAgent._system_message()`.

**The budget is the point.** Always-injected text taxes every request, so:
categories (`identity`, `preferences`, `projects`, `relationships`, `goals`,
`notes`), 400 chars per value, 2400 chars total, with eviction by **category
rank first, then age**. Sorting by age alone would evict the user's name
(written once, long ago) before a note written this morning — exactly
backwards; a test pins this. A corrupt profile returns empty rather than
breaking startup. Reachable via the `profile` tool and `GET /profile`.

## 10. Universal file processor — `tools/file_processor.py`

One tool for "do something with this file": detect the type, dispatch to the
verbs it supports.

| Type | Verbs |
|---|---|
| text / code | summarize, extract_text, stats |
| pdf, docx | summarize, extract_text, stats |
| csv / tsv | summarize, extract_text, stats, **analyze** |
| json | summarize, extract_text, stats, **validate** |
| image | describe, stats |
| archive | list, stats |
| audio / video | stats |

**Local libraries do the work; the model is only asked for `summarize` and
`describe`.** Counting CSV rows, validating JSON, listing a zip and extracting
PDF text are deterministic and must not cost a token or a network round trip —
this is the main departure from the design it is adapted from, which routed
everything through Gemini. Optional dependencies (`pypdf`, `python-docx`,
`pillow`) are imported inside the function that needs them and reported
cleanly when absent: `pip install -e ".[files]"`.

## 9. API authentication — `server/auth.py`

The API previously had **no authentication at all** while exposing
shell-capable agents, memory, connectors and the confirmation gate. On
loopback that is untidy; bound to `0.0.0.0` so the HUD works from a phone —
which the launcher scripts encourage — it is unauthenticated remote code
execution on the LAN.

Now: a bearer token compared with `secrets.compare_digest`, generated once
into `~/.jarvis/api_token` at mode 0600 (or `JARVIS_API_TOKEN`).

- **Loopback is exempt by default**, so the CLI, desktop shell and every
  existing local workflow are unchanged. Remote callers need the token.
- `Authorization: Bearer …`, `X-Jarvis-Token`, or `?token=` (browsers cannot
  set headers on EventSource/WebSocket URLs).
- `/health` and the OpenAPI docs stay open for proxies.
- `JARVIS_API_REQUIRE_TOKEN=1` removes the loopback exemption;
  `JARVIS_API_AUTH=off` disables it entirely.

```
jarvis token            # show it
jarvis token --rotate   # invalidate every existing client
```

Why a token rather than the application-layer AES the source design uses:
encrypting a payload does not authenticate a caller, and it leaves the key in
browser JavaScript. **This is not a substitute for TLS** — do not expose it to
the open internet without a terminator in front.

---

## Tests

`tests/test_orchestration_layer.py` — 52 tests: priority ordering and FIFO
fairness, cancellation before and during a run, progress reporting, planner
validation against live specs, executor retry/skip/abort/replan-once,
cancellation mid-plan, warmup payload shape and idempotency, profile budget
and eviction ordering, CSV/JSON/zip/stats handled with no model, summarize
passing real file text to the model, and every auth path.

Full suite: **143 passing.**
