# The reliability & safety layer

Five pieces, added together because they only pay off together: a call that can
fall back, a failure that gets classified, a dangerous action that a human
actually approved, a mistake that can be taken back, and a tool set that does
not depend on someone remembering to edit a list.

Design credit: the *shapes* of (1), (2), (3) and (5) are adapted from
FatihMakes' Mark-XXXIX-OR and Mark-LV — see `UPGRADES_FROM_MARK39.md` and
`UPGRADES_FROM_MARK_LV.md`. No code was copied (Mark 39 is unlicensed, Mark-LV
is CC BY-NC 4.0); these are independent implementations of the ideas.

---

## 1. Model ladders — `jarvis/engine/ladder.py`

Callers ask for a **purpose**, never a model:

```python
from jarvis.engine.ladder import for_purpose, FAST, SMART
reply = for_purpose(FAST).generate(messages)
```

| Purpose | For |
|---|---|
| `FAST` | classification, extraction, one-line decisions |
| `SMART` | reasoning, generation, long documents |
| `SEARCH` | grounded / tool-heavy work |

Each purpose is an ordered list of rungs `(engine, model, timeout)`. A call
walks top to bottom:

- **Every rung has a timeout.** Nothing in the stack bounded a request before;
  one endpoint returning 504s could hang a call indefinitely.
- **A failed rung goes on a cooldown** (30s → 60s → 120s → 300s, reset on
  success), so the *next* request does not pay the same timeout again.
- **An empty response counts as a failure.** Silently returning `""` is what a
  dying endpoint looks like from the outside.
- **A rung that cannot be built is skipped**, so listing `openai` costs nothing
  when `OPENAI_API_KEY` is unset.

Defaults are local-first (Ollama leads). Override in `~/.jarvis/config.toml` —
see the `[ladder.*]` section of `configs/jarvis/config.example.toml`. Inspect
live state at `GET /ladder`, and `engine.last_trace` after any call.

## 2. Failure recovery — `jarvis/agents/recovery.py`

Every tool failure is classified into one of four decisions:

| Decision | Meaning |
|---|---|
| `RETRY` | transient — the same step, unchanged, can succeed |
| `SKIP` | not critical — the task can succeed without it |
| `REPLAN` | the approach was wrong — different tool or arguments |
| `ABORT` | impossible or unsafe to continue |

A **rule table handles the common cases with no model call at all**: timeouts,
429s, 5xx, connection resets, locked files, missing paths, bad arguments,
permission denied, missing optional dependencies, full disk. Only genuinely
novel failures go to the model, and they go to the `FAST` ladder. If the model
is unavailable or answers with nonsense, the fallback is one retry then replan
— never a loop.

Every decision carries a `user_message` of at most fifteen words, because it is
meant to be spoken. `ReActAgent` now acts on these decisions with a
`RetryBudget` capping retries per-step and in total.

## 3. The confirmation gate — `jarvis/core/confirm.py`

The old pattern was:

```python
if not confirm:            # ← a TOOL PARAMETER
    return "Run again with confirm=true."
```

**The model writes tool parameters.** Nothing stopped it sending `confirm=true`
on the first call, and nothing checked that a human was ever involved. It was a
convention, not a gate.

Now the token is issued by the *interface*:

1. A tool calls `confirm.request(title, detail, run=callable)` — which returns
   immediately and does **not** run the work.
2. The HUD shows the pending item (`GET /confirm`) with CONFIRM / CANCEL.
3. Only `POST /confirm/{token}/approve` runs the callable.

Non-blocking, 90-second expiry, bounded queue, and a token cannot be replayed
(the entry is removed before the work runs). `ShellTool` and `AppLauncherTool`
now go through it; `ShellTool` has no `confirm` parameter at all.

### The affordance — where a human actually presses the button

A gate with no button is just a queue that never drains, so both HUDs render
pending requests:

- **Browser HUD** — `frontend/src/components/ConfirmGate.tsx`, mounted in
  `main.tsx` *outside* `<App>` so it appears over the dashboard, the Iron Man
  HUDs and classic chat alike. It polls `GET /confirm` every 2s, shows title,
  detail and a live countdown bar, and posts approve/cancel. `Esc` cancels the
  oldest item; there is deliberately **no keyboard shortcut for approve** —
  confirming should be a decision, not a reflex. When no backend answers (the
  GitHub Pages demo) it backs off to a 30s heartbeat and renders nothing.
