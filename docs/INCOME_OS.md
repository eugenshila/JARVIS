# Income OS — Online Income + Investment Research, Tracking, and Planning

Income OS is a **research, planning, and tracking copilot** for online income
and investing. It follows the same local-first pattern as Career OS
(`docs/JAUTOMATIC_INTEGRATION.md`) and Business OS (`docs/BUSINESS_OS.md`):
plain local JSON files, a `BaseTool` per capability, a `jarvis income ...`
CLI, read-only HUD API routes, and dashboard cards.

## Guardrails — read this first

- **Research / planning / tracking only.** No tool in Income OS places a
  trade, connects to a brokerage or exchange for order execution, or stores
  brokerage/exchange credentials. Watchlist and portfolio data is entered by
  you; it is never synced live from a brokerage account.
- **Not financial advice.** Every investment-related response and dashboard
  card carries a disclaimer: *"Informational only — not financial advice.
  JARVIS is not a licensed financial advisor. You are responsible for your
  own investment decisions."*
- **Local-first, no PostgreSQL.** All state lives in local JSON files under
  `~/.jarvis/income/` (or `$JARVIS_HOME/income/`). No new database server,
  no cloud dependency required for the core feature to work.
- **Read-only APIs.** `GET /hud/income*` only ever reads local files. The
  narrow `POST /hud/income*` routes only append/update those same local
  files — nothing calls a trading API to execute anything.
- **Search is optional and degrades gracefully.** `income_opportunities find`
  and `investment_research research` reuse the existing `web_search` tool
  (Tavily if `TAVILY_API_KEY` is set, else free DuckDuckGo via `ddgs`, else a
  clear "search unavailable" message). Nothing breaks if no search backend is
  installed.

## Local data files

```
~/.jarvis/income/
  opportunities.json     # gigs/grants/bounties/contracts you're tracking
  watchlist.json         # symbols you want to watch (user-curated)
  portfolio.json         # holdings you enter yourself (not live-synced)
  research_notes.json    # saved news/research summaries per symbol
  projects.json          # side projects: hours, revenue, expenses, ROI
  settings.json          # optional: skills list used by `opportunities find`
```

## The 4 tools

Implemented in `src/jarvis/tools/income_tools.py`, registered in
`src/jarvis/tools/registry.py` as `income_opportunities`,
`investment_research`, `income_projects`, `money_briefing`.

1. **`income_opportunities`** — find/track online gigs, freelance contracts,
   grants, and bounties matched to your skills (pulled from the JAUTOMATIC
   profile if present). Actions: `find`, `list`, `add`, `status`, `today`.
2. **`investment_research`** — a watchlist you curate, a portfolio you enter
   yourself, and saved news/research summaries. Actions: `watchlist_add`,
   `watchlist_remove`, `watchlist`, `portfolio_set`, `portfolio`, `research`,
   `notes`. **Not advice** — every response says so.
3. **`income_projects`** — track hours, revenue, expenses, and $/hour ROI for
   side projects. Actions: `add`, `log`, `list`, `report`, `today`.
4. **`money_briefing`** — read-only daily aggregator combining Career OS +
   the three tools above into one HUD-ready "today" summary.

## CLI

```bash
jarvis income opportunities find --query "remote Python automation gigs"
jarvis income opportunities list
jarvis income opportunities add --title "..." --url "..." --type gig
jarvis income opportunities status --id <id> --set applied
jarvis income opportunities today

jarvis income watchlist add --symbol AAPL
jarvis income watchlist remove --symbol AAPL
jarvis income watchlist list

jarvis income portfolio set --symbol AAPL --quantity 10 --cost-basis 150
jarvis income portfolio show

jarvis income research --symbol AAPL
jarvis income notes

jarvis income projects add --name "Freelance automation"
jarvis income projects log --id <id> --hours 2 --revenue 150
jarvis income projects list
jarvis income projects report
jarvis income projects today

jarvis income briefing
```

## HUD API

All `GET` routes are pure reads of local JSON; `POST` routes only write to
those same local files.

```
GET  /hud/income                 combined snapshot (opportunities, watchlist, portfolio, projects)
GET  /hud/income/opportunities
GET  /hud/income/watchlist
GET  /hud/income/portfolio
GET  /hud/income/projects
GET  /hud/income/briefing        money_briefing "today" output
POST /hud/income/opportunities   {action: "add"|"status", ...}
POST /hud/income/watchlist       {action: "add"|"remove", symbol}
POST /hud/income/portfolio       {symbol, quantity, cost_basis, current_price?}
POST /hud/income/projects/log    {id, hours?, revenue?, expense?, note?}
```

`GET /hud/preflight` now also returns an `income` key with the same combined
snapshot, alongside the existing `career` key.

## Dashboard

- **Default landing dashboard** (`frontend/src/pages/JarvisDashboard.tsx`,
  shown on load) has a compact **"CAREER + INCOME OS"** card in the left
  column. It fetches `/hud/career` and `/hud/income` and falls back to
  sample data if the API isn't reachable (e.g. the static GitHub Pages demo).
- **Circular HUD** (`frontend/src/pages/IronManCircularHUD.tsx`, reached via
  HUD → CIRCULAR HUD) has a full **INCOME OS** card next to the existing
  CAREER OS card: opportunity/watchlist/portfolio/project counts, an
  add-to-watchlist input, and a "MONEY BRIEFING" button. Both cards show the
  "research & tracking only — not financial advice" disclaimer.

## Tests

`tests/test_income_tools.py` covers CRUD flows for all 4 tools, registry
wiring, local-JSON-only storage, and asserts the "not financial advice"
disclaimer is present on every `investment_research` response.
