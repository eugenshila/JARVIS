"""Live morning briefing for the JARVIS boot experience.

Sources are intentionally keyless where practical:
- Open-Meteo for weather.
- Yahoo Finance chart endpoint for major market indices.
- Google News RSS for latest headlines.

If a network source is unavailable, the briefing still boots and marks that
section as unavailable instead of blocking JARVIS.
"""
from __future__ import annotations
import json, os, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

DEFAULT_LAT = float(os.environ.get("JARVIS_WEATHER_LAT", "-1.286389"))
DEFAULT_LON = float(os.environ.get("JARVIS_WEATHER_LON", "36.817223"))
DEFAULT_CITY = os.environ.get("JARVIS_WEATHER_CITY", "Nairobi")

def _get(url: str, timeout: float = 6) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent":"JARVIS-SHILATECH/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def weather() -> dict:
    try:
        q=urllib.parse.urlencode({
            "latitude":DEFAULT_LAT,"longitude":DEFAULT_LON,"timezone":"auto",
            "current":"temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "daily":"temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days":1
        })
        d=json.loads(_get("https://api.open-meteo.com/v1/forecast?"+q).decode())
        c=d["current"]; day=d["daily"]
        codes={0:"Clear",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
               45:"Fog",48:"Rime fog",51:"Light drizzle",53:"Drizzle",55:"Heavy drizzle",
               61:"Light rain",63:"Rain",65:"Heavy rain",80:"Rain showers",81:"Rain showers",82:"Heavy showers",
               95:"Thunderstorm",96:"Thunderstorm",99:"Thunderstorm"}
        return {"city":DEFAULT_CITY,"temp":c["temperature_2m"],"feels":c["apparent_temperature"],
                "humidity":c["relative_humidity_2m"],"wind":c["wind_speed_10m"],
                "condition":codes.get(c["weather_code"],"Current conditions"),
                "high":day["temperature_2m_max"][0],"low":day["temperature_2m_min"][0],
                "rain":day["precipitation_probability_max"][0]}
    except Exception as e:
        return {"city":DEFAULT_CITY,"error":str(e)}

def markets() -> list[dict]:
    symbols=[("^GSPC","S&P 500"),("^DJI","Dow Jones"),("^IXIC","Nasdaq")]
    out=[]
    for symbol,label in symbols:
        try:
            url="https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(symbol,safe="")+"?range=1d&interval=1d"
            d=json.loads(_get(url).decode())["chart"]["result"][0]
            meta=d["meta"]; price=meta.get("regularMarketPrice")
            prev=meta.get("previousClose") or meta.get("chartPreviousClose")
            pct=((price-prev)/prev*100) if price is not None and prev else None
            out.append({"label":label,"price":price,"pct":pct})
        except Exception:
            out.append({"label":label,"error":"unavailable"})
    return out

def news() -> list[dict]:
    try:
        url="https://news.google.com/rss?"+urllib.parse.urlencode({"hl":"en-KE","gl":"KE","ceid":"KE:en"})
        root=ET.fromstring(_get(url).decode("utf-8","ignore"))
        items=[]
        for item in root.findall("./channel/item")[:6]:
            items.append({"title":(item.findtext("title") or "").strip(),
                          "source":(item.findtext("source") or "").strip()})
        return items
    except Exception:
        return []

def build_brief(user_name: str = "Sir", tasks: list[str] | None = None) -> dict:
    tasks=tasks or []
    w=weather(); m=markets(); n=news()
    now=datetime.now()
    return {"time":now.strftime("%I:%M %p"),"date":now.strftime("%A, %B %d, %Y"),
            "greeting":("Good morning" if now.hour<12 else "Good afternoon" if now.hour<18 else "Good evening"),
            "user":user_name,"weather":w,"markets":m,"news":n,"tasks":tasks}

def voice_script(brief: dict) -> str:
    w=brief["weather"]; m=brief["markets"]; n=brief["news"]; t=brief["tasks"]
    parts=[f'{brief["greeting"]}, {brief["user"]}. JARVIS is online and all systems are nominal.']
    if "error" not in w:
        parts.append(f'Current weather in {w["city"]}: {w["temp"]:.0f} degrees Celsius, {w["condition"].lower()}, with a high of {w["high"]:.0f} and a low of {w["low"]:.0f}.')
    if t:
        parts.append(f'You have {len(t)} priority tasks. ' + ". ".join(t[:3]) + ".")
    else:
        parts.append("Your task board is ready. No priority tasks have been configured yet.")
    valid=[x for x in m if x.get("price") is not None]
    if valid:
        parts.append("Market snapshot: " + ", ".join(f'{x["label"]} {x["pct"]:+.1f} percent' for x in valid) + ".")
    if n:
        parts.append("I have the latest news headlines ready on the HUD.")
    parts.append("Good to have you back, Sir. What shall we work on first?")
    return " ".join(parts)
