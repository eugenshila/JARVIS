# Income OS + JAUTOMATIC Finalization — Spec

Status: planning + partial implementation. Grounded in the current state of
`eugenshila/JARVIS` on `main` (this file lives at
`docs/INCOME_OS_AND_JAUTOMATIC_SPEC.md`).

This spec has three parts:

1. **Part 1 — Connect JAUTOMATIC** (mostly already built; needs configuring).
2. **Part 2 — Build the Income OS** (new investment/income capability, not built yet).
3. **Part 3 — A copy-paste prompt** for a new coding session to implement
   everything in Part 2 (and double-check Part 1).

> **Update:** the one small code tweak called out in Part 1 has already been
> applied in this session (see below) and is covered by new tests. Part 1 is
> now just "set env vars and run the verify commands" — no code changes left.

---

## Part 1 — Connect `eugenshila/JAUTOMATIC` (mostly already built)

JARVIS already ships a full connector (`src/jarvis/connectors/jautomatic.py`),
a `career_os` tool (`src/jarvis/tools/career_tools.py`), a `jarvis career ...`
CLI group (`src/jarvis/cli/main.py`), read-only `/hud/career*` API endpoints
(`src/jarvis/server/api.py`), and a CAREER OS HUD card
(`frontend/src/pages/IronManCircularHUD.tsx`). JARVIS never auto-submits
applications or sends email — it reads JAUTOMATIC's local workspace and turns
it into daily plans. Full background in `docs/JAUTOMATIC_INTEGRATION.md`.

On GitHub the project is published as `eugenshila/JAUTOMATIC-JOB-SEARCH`
(there is no separate repo literally named `JAUTOMATIC`). Locally, though,
people often clone or rename the checkout folder to the shorter `JAUTOMATIC`
— that mismatch was the one connector gap, now fixed (see "Code tweak"
below).

### Exact env vars to set

Set these wherever your JAUTOMATIC checkout/app + data actually live. All are
optional — JARVIS falls back to sane per-OS defaults — but setting them
explicitly avoids ambiguity.

```bash
# Linux/macOS example
export JAUTOMATIC_REPO="$HOME/JAUTOMATIC"                 # source checkout (folder can be named
                                                            # JAUTOMATIC or JAUTOMATIC-JOB-SEARCH)
export JAUTOMATIC_DATA_DIR="$HOME/.local/share/jautomatic-job-search"  # workspace: jautomatic.sqlite3 + profile.json
export JAUTOMATIC_APP_PATH=""                              # optional: path to a packaged/installed executable
```

```powershell
# Windows PowerShell example
$env:JAUTOMATIC_REPO = "$HOME\JAUTOMATIC"
$env:JAUTOMATIC_DATA_DIR = "$env:APPDATA\JAUTOMATIC"
$env:JAUTOMATIC_APP_PATH = "C:\Program Files\JAUTOMATIC\jautomatic.exe"   # only if installed as an app
```

Notes:

- `JAUTOMATIC_REPO` (aliases: `JAUTOMATIC_SOURCE`, `JAUTOMATIC_HOME`) — path
  to the JAUTOMATIC **source checkout** (needs `main.py` and a `jautomatic/`
  package inside it). Used to *launch* JAUTOMATIC from JARVIS.
- `JAUTOMATIC_DATA_DIR` — path to JAUTOMATIC's **workspace** containing
  `jautomatic.sqlite3`, `profile.json`, `settings.json`, `documents/`,
  `exports/`. Used to *read* pipeline/profile/training data. Defaults to
  `%APPDATA%\JAUTOMATIC` on Windows or `~/.local/share/jautomatic-job-search`
  on Linux/macOS if unset.
- `JAUTOMATIC_APP_PATH` — only needed if you run a packaged JAUTOMATIC
  executable instead of the Python source checkout.

If you don't set any of these, JARVIS still tries, in order: `JAUTOMATIC_APP_PATH`
→ common installed Windows paths → a sibling checkout next to this repo /
in `$HOME` / one level above `$HOME`, under either the `JAUTOMATIC-JOB-SEARCH`
or `JAUTOMATIC` folder name.

### Verify commands

Run these after setting the env vars (or after cloning JAUTOMATIC next to
JARVIS with a matching folder name):

