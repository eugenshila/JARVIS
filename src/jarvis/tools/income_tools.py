"""Income OS tools — online income + investment RESEARCH and TRACKING.

Guardrails (see docs/INCOME_OS.md):
  * Research / planning / tracking only. Nothing here places a trade,
    connects to a brokerage/exchange for order execution, or stores
    brokerage credentials.
  * Not financial advice. Every investment-related response carries a
    disclaimer.
  * Local-first: everything is stored as JSON under ~/.jarvis/income/
    (or $JARVIS_HOME/income/). No PostgreSQL, no external database.
  * Watchlist/portfolio data is entered by the user, never auto-synced from
    a live brokerage account.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from jarvis.core.config import get_home
from jarvis.tools.base import BaseTool, ToolSpec


DISCLAIMER = (
    "\n\n⚠️ Informational only — not financial advice. JARVIS is not a licensed "
    "financial advisor, broker, or tax professional. You are responsible for your "
    "own investment decisions. No trades are placed automatically; nothing here "
    "connects to a brokerage or exchange."
)

OPPORTUNITY_STATUSES = {"discovered", "saved", "applied", "won", "passed"}


# --------------------------------------------------------------------------- #
# Storage helpers — plain local JSON files, no PostgreSQL, no server required
# --------------------------------------------------------------------------- #

def income_dir() -> Path:
    home = get_home()
    d = home / "income"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_list(filename: str) -> list[dict[str, Any]]:
    path = income_dir() / filename
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def _save_list(filename: str, items: list[dict[str, Any]]) -> None:
    (income_dir() / filename).write_text(json.dumps(items, indent=2), encoding="utf-8")


def _load_dict(filename: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    path = income_dir() / filename
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return dict(default or {})


def _save_dict(filename: str, data: dict[str, Any]) -> None:
    (income_dir() / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _today() -> str:
    return date.today().isoformat()


def _skills_from_profile() -> list[str]:
    """Best-effort: reuse the JAUTOMATIC profile's skills if present."""
    try:
        from jarvis.connectors.jautomatic import JAutomaticConnector

        profile = JAutomaticConnector().profile_summary()
        skills = profile.get("skills") or []
        if isinstance(skills, list) and skills:
            return [str(s) for s in skills][:8]
    except Exception:
        pass
    settings = _load_dict("settings.json")
    skills = settings.get("skills") or []
    return [str(s) for s in skills][:8] if isinstance(skills, list) else []


def _web_search(query: str) -> str:
    """Best-effort search via the existing hybrid web_search tool. Degrades
    gracefully (no API key required) instead of failing."""
    try:
        from jarvis.tools.registry import get_tool

        tool = get_tool("web_search")
        if tool:
            return tool.run(query=query, max_results=5)
    except Exception as exc:
        return f"[search unavailable: {exc}]"
    return "[web_search tool not available]"


# --------------------------------------------------------------------------- #
# 1. income_opportunities — online gigs / freelance work / grants / bounties
# --------------------------------------------------------------------------- #

