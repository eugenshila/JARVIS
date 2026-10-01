"""
Read-only data sources for the morning briefing.

Every adapter here answers the same question — "what should he know before he
starts?" — and every one of them is strictly observational. None of them can
send, reply, delete, or trade; the capability simply is not written. Where a
vendor SDK would hand us a `.Send()` or `.Delete()`, the adapter touches only
the properties it needs and routes the attempt through the guard first.

Each adapter returns a `Summary`: a short headline the routine can speak, a
handful of bullet lines, and a `degraded` flag. Degraded means "this is a
snapshot or the source was unreachable" and the routine says so out loud,
because a briefing that quietly omits a source is worse than no briefing.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from plugins._jmorning_safety import BlockedAction, guard, http_get_json

DATA_DIR = Path(__file__).resolve().parent.parent / "memory"


def _cfg(ns: str, key: str, default=None):
    try:
        from memory.config_manager import get_plugin_setting
        val = get_plugin_setting(ns, key, default)
    except Exception:
        val = default
    return default if val in (None, "") else val


@dataclass
class Summary:
    source: str
    headline: str = ""
    lines: list[str] = field(default_factory=list)
    degraded: bool = False
    note: str = ""

    def text(self) -> str:
        head = f"{self.source}: {self.headline}"
        if self.degraded and self.note:
            head += f" ({self.note})"
        body = "".join(f"\n    • {l}" for l in self.lines)
        return head + body


# ───────────────────────── Outlook (desktop, COM) ─────────────────────────

# Outlook's MAPI item properties we are allowed to touch. Listing them makes the
# read-only intent reviewable at a glance — and means an item is never passed
# anywhere that could call .Send(), .Delete() or .Reply() on it.
_MAIL_FIELDS = ("Subject", "SenderName", "ReceivedTime", "UnRead", "Importance", "To")

# Outlook's default folder ids (olFolderInbox / olFolderCalendar).
_OL_INBOX, _OL_CALENDAR = 6, 9


def _outlook_app():
    """Attach to the user's already-running Outlook; never start a new profile."""
    if os.name != "nt":
        raise OSError("Outlook desktop automation is Windows-only.")
    import win32com.client  # pywin32, only imported on Windows
    try:
        return win32com.client.GetActiveObject("Outlook.Application")
    except Exception:
        return win32com.client.Dispatch("Outlook.Application")


def _iter_recent(folder, hours: int, limit: int):
    """Newest-first items from the last `hours`, read via Restrict so we never
    walk a 50k-item mailbox."""
    items = folder.Items
    items.Sort("[ReceivedTime]", True)
    cutoff = datetime.now() - timedelta(hours=hours)
    try:
        items = items.Restrict(
            "[ReceivedTime] >= '" + cutoff.strftime("%m/%d/%Y %H:%M %p") + "'")
    except Exception:
        pass
    out = []
    for item in items:
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _accounts_in_scope(session, wanted: str) -> list:
    """`wanted` is 'all', 'gmail', or a comma-separated list of addresses."""
    stores = []
    for i in range(1, session.Folders.Count + 1):
        stores.append(session.Folders.Item(i))
    if wanted == "all":
        return stores
    if wanted == "gmail":
        return [s for s in stores if "gmail" in str(s.Name).lower()
                or "googlemail" in str(s.Name).lower()]
    wants = [w.strip().lower() for w in wanted.split(",") if w.strip()]
    return [s for s in stores if any(w in str(s.Name).lower() for w in wants)] or stores