```bash
jarvis career paths      # shows resolved workspace/db/profile/app paths + ✅/⚠️ per file
jarvis career status     # pipeline stats: jobs, applications, sent, interviews, offers, follow-ups
jarvis career mode --set seeking
jarvis career today      # 3-task ADHD-friendly plan for the active mode
jarvis career followups  # follow-ups due today
jarvis career training   # free-training progress (Microsoft Learn, freeCodeCamp, etc.)
jarvis career postgres   # confirms: No PostgreSQL required (SQLite + JSON only)
```

Expected good-state signals:

- `jarvis career paths` shows real paths with `✅` next to the database and
  profile files (not `⚠️ missing`).
- `jarvis career status` shows non-zero `jobs`/`applications` once you've run
  JAUTOMATIC at least once, and reports `Storage: SQLite + JSON files —
  PostgreSQL required: No`.
- `jarvis career mode --set seeking` persists to `~/.jarvis/career.json` (or
  `%JARVIS_HOME%\career.json` if `JARVIS_HOME` is set) and `today` then
  produces the "seeking" task list (follow-ups → materials-ready review →
  free training → 30-minute fresh search → one career-asset update).

### The one small code tweak — already applied

**Problem:** `src/jarvis/connectors/jautomatic.py::_repo_candidates()`
only looked for a sibling checkout folder named `JAUTOMATIC-JOB-SEARCH`. If a
user clones/renames it to the shorter `JAUTOMATIC` (as this project's naming
implies), JARVIS could not auto-discover it without manually setting
`JAUTOMATIC_REPO`.

**Fix (done in this session):** the candidate search now tries **both**
folder names — `JAUTOMATIC-JOB-SEARCH` and `JAUTOMATIC` — under each base
directory (next to this repo, `$HOME`, one level above `$HOME`, and
`/home/user`), in addition to any explicit `JAUTOMATIC_REPO` /
`JAUTOMATIC_SOURCE` / `JAUTOMATIC_HOME` env var.

```python
# src/jarvis/connectors/jautomatic.py
_REPO_FOLDER_NAMES = ("JAUTOMATIC-JOB-SEARCH", "JAUTOMATIC")

def _repo_candidates() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("JAUTOMATIC_REPO", "JAUTOMATIC_SOURCE", "JAUTOMATIC_HOME"):
        if os.environ.get(env_name):
            candidates.append(Path(os.environ[env_name]).expanduser())
    cwd = Path.cwd()
    home = Path.home()
    bases = [cwd.parent, home, home.parent, Path("/home/user")]
    for base in bases:
        for name in _REPO_FOLDER_NAMES:
            candidates.append(base / name)
    return candidates
```

Covered by new tests in `tests/test_jautomatic_integration.py`:
`test_repo_candidates_include_plain_jautomatic_folder_name` and
`test_find_app_locates_plain_jautomatic_source_checkout`. `docs/JAUTOMATIC_INTEGRATION.md`
was updated to describe both folder names. All 28 existing tests still pass.

### Acceptance checklist — Part 1

- [x] Connector, tool, CLI group, API routes, and HUD card exist (already in `main`).
- [x] Connector auto-discovers a checkout named `JAUTOMATIC` as well as
      `JAUTOMATIC-JOB-SEARCH` (code tweak applied + tested).
- [ ] `JAUTOMATIC_REPO`, `JAUTOMATIC_DATA_DIR` (and `JAUTOMATIC_APP_PATH` if
      applicable) are set in your real shell/profile — **you do this on your
      machine**, it's user-specific and not something to hardcode in the repo.
- [ ] `jarvis career paths` shows ✅ for the database and profile once
      JAUTOMATIC has been run at least once and produced data.
- [ ] `jarvis career status` / `today` / `mode --set seeking` /
      `followups` / `training` / `postgres` all return sensible output on
      your machine.
- [ ] Confirmed: JARVIS still never auto-applies/auto-sends anything —
      `career open` requires `--yes` and only launches JAUTOMATIC itself.

---

## Part 2 — Build the Income OS (new capability)

Income OS is a **research, tracking, and planning copilot** for online income
and investing — modeled after the existing Business OS / Career OS pattern
(local JSON/SQLite state, a `BaseTool` per capability, a `jarvis income ...`
CLI group, read-only `/hud/income*` API routes, and HUD cards). It does not
exist yet; this section specs it precisely enough to implement in one pass.

### Guardrails (non-negotiable, apply to every part below)