- **Desktop HUD** — `app.py` grows an amber bar under the title bar
  (`poll_confirmations`, `approve_confirmation`, `cancel_confirmation`). The
  MSI build runs the agent in-process, so it reads `jarvis.core.confirm`
  directly; approved work runs on a worker thread so a slow command cannot
  freeze Tk.

Both send the API token (`X-Jarvis-Token`) when one is configured, so the gate
still works with `JARVIS_API_REQUIRE_TOKEN=1`.

Reserved strictly for **irreversible** things. Everything else uses undo.

## 4. The undo stack — `jarvis/core/undo.py`

An assistant that asks "are you sure?" before every action is one you stop
using. So: act immediately, remember how to reverse it, let the user say
"undo".

```python
from jarvis.core.undo import push_undo

old = path.read_text()
path.write_text(new)
push_undo(f"write {path.name}", lambda: (path.write_text(old), "restored")[1])
```

Depth 10, thread-safe, LIFO. A failing reverse returns a message rather than
raising. `FileWriteTool` is wired up; the model reaches it through the `undo`
tool, and the UI through `GET`/`POST /undo`.

## 5. Tool discovery — `jarvis/tools/discovery.py`

`tools/registry.py` was ~20 `try/except ImportError` blocks and a dict literal
naming every class twice. Now the package is scanned:

- Any `BaseTool` subclass with a `spec` in `jarvis/tools/` is found.
- So is any module dropped in `~/.jarvis/plugins/` — user plugins need no
  changes to the codebase.
- A tool may declare `behavior = "BLOCKING" | "NON_BLOCKING"` and
  `scheduling = "WHEN_IDLE" | "SILENT" | "INTERRUPT"`, so a slow tool can say
  so instead of holding the conversation open.
- Import errors, invalid specs and name collisions are **recorded and skipped**
  — discovery never raises, and one broken optional dependency cannot take the
  whole tool set down. See `format_problems()` and `GET /tools`.
- Enable/disable is read from `~/.jarvis/tools.json` **on every dispatch**
  (mtime-cached), so a UI toggle needs no restart.

`REGISTRY`, `get_tool`, `list_tools` and `get_tools` keep working; `REGISTRY`
is now a live read-only view. Historical aliases (`code_exec`, `career`,
`online_status`, …) are declared in `ALIASES`.

---

## New HTTP endpoints

| Endpoint | Purpose |
|---|---|
| `GET /confirm` | what is waiting on a human |
| `POST /confirm/{token}/approve` | a human pressed CONFIRM |
| `POST /confirm/{token}/cancel` | a human pressed CANCEL |
| `GET /undo` / `POST /undo` | undo history / undo last |
| `GET /ladder` | rungs, availability, active cooldowns |
| `GET /tools` | every discovered tool, including load failures |

## Tests

`tests/test_reliability_layer.py` — 52 tests covering fallthrough, timeout
bounding, cooldown skip/backoff, token replay and expiry, "the shell tool does
not run without a human", undo LIFO/bounding/failure, every classifier rule,
malformed model output, broken-module discovery, user plugins, and two ReAct
integration cases (transient failure recovered, permission failure aborted).

`tests/test_confirm_hud.py` — 10 tests over the *interface* half: the HTTP
endpoints (pending request visible, nothing runs until approve, a token cannot
be replayed, cancel drops the work, unknown token rejected), the React gate
(exists, calls the right endpoints, is mounted for every view, dev server
proxies `/confirm`), and the desktop HUD (polls, exposes CONFIRM/CANCEL, runs
approved work off the UI thread).

## Known limitations

1. **Loopback auth is permissive by default.** `server/auth.py` exempts
   loopback callers unless `JARVIS_API_REQUIRE_TOKEN=1`. Any local process —
   including a browser tab on a malicious page hitting `localhost:8000` — can
   therefore reach shell-capable endpoints. Tightening the default would break
   the CLI, the desktop shell and the launcher scripts, so it is a product
   decision, not a patch.
2. **`_call_with_timeout` leaks daemon threads.** A rung that exceeds its
   timeout is abandoned, not cancelled: the worker thread keeps running until
   the underlying HTTP call returns. Bounded in practice by the engines' own
   socket timeouts, but a hung endpoint can accumulate threads over a long
   session. A real fix needs cancellable engine calls (async client or
   per-request session teardown).