class IncomeOpportunitiesTool(BaseTool):
    spec = ToolSpec(
        name="income_opportunities",
        description=(
            "Find and track online income opportunities (freelance gigs, contracts, "
            "grants, bounties) matched to your skills. Read/search only — never "
            "auto-applies or submits proposals on your behalf."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["find", "list", "add", "status", "today"],
                    "default": "list",
                },
                "query": {"type": "string", "description": "Search query for action=find"},
                "title": {"type": "string"},
                "url": {"type": "string"},
                "source": {"type": "string"},
                "type": {"type": "string", "enum": ["gig", "grant", "bounty", "contract"], "default": "gig"},
                "est_value": {"type": "string", "description": "Estimated payout, free text"},
                "notes": {"type": "string"},
                "id": {"type": "string", "description": "Opportunity id for action=status"},
                "set_status": {
                    "type": "string",
                    "enum": sorted(OPPORTUNITY_STATUSES),
                    "description": "New status for action=status",
                },
            },
            "required": [],
        },
        requires_approval=True,
    )

    FILE = "opportunities.json"

    def run(self, action: str = "list", **kw: Any) -> str:
        action = (action or "list").lower()
        if action == "find":
            return self._find(kw.get("query", ""))
        if action == "add":
            return self._add(kw)
        if action == "status":
            return self._status(kw.get("id", ""), kw.get("set_status", ""))
        if action == "today":
            return self._today_plan()
        return self._list()

    def _find(self, query: str) -> str:
        query = query.strip()
        if not query:
            skills = _skills_from_profile()
            query = (
                f"remote freelance gigs for {', '.join(skills[:3])}" if skills
                else "remote freelance gigs beginner friendly"
            )
        result = _web_search(f"{query} remote freelance OR contract OR grant apply")
        items = _load_list(self.FILE)
        entry = {
            "id": _new_id(),
            "title": f"Search: {query}",
            "source": "web_search",
            "url": "",
            "type": "gig",
            "est_value": "",
            "skills_match": _skills_from_profile(),
            "status": "discovered",
            "notes": result[:2000],
            "added_at": _now(),
        }
        items.append(entry)
        _save_list(self.FILE, items)
        return (
            f"🔎 **Income Opportunities — search results for:** `{query}`\n\n{result}\n\n"
            f"Saved as opportunity `{entry['id']}` (status: discovered). Review it, then "
            "`income opportunities status --id {id} --set saved` to track one you like.\n"
            "JARVIS does not auto-apply or submit proposals for you." + DISCLAIMER
        )

    def _add(self, kw: dict[str, Any]) -> str:
        items = _load_list(self.FILE)
        entry = {
            "id": _new_id(),
            "title": kw.get("title") or "Untitled opportunity",
            "source": kw.get("source") or "manual",
            "url": kw.get("url") or "",
            "type": kw.get("type") or "gig",
            "est_value": kw.get("est_value") or "",
            "skills_match": _skills_from_profile(),
            "status": "saved",
            "notes": kw.get("notes") or "",
            "added_at": _now(),
        }
        items.append(entry)
        _save_list(self.FILE, items)
        return f"✅ Added opportunity `{entry['id']}` — {entry['title']} (status: saved)."

    def _status(self, opp_id: str, new_status: str) -> str:
        if not opp_id:
            return "Provide --id of the opportunity to update."
        new_status = (new_status or "").lower()
        if new_status not in OPPORTUNITY_STATUSES:
            return f"Unknown status '{new_status}'. Use one of: {', '.join(sorted(OPPORTUNITY_STATUSES))}."
        items = _load_list(self.FILE)
        for item in items:
            if item.get("id") == opp_id:
                item["status"] = new_status
                item["updated_at"] = _now()
                _save_list(self.FILE, items)
                return f"Opportunity `{opp_id}` ({item.get('title')}) marked **{new_status}**."
        return f"No opportunity found with id `{opp_id}`."

    def _list(self) -> str:
        items = _load_list(self.FILE)
        if not items:
            return (
                "No income opportunities tracked yet, Sir. Try `income opportunities find "
                "--query \"...\"` or `income opportunities add`."
            )
        by_status: dict[str, int] = {}
        for item in items:
            by_status[item.get("status", "discovered")] = by_status.get(item.get("status", "discovered"), 0) + 1
        lines = [f"💰 **Income Opportunities — {len(items)} tracked**", ""]
        for status, count in sorted(by_status.items()):
            lines.append(f"  • {status}: {count}")
        lines.append("")
        for item in items[-10:]:
            lines.append(
                f"  • `{item.get('id')}` [{item.get('status')}] {item.get('title')} "
                f"({item.get('type')}) {item.get('url') or ''}".rstrip()
            )
        return "\n".join(lines)

    def _today_plan(self) -> str:
        items = [i for i in _load_list(self.FILE) if i.get("status") in {"discovered", "saved"}]
        tasks: list[str] = []
        if items:
            tasks.append(f"Review opportunity `{items[-1]['id']}` — {items[-1]['title']} — and decide saved/applied/passed.")
        tasks.append("Spend 20-30 minutes searching for one new gig/grant matched to your skills, then stop.")
        tasks.append("Update one profile/portfolio asset (bio, rate card, sample) that helps future applications.")
        tasks = tasks[:3]
        lines = ["📅 **Income Opportunities — Today's plan**", "", "ADHD rule: max 3 income MITs."]
        for idx, task in enumerate(tasks, 1):
            lines.append(f"{idx}. {task}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 2. investment_research — watchlist + user-entered portfolio + news summaries
# --------------------------------------------------------------------------- #

class InvestmentResearchTool(BaseTool):
    spec = ToolSpec(
        name="investment_research",
        description=(
            "Investment RESEARCH copilot: a watchlist you curate, a portfolio you enter "
            "yourself, and saved news/research summaries. NOT financial advice, NOT "
            "connected to any brokerage, and NEVER places trades."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "watchlist_add", "watchlist_remove", "watchlist",
                        "portfolio_set", "portfolio",
                        "research", "notes",
                    ],
                    "default": "watchlist",
                },
                "symbol": {"type": "string"},
                "note": {"type": "string"},
                "quantity": {"type": "number"},
                "cost_basis": {"type": "number"},
                "current_price": {"type": "number", "description": "Optional, user-entered current price"},
                "as_of": {"type": "string", "description": "ISO date; defaults to today"},
            },
            "required": [],
        },
        requires_approval=True,
    )

    WATCHLIST = "watchlist.json"
    PORTFOLIO = "portfolio.json"
    NOTES = "research_notes.json"

    def run(self, action: str = "watchlist", **kw: Any) -> str:
        action = (action or "watchlist").lower()
        symbol = (kw.get("symbol") or "").upper().strip()
        if action == "watchlist_add":
            return self._watchlist_add(symbol, kw.get("note", ""))
        if action == "watchlist_remove":
            return self._watchlist_remove(symbol)
        if action == "portfolio_set":
            return self._portfolio_set(symbol, kw)
        if action == "portfolio":
            return self._portfolio()
        if action == "research":
            return self._research(symbol)
        if action == "notes":
            return self._notes()
        return self._watchlist()

    def _watchlist_add(self, symbol: str, note: str) -> str:
        if not symbol:
            return "Provide --symbol to add to the watchlist." + DISCLAIMER
        items = _load_list(self.WATCHLIST)
        if any(i.get("symbol") == symbol for i in items):
            return f"`{symbol}` is already on the watchlist." + DISCLAIMER
        items.append({"symbol": symbol, "note": note or "", "added_at": _now()})
        _save_list(self.WATCHLIST, items)
        return f"Added `{symbol}` to your watchlist ({len(items)} total)." + DISCLAIMER

    def _watchlist_remove(self, symbol: str) -> str:
        items = _load_list(self.WATCHLIST)
        remaining = [i for i in items if i.get("symbol") != symbol]
        if len(remaining) == len(items):
            return f"`{symbol}` was not on the watchlist."
        _save_list(self.WATCHLIST, remaining)
        return f"Removed `{symbol}` from the watchlist ({len(remaining)} remaining)."

    def _watchlist(self) -> str:
        items = _load_list(self.WATCHLIST)
        if not items:
            return "Watchlist is empty. Add a symbol: `income watchlist add --symbol AAPL`." + DISCLAIMER
        lines = [f"👀 **Watchlist — {len(items)} symbols (user-curated, not advice)**", ""]
        for item in items:
            note = f" — {item.get('note')}" if item.get("note") else ""
            lines.append(f"  • {item.get('symbol')}{note}")
        return "\n".join(lines) + DISCLAIMER

    def _portfolio_set(self, symbol: str, kw: dict[str, Any]) -> str:
        if not symbol:
            return "Provide --symbol to set a holding." + DISCLAIMER
        holdings = _load_list(self.PORTFOLIO)
        entry = {
            "symbol": symbol,
            "quantity": float(kw.get("quantity") or 0),
            "cost_basis": float(kw.get("cost_basis") or 0),
            "current_price": (float(kw["current_price"]) if kw.get("current_price") not in (None, "") else None),
            "as_of": kw.get("as_of") or _today(),
        }
        holdings = [h for h in holdings if h.get("symbol") != symbol]
        holdings.append(entry)
        _save_list(self.PORTFOLIO, holdings)
        return (
            f"Saved holding `{symbol}`: qty {entry['quantity']}, cost basis {entry['cost_basis']} "
            f"(as of {entry['as_of']}). This is data you entered — not synced from a brokerage."
            + DISCLAIMER
        )

    def _portfolio(self) -> str:
        holdings = _load_list(self.PORTFOLIO)
        if not holdings:
            return "No holdings entered yet. `income portfolio set --symbol AAPL --quantity 10 --cost-basis 150`." + DISCLAIMER
        lines = ["📊 **Portfolio (user-entered, not live-synced)**", ""]
        total_cost = 0.0
        total_value = 0.0
        has_price = False
        for h in holdings:
            qty = h.get("quantity", 0)
            cost_basis = h.get("cost_basis", 0)
            price = h.get("current_price")
            cost_total = qty * cost_basis
            total_cost += cost_total
            line = f"  • {h.get('symbol')}: qty {qty}, cost basis {cost_basis} (as of {h.get('as_of')})"
            if price is not None:
                has_price = True
                value = qty * price
                total_value += value
                pl = value - cost_total
                pl_pct = (pl / cost_total * 100) if cost_total else 0.0
                line += f" — entered price {price} → value {value:.2f}, P/L {pl:+.2f} ({pl_pct:+.1f}%)"
            lines.append(line)
        lines.append("")
        lines.append(f"Total cost basis: {total_cost:.2f}")
        if has_price:
            lines.append(f"Total value at entered prices: {total_value:.2f}")
        lines.append("Prices above are whatever you entered — JARVIS does not fetch live brokerage prices or place trades.")
        return "\n".join(lines) + DISCLAIMER

    def _research(self, symbol: str) -> str:
        if not symbol:
            return "Provide --symbol to research." + DISCLAIMER
        summary = _web_search(f"{symbol} stock news recent")
        notes = _load_list(self.NOTES)
        record = {"symbol": symbol, "date": _today(), "summary": summary[:3000], "saved_at": _now()}
        notes.append(record)
        _save_list(self.NOTES, notes)
        return f"📰 **Research summary — {symbol}** ({_today()})\n\n{summary}\n\nSaved to research notes." + DISCLAIMER

    def _notes(self) -> str:
        notes = _load_list(self.NOTES)
        if not notes:
            return "No saved research notes yet. `income research --symbol AAPL`." + DISCLAIMER
        lines = [f"🗂 **Saved research notes — {len(notes)}**", ""]
        for n in notes[-10:]:
            lines.append(f"  • {n.get('date')} — {n.get('symbol')}: {n.get('summary', '')[:120]}...")
        return "\n".join(lines) + DISCLAIMER