1. **Research / planning / tracking only — never autonomous trading.** No
   tool places orders, moves money, connects to a brokerage/exchange API for
   trading, or executes any transaction. Portfolio and watchlist data is
   **entered by the user**, not fetched live from a brokerage account.
2. **Not financial advice.** Every investment-related tool response and every
   INCOME dashboard card carries a visible disclaimer, e.g.: *"Informational
   only, not financial advice. Not a licensed financial advisor. You are
   responsible for your own investment decisions."*
3. **Local-first, no PostgreSQL.** State lives in local JSON files (plus
   optional local SQLite for time-series if needed) under `~/.jarvis/income/`,
   exactly like `career.json` and the Business OS profile today. No new
   server dependency, no cloud database.
4. **Read-only APIs.** New `/hud/income*` endpoints only ever read/append to
   local files the user controls; nothing calls external paid trading APIs
   automatically. News/market lookups reuse the existing `tavily_search` /
   `ddgs_search` tools (already in the repo) — optional, and degrade
   gracefully with a clear message if no search API key is configured.
5. **Confirmation for anything that writes.** Like `career_os`/`business_os`,
   Income OS tools that mutate state should keep `requires_approval=True`
   where they change the user's tracked money data, mirroring the existing
   pattern in `career_tools.py`.

### Data model — local files under `~/.jarvis/income/`

```
~/.jarvis/income/
  opportunities.json     # discovered/tracked gig & grant opportunities
  watchlist.json         # tickers/assets the user wants to watch (user-entered)
  portfolio.json         # user-entered holdings snapshot (NOT live-synced)
  research_notes.json    # saved research summaries per symbol/topic
  projects.json          # income-generating side projects: hours, revenue, expenses
  settings.json          # skills profile, risk notes, disclaimers-acknowledged flag
```

All files are plain JSON, human-readable, git-ignorable (`~/.jarvis/` is
outside the repo already, same convention as `career.json` /
`business_profile.json`).

### 4 new tools

Each is a `BaseTool` subclass in `src/jarvis/tools/income_tools.py`,
registered in `src/jarvis/tools/registry.py` next to `career_os`.

#### 1. `income_opportunities`
Find and track online gigs/freelance work/grants/bounties matched to the
user's skills (pulled from the JAUTOMATIC profile if present, else from
`settings.json`).

