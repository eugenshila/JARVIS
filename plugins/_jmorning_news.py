"""Read-only Kenyan news and explicitly labelled marketing advisory."""
from __future__ import annotations
import email.utils, re
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from plugins._jmorning_safety import http_get, http_get_json
from plugins._jmorning_sources import Summary, _cfg

FEED = "https://news.google.com/rss/search"
WEIGHTS = {"nation": 4, "standard": 4, "citizen": 4, "business daily": 4}

def _clean(s): return re.sub(r"\\s+", " ", s or "").strip()
def _source(title):
    return _clean(title.rsplit(" - ", 1)[-1]) if " - " in title else "Unknown source"
def _key(title): return re.sub(r"[^a-z0-9 ]", "", title.lower().rsplit(" - ",1)[0])[:110]

def kenya_news_summary():
    try:
        status, body = http_get(FEED, params={"q":"Kenya", "hl":"en-KE", "gl":"KE", "ceid":"KE:en"}, headers={"User-Agent":"JARVIS morning briefing"})
        if status >= 400: raise OSError(f"HTTP {status}")
        root = ET.fromstring(body)
        grouped = {}
        for item in root.findall(".//item"):
            title = _clean(item.findtext("title")); source = _source(title)
            published = item.findtext("pubDate") or ""
            try: age = (datetime.now(timezone.utc)-email.utils.parsedate_to_datetime(published).astimezone(timezone.utc)).total_seconds()
            except Exception: age = 10**9
            key = _key(title); g = grouped.setdefault(key, {"title":title.rsplit(" - ",1)[0], "sources":set(), "age":age})
            g["sources"].add(source)
        ranked = sorted(grouped.values(), key=lambda x: (sum(WEIGHTS.get(s.lower(),0) for s in x["sources"]), len(x["sources"]), -x["age"]), reverse=True)[:5]
        lines = [f"{x['title']} — {', '.join(sorted(x['sources']))} ({len(x['sources'])} outlet(s))" for x in ranked]
        return Summary("Kenyan news", f"{len(ranked)} top Google News RSS result(s), ranked deterministically.", lines, degraded=not bool(ranked), note="Google News RSS")
    except Exception as e:
        return Summary("Kenyan news", "feed unavailable; no story asserted.", degraded=True, note=str(e)[:90])

def marketing_advisory():
    # Deliberately never presented as fetched news or fact.
    return Summary("ADVISORY — marketing (not fetched fact)", "Ideas only; validate before publishing.", [
        "Use the strongest verified Kenyan customer problem from today's briefing as one educational post.",
        "Test one clear offer with a measurable call to action; do not infer demand from headlines.",
        "No campaign, message, or publication is sent by JARVIS.",
    ], degraded=True, note="ADVISORY ONLY")