# --------------------------------------------------------------------------- #
# 3. income_projects — hours / revenue / ROI tracking for side projects
# --------------------------------------------------------------------------- #

class IncomeProjectsTool(BaseTool):
    spec = ToolSpec(
        name="income_projects",
        description="Track hours, revenue, expenses, and ROI for side projects / freelance work.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add", "log", "list", "report", "today"], "default": "list"},
                "id": {"type": "string"},
                "name": {"type": "string"},
                "hours": {"type": "number", "default": 0},
                "revenue": {"type": "number", "default": 0},
                "expense": {"type": "number", "default": 0},
                "note": {"type": "string"},
            },
            "required": [],
        },
        requires_approval=True,
    )

    FILE = "projects.json"

    def run(self, action: str = "list", **kw: Any) -> str:
        action = (action or "list").lower()
        if action == "add":
            return self._add(kw.get("name", ""))
        if action == "log":
            return self._log(kw)
        if action == "report":
            return self._report()
        if action == "today":
            return self._today_plan()
        return self._list()

    def _add(self, name: str) -> str:
        if not name:
            return "Provide --name for the new project."
        projects = _load_list(self.FILE)
        entry = {"id": _new_id(), "name": name, "status": "active", "entries": [], "created_at": _now()}
        projects.append(entry)
        _save_list(self.FILE, projects)
        return f"✅ Project `{entry['id']}` — {name} created."

    def _log(self, kw: dict[str, Any]) -> str:
        proj_id = kw.get("id", "")
        projects = _load_list(self.FILE)
        for project in projects:
            if project.get("id") == proj_id:
                project.setdefault("entries", []).append({
                    "date": _today(),
                    "hours": float(kw.get("hours") or 0),
                    "revenue": float(kw.get("revenue") or 0),
                    "expense": float(kw.get("expense") or 0),
                    "note": kw.get("note") or "",
                })
                _save_list(self.FILE, projects)
                return f"Logged entry for `{proj_id}` — {project.get('name')}."
        return f"No project found with id `{proj_id}`. Use `income projects list`."

    def _list(self) -> str:
        projects = _load_list(self.FILE)
        if not projects:
            return "No income projects tracked yet. `income projects add --name \"Freelance automation\"`."
        lines = [f"🛠 **Income Projects — {len(projects)}**", ""]
        for p in projects:
            hours = sum(e.get("hours", 0) for e in p.get("entries", []))
            revenue = sum(e.get("revenue", 0) for e in p.get("entries", []))
            lines.append(f"  • `{p.get('id')}` {p.get('name')} — {hours:.1f}h, {revenue:.2f} revenue ({p.get('status')})")
        return "\n".join(lines)

    def _report(self) -> str:
        projects = _load_list(self.FILE)
        if not projects:
            return "No income projects tracked yet."
        lines = ["📈 **Income Projects — Report**", ""]
        for p in projects:
            entries = p.get("entries", [])
            hours = sum(e.get("hours", 0) for e in entries)
            revenue = sum(e.get("revenue", 0) for e in entries)
            expense = sum(e.get("expense", 0) for e in entries)
            net = revenue - expense
            rate = (revenue / hours) if hours else 0.0
            lines.append(
                f"  • {p.get('name')}: {hours:.1f}h · revenue {revenue:.2f} · expenses {expense:.2f} "
                f"· net {net:.2f} · {rate:.2f}/hour"
            )
        return "\n".join(lines)

    def _today_plan(self) -> str:
        projects = [p for p in _load_list(self.FILE) if p.get("status") == "active"]
        if not projects:
            return "No active income projects. `income projects add --name \"...\"` to start one."

        def rate(p: dict[str, Any]) -> float:
            entries = p.get("entries", [])
            hours = sum(e.get("hours", 0) for e in entries)
            revenue = sum(e.get("revenue", 0) for e in entries)
            return (revenue / hours) if hours else 0.0

        best = max(projects, key=rate)
        lines = [
            "📅 **Income Projects — Today's plan**",
            "",
            "ADHD rule: pick one focus block for income-generating work.",
            f"1. Spend one focus block on `{best['id']}` — {best.get('name')} (best $/hour so far: {rate(best):.2f}).",
            "2. Log the session afterwards: `income projects log --id <id> --hours <h> --revenue <r>`.",
        ]
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 4. money_briefing — daily money section for the HUD morning brief
# --------------------------------------------------------------------------- #