def _mail_summary(scope: str, label: str) -> Summary:
    """Shared engine for the Outlook and Gmail-via-Outlook summaries."""
    guard(f"read recent mail headers from Outlook ({label})")
    hours = int(_cfg("outlook", "lookback_hours", 16) or 16)
    limit = int(_cfg("outlook", "max_items", 40) or 40)
    try:
        session = _outlook_app().GetNamespace("MAPI")
        stores = _accounts_in_scope(session, scope)
        if not stores:
            return Summary(label, "no matching account found in Outlook.",
                           degraded=True, note="check the account filter")
        unread, flagged, senders, subjects = 0, 0, {}, []
        for store in stores:
            try:
                inbox = store.Folders.Item("Inbox")
            except Exception:
                try:
                    inbox = session.GetDefaultFolder(_OL_INBOX)
                except Exception:
                    continue
            for item in _iter_recent(inbox, hours, limit):
                try:
                    if not getattr(item, "UnRead", False):
                        continue
                    unread += 1
                    sender = str(getattr(item, "SenderName", "") or "unknown")
                    senders[sender] = senders.get(sender, 0) + 1
                    if int(getattr(item, "Importance", 1) or 1) >= 2:
                        flagged += 1
                        subjects.append(f"⚑ {sender}: {getattr(item, 'Subject', '')}")
                    elif len(subjects) < 5:
                        subjects.append(f"{sender}: {getattr(item, 'Subject', '')}")
                except Exception:
                    continue
        top = ", ".join(f"{n} ({c})" for n, c in
                        sorted(senders.items(), key=lambda kv: -kv[1])[:3])
        head = f"{unread} unread in the last {hours}h"
        if flagged:
            head += f", {flagged} marked high importance"
        lines = subjects[:6]
        if top:
            lines.append(f"Most active: {top}")
        return Summary(label, head + ".", lines)
    except Exception as e:
        return Summary(label, "not reachable.", degraded=True, note=str(e)[:90])


def outlook_summary() -> Summary:
    return _mail_summary(str(_cfg("outlook", "accounts", "all")), "Outlook")


def gmail_summary() -> Summary:
    """
    Gmail is read through the Outlook desktop profile, because that is where the
    user's Gmail accounts are already configured and authenticated. No separate
    OAuth, no second copy of the credentials, and it inherits the same read-only
    property whitelist as every other mailbox.
    """
    return _mail_summary(str(_cfg("outlook", "gmail_accounts", "gmail")), "Gmail")


def calendar_summary() -> Summary:
    guard("read today's calendar entries from Outlook")
    try:
        session = _outlook_app().GetNamespace("MAPI")
        cal = session.GetDefaultFolder(_OL_CALENDAR)
        items = cal.Items
        items.IncludeRecurrences = True
        items.Sort("[Start]")
        start = datetime.now().replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
        items = items.Restrict(
            f"[Start] >= '{start:%m/%d/%Y %H:%M %p}' AND [End] <= '{end:%m/%d/%Y %H:%M %p}'")
        lines = []
        for item in items:
            lines.append(f"{item.Start.strftime('%H:%M')} {item.Subject}")
            if len(lines) >= 8:
                break
        return Summary("Calendar", f"{len(lines)} event(s) today.", lines)
    except Exception as e:
        return Summary("Calendar", "not reachable.", degraded=True, note=str(e)[:90])


# ───────────────────────── WhatsApp Business ─────────────────────────

def whatsapp_summary() -> Summary:
    """
    Read-only WhatsApp Business summary.

    Worth being precise about what is and isn't possible: Meta's Cloud API does
    not expose an endpoint to *list* inbound messages — they only ever arrive on
    your webhook. So this adapter does two things:
      * GETs the phone-number resource for account health (quality rating,
        messaging limit, verification) — genuinely useful at 6am, because a
        flagged number is a business problem;
      * reads the inbox file your webhook writes, if you point `inbox_file` at
        one, to count what came in overnight.
    There is no send path here, and there never will be.
    """
    guard("read WhatsApp Business account status and the local webhook inbox")
    lines: list[str] = []
    degraded, note = False, ""

    token = _cfg("whatsapp", "access_token", "")
    phone_id = _cfg("whatsapp", "phone_number_id", "")
    version = _cfg("whatsapp", "api_version", "v21.0")
    if token and phone_id:
        try:
            data = http_get_json(
                f"https://graph.facebook.com/{version}/{phone_id}",
                params={"fields": "display_phone_number,verified_name,quality_rating,"
                                  "messaging_limit_tier,code_verification_status"},
                headers={"Authorization": f"Bearer {token}"})
            lines.append(f"Number {data.get('display_phone_number','?')} "
                         f"({data.get('verified_name','?')}) — quality "
                         f"{data.get('quality_rating','unknown')}, tier "
                         f"{data.get('messaging_limit_tier','unknown')}")
        except Exception as e:
            degraded, note = True, f"Cloud API unreachable: {str(e)[:60]}"
    else:
        degraded, note = True, "no access token configured"

    inbox = _cfg("whatsapp", "inbox_file", "")
    unread, recent = 0, []
    if inbox:
        try:
            msgs = json.loads(Path(inbox).read_text("utf-8"))
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=16)).timestamp()
            for m in msgs if isinstance(msgs, list) else msgs.get("messages", []):
                ts = float(m.get("timestamp", 0) or 0)
                if ts >= cutoff:
                    unread += 1
                    if len(recent) < 5:
                        recent.append(f"{m.get('from_name') or m.get('from','?')}: "
                                      f"{str(m.get('text',''))[:70]}")
            lines.append(f"{unread} inbound message(s) overnight")
            lines.extend(recent)
        except Exception as e:
            degraded = True
            note = note or f"inbox file unreadable: {str(e)[:60]}"

    head = "account healthy." if lines and not degraded else "status unavailable."
    if unread:
        head = f"{unread} inbound overnight; review in WhatsApp Business."
    return Summary("WhatsApp Business", head, lines, degraded, note)