- Actions: `find` (uses `tavily_search`/`ddgs_search` with a skills-based
  query — e.g. "freelance Python automation gigs remote" — and stores
  candidate results), `list`, `add` (manually add an opportunity), `status`
  (mark `saved` / `applied` / `won` / `passed`), `today` (2-3 MIT suggestions,
  ADHD-style, matching `career today`'s format).
- Storage: `opportunities.json`, list of `{id, title, source, url, type
  (gig|grant|bounty|contract), est_value, skills_match, status, notes,
  added_at}`.
- Explicitly out of scope: auto-applying, auto-submitting proposals, storing
  payment credentials.

#### 2. `investment_research`
A watchlist + user-entered portfolio + news-summary tool. **Not advice.**

- Actions: `watchlist_add` / `watchlist_remove` / `watchlist` (list),
  `portfolio_set` (user enters holdings: symbol, quantity, cost basis, as of
  date — no brokerage connection), `portfolio` (show entered holdings +
  simple unrealized P/L if the user also supplies a current price manually
  or via a read-only quote lookup), `research` (fetch recent news for a
  symbol/topic via `tavily_search`/`ddgs_search` and save a dated summary to
  `research_notes.json`), `notes` (list saved research).
- Every response from this tool ends with the disclaimer line.
- No order placement, no brokerage OAuth, no auto-rebalancing.

#### 3. `income_projects`
Track side projects/freelance work: hours logged, revenue, expenses, simple
ROI.

- Actions: `add` (create a project), `log` (log hours and/or revenue/expense
  entries against a project), `list`, `report` (per-project totals: hours,
  revenue, expenses, net, $/hour), `today` (suggest which project to spend
  today's income-generating time block on, ADHD 1-3 MIT style).
- Storage: `projects.json`, list of `{id, name, status, entries: [{date,
  hours, revenue, expense, note}]}`.

#### 4. `money_briefing`
Rolls the above (plus Career OS) into one daily "money" section for the HUD
morning brief.

- Action: `today` — combines: career mode + follow-ups due (from
  `career_os`), top 1-2 income opportunities due for action, today's project
  suggestion, watchlist item count + any saved research from the last 24h,
  and the standing disclaimer.
- No new state of its own; it's a read-only aggregator, similar in spirit to
  `proactive_briefing`/`morning_digest` already in the repo.

### `jarvis income ...` CLI

New Click group in `src/jarvis/cli/main.py`, mirroring the `career` group:

```bash
jarvis income opportunities find --query "remote Python automation gigs"
jarvis income opportunities list
jarvis income opportunities add --title "..." --url "..." --type gig
jarvis income opportunities status --id <id> --set applied
jarvis income opportunities today

jarvis income watchlist add --symbol AAPL
jarvis income watchlist list
jarvis income portfolio set --symbol AAPL --quantity 10 --cost-basis 150
jarvis income portfolio show
jarvis income research --symbol AAPL
jarvis income research notes

jarvis income projects add --name "Freelance automation"
jarvis income projects log --id <id> --hours 2 --revenue 150
jarvis income projects report
jarvis income projects today

jarvis income briefing today
```

### Read-only API endpoints

In `src/jarvis/server/api.py`, alongside the existing `/hud/career*` routes:

```
GET  /hud/income                 -> combined snapshot (opportunities, watchlist,
                                     portfolio summary, projects summary)
GET  /hud/income/opportunities
GET  /hud/income/watchlist
GET  /hud/income/portfolio
GET  /hud/income/projects
GET  /hud/income/briefing        -> money_briefing "today" output
POST /hud/income/opportunities   -> add/update an opportunity (local file only)
POST /hud/income/watchlist       -> add/remove a watchlist symbol (local file only)
POST /hud/income/portfolio       -> set user-entered holdings (local file only)
POST /hud/income/projects/log    -> log hours/revenue/expense entry
```

All `GET` routes are pure reads of local JSON. `POST` routes only write to
the local `~/.jarvis/income/*.json` files — never call a brokerage, never
place an order, never move money.

### Dashboard: INCOME + CAREER cards

In `frontend/src/pages/IronManCircularHUD.tsx` (and the mock/demo data
block), add an **INCOME OS** card next to the existing **CAREER OS** card:

- Header disclaimer strip: *"Research & tracking only — not financial
  advice."*
- Sections: Opportunities (count by status), Watchlist (symbol count),
  Portfolio (user-entered holdings count + as-of date, no live trading link),
  Projects (active count + this week's hours/revenue), and a "TODAY" button
  that calls `/hud/income/briefing`.
- The existing CAREER OS card stays as-is; Income OS is additive, not a
  replacement, so job-search and money-tracking sit side by side in the HUD
  under one "Money" section of the morning brief.

### Acceptance checklist — Part 2

- [x] `src/jarvis/tools/income_tools.py` with the 4 tools registered in
      `src/jarvis/tools/registry.py`.
- [x] Local files created under `~/.jarvis/income/` on first use; no
      PostgreSQL, no new external services required to run the basics.
- [x] `jarvis income ...` CLI group works end-to-end for every action listed
      above (verified manually: opportunities/watchlist/portfolio/projects/
      briefing all round-trip correctly).
- [x] `/hud/income*` endpoints exist, are read-only for `GET`, and `POST`
      routes only touch local JSON (verified with a live FastAPI TestClient
      and a running `uvicorn` + Vite dev server).
- [x] INCOME OS card added to the Circular HUD next to CAREER OS, **and** a
      compact "CAREER + INCOME OS" card added to the default landing
      dashboard (`JarvisDashboard.tsx`) so it's visible immediately on load,
      not only in the Circular HUD view. Both read live data via
      `/hud/career` + `/hud/income` and fall back to sample data if the API
      isn't reachable (e.g. the static GitHub Pages demo).
- [x] Every investment-related tool output and dashboard card visibly states
      it is not financial advice.
- [x] No code path places a trade, connects to a brokerage for execution, or
      stores brokerage credentials — confirmed by code review of
      `income_tools.py` (only local JSON read/write + the existing
      `web_search` tool for optional news lookups).
- [x] Unit tests added under `tests/test_income_tools.py` for all 4 tools
      (CRUD flows, registry wiring, local-JSON-only storage, and disclaimer
      presence on every `investment_research` response). Full suite: 36/36
      passing.
- [x] `docs/INCOME_OS.md` written describing the feature (same style as
      `docs/BUSINESS_OS.md` / `docs/JAUTOMATIC_INTEGRATION.md`).

**Implementation status: done in this session** (was previously scoped for a
future session in Part 3; built directly here instead). Part 3's prompt below
is kept for reference / for extending Income OS further, but the core spec is
now implemented on `arena/01a0e7bb-jarvis`.

---

## Part 3 — Copy-paste prompt for a new coding session

Paste the block below verbatim into a fresh Arena coding session on this
repo to implement Part 2 in full and double-check Part 1.

```text
Implement the Income OS for JARVIS and finalize the JAUTOMATIC connection, per
docs/INCOME_OS_AND_JAUTOMATIC_SPEC.md in this repo. Read that file first — it
is the source of truth for scope, data model, CLI, API, and guardrails.

Part A — Verify JAUTOMATIC connection (should already work):
1. Confirm src/jarvis/connectors/jautomatic.py finds a checkout named either
   `JAUTOMATIC` or `JAUTOMATIC-JOB-SEARCH` (this fix already landed — just
   re-verify with tests, don't re-do it).
2. Run: jarvis career paths / status / mode --set seeking / today / followups
   / training / postgres, and confirm sensible output. Report what you find.

Part B — Build the Income OS (new capability), following the spec's Part 2
exactly:
1. Create src/jarvis/tools/income_tools.py with 4 BaseTool subclasses:
   - income_opportunities (find/track online gigs, freelance work, grants,
     bounties matched to skills; uses tavily_search/ddgs_search if available,
     degrades gracefully if not)
   - investment_research (user-entered watchlist + user-entered portfolio +
     saved news/research summaries — NOT live brokerage-synced, NOT advice)
   - income_projects (track hours/revenue/expenses/ROI per side project)
   - money_briefing (daily aggregator combining career_os + the above for
     the HUD morning brief)
   Register them in src/jarvis/tools/registry.py next to career_os.
2. Local-first storage only: JSON files under ~/.jarvis/income/ (respecting
   JARVIS_HOME like career.json does). No PostgreSQL. No new external
   service dependency for the core feature to work.
3. Add a `jarvis income ...` Click command group in src/jarvis/cli/main.py
   mirroring the existing `jarvis career ...` group, covering every
   subcommand listed in the spec's Part 2 CLI section.
4. Add read-only GET /hud/income* endpoints (plus narrowly-scoped local-file
   POST endpoints for opportunities/watchlist/portfolio/projects) in
   src/jarvis/server/api.py, following the existing /hud/career* pattern.
5. Add an INCOME OS card to frontend/src/pages/IronManCircularHUD.tsx next to
   the existing CAREER OS card, including its mock/demo data branch, with a
   visible "not financial advice" disclaimer on the card and in every
   investment-related tool response.
6. Guardrails — hard requirements, verify explicitly before finishing:
   - No code path executes a trade, connects to a brokerage/exchange for
     order placement, or stores brokerage/exchange credentials.
   - No PostgreSQL or other new database server is introduced.
   - Every investment-related output includes a clear "informational only,
     not financial advice" style disclaimer.
   - All new tools that mutate state require approval / confirmation the
     same way career_os does.
7. Add unit tests under tests/ (one file per tool area is fine) covering
   normal CRUD flows and asserting the disclaimer text is present in
   investment_research output, following the existing test style in
   tests/test_jautomatic_integration.py and tests/test_basic.py.
8. Write docs/INCOME_OS.md describing the feature, env vars (if any), CLI,
   API, and guardrails, matching the style of docs/BUSINESS_OS.md and
   docs/JAUTOMATIC_INTEGRATION.md.
9. Run the full test suite (pytest) and fix anything broken. Keep changes
   scoped to this feature; do not touch unrelated modules.
10. Open a PR against main with a clear summary, calling out explicitly that
    this is a research/tracking system with no automated trading.

Work on the current session's branch, commit as you go, and push when done.
```

---

### Bottom line

- **Job search** (including "works while I'm still looking for a job" via
  `seeking` mode) is already implemented in this repo and just needed one
  connector fix — now applied — plus your own `JAUTOMATIC_REPO` /
  `JAUTOMATIC_DATA_DIR` env vars pointed at your real JAUTOMATIC checkout and
  workspace.
- **Investment + online-income tracking** is fully feasible to build with the
  existing architecture (local JSON, `BaseTool` + Click + FastAPI + HUD card
  pattern already proven by Career OS and Business OS). It is scoped as a
  **research / planning / tracking copilot**, never an autonomous trader —
  guardrails above are load-bearing, not optional polish.