class MoneyBriefingTool(BaseTool):
    spec = ToolSpec(
        name="money_briefing",
        description=(
            "Daily money briefing combining Career OS, income opportunities, income "
            "projects, and the investment watchlist into one HUD-ready summary. "
            "Read-only aggregator — not financial advice."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["today"], "default": "today"},
            },
            "required": [],
        },
    )

    def run(self, action: str = "today", **kw: Any) -> str:
        return self._today()

    def _today(self) -> str:
        lines = ["💵 **Money Briefing — Today**", ""]

        # Career OS
        try:
            from jarvis.tools.career_tools import CareerTool, _load_career_config

            career_stats = CareerTool()
            mode = _load_career_config().get("mode", "seeking")
            stats = career_stats.run(action="status")
            due = 0
            try:
                from jarvis.connectors.jautomatic import JAutomaticConnector

                due = JAutomaticConnector().stats().get("follow_ups_due", 0)
            except Exception:
                pass
            lines.append(f"**Career** (mode: {mode}) — follow-ups due: {due}")
        except Exception:
            lines.append("**Career** — Career OS unavailable.")

        # Income opportunities
        opps = _load_list("opportunities.json")
        active_opps = [o for o in opps if o.get("status") in {"discovered", "saved"}]
        lines.append(f"**Income opportunities** — {len(active_opps)} awaiting review out of {len(opps)} tracked")
        if active_opps:
            top = active_opps[-1]
            lines.append(f"  • Next: `{top.get('id')}` {top.get('title')}")

        # Income projects
        projects = [p for p in _load_list("projects.json") if p.get("status") == "active"]
        if projects:
            lines.append(f"**Income projects** — {len(projects)} active; run `jarvis income projects today` for a suggestion.")
        else:
            lines.append("**Income projects** — none tracked yet.")

        # Watchlist / research
        watchlist = _load_list("watchlist.json")
        notes = _load_list("research_notes.json")
        cutoff = datetime.now() - timedelta(hours=24)
        recent_notes = []
        for n in notes:
            try:
                if datetime.fromisoformat(n.get("saved_at", "")) >= cutoff:
                    recent_notes.append(n)
            except Exception:
                continue
        symbol_word = "symbol" if len(watchlist) == 1 else "symbols"
        lines.append(f"**Watchlist** — {len(watchlist)} {symbol_word}, {len(recent_notes)} research notes saved in the last 24h")

        lines.append(DISCLAIMER.strip())
        return "\n".join(lines)