# ───────────────────────── Market ─────────────────────────

def market_summary() -> Summary:
    """
    Price-watch only. No broker is contacted, no order endpoint exists in this
    file, and the guard would refuse one anyway.
    """
    guard("read market prices for the watchlist")
    symbols = str(_cfg("market", "symbols", "bitcoin,ethereum")).split(",")
    symbols = [s.strip() for s in symbols if s.strip()]
    vs = str(_cfg("market", "currency", "usd")).lower()
    if not symbols:
        return Summary("Market", "no watchlist configured.", degraded=True)
    try:
        data = http_get_json(
            str(_cfg("market", "api_url", "https://api.coingecko.com/api/v3/simple/price")),
            params={"ids": ",".join(symbols), "vs_currencies": vs,
                    "include_24hr_change": "true"})
        lines, movers = [], []
        for sym in symbols:
            d = data.get(sym) or {}
            price = d.get(vs)
            chg = d.get(f"{vs}_24h_change")
            if price is None:
                continue
            arrow = "▲" if (chg or 0) >= 0 else "▼"
            lines.append(f"{sym.title()}: {price:,.2f} {vs.upper()} "
                         f"{arrow}{abs(chg or 0):.2f}% (24h)")
            if chg is not None and abs(chg) >= 5:
                movers.append(sym.title())
        head = (f"{len(lines)} instrument(s) tracked"
                + (f"; big moves in {', '.join(movers)}" if movers else "; nothing dramatic")
                + ".")
        return Summary("Market", head, lines)
    except Exception as e:
        return Summary("Market", "feed unavailable.", degraded=True, note=str(e)[:90])


# ───────────────────────── Shilatech ─────────────────────────

def shilatech_summary() -> Summary:
    """
    Business snapshot for Shilatech. Points at whatever endpoint you configure
    and degrades to a local JSON file so the briefing is never blank.
    """
    guard("read the Shilatech business summary")
    base = _cfg("shilatech", "base_url", "")
    token = _cfg("shilatech", "api_token", "")
    data = None
    if base:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        for path in ("/api/summary", "/api/dashboard", "/summary"):
            try:
                data = http_get_json(str(base).rstrip("/") + path, headers=headers)
                break
            except Exception:
                continue
    degraded = data is None
    if degraded:
        try:
            data = json.loads((DATA_DIR / "shilatech_snapshot.json").read_text("utf-8"))
        except Exception:
            data = {}
    if not data:
        return Summary("Shilatech", "no data source configured.", degraded=True,
                       note="set base_url in plugin settings")
    lines = []
    for key in ("open_tickets", "orders_today", "revenue_today", "overdue_invoices",
                "active_clients", "uptime", "alerts"):
        if key in data:
            lines.append(f"{key.replace('_', ' ').title()}: {data[key]}")
    for extra in (data.get("notes"), data.get("alert")):
        if extra:
            lines.append(str(extra))
    head = str(data.get("headline") or f"{len(lines)} metric(s) reported.")
    return Summary("Shilatech", head, lines, degraded,
                   "local snapshot" if degraded else "")
