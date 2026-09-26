"""Business Profile — Persistent memory for goals, priorities, workflows, rules, standards.

Stores in ~/.jarvis/business_profile.toml + ~/.jarvis/memory/ for vector search.
This is the brain of JARVIS Business OS — teaches JARVIS your business.
"""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any
import json

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import tomlkit

from jarvis.core.config import get_home

@dataclass
class Goals:
    north_star: str = "Build SHILATECH into leading personal AI company"
    long_term_1y: list[str] = field(default_factory=lambda: [
        "Launch JARVIS hybrid online/offline product for i5-6300U 8GB",
        "Acquire 1000 active users",
        "Establish SHILATECH brand • Malibu Point 10880"
    ])
    short_term_90d: list[str] = field(default_factory=lambda: [
        "Ship modern circular HUD v1.0 matching Iron Man",
        "Implement voice auto-init online/offline",
        "Setup persistent memory + business OS"
    ])
    short_term_30d: list[str] = field(default_factory=lambda: [
        "Fix MSI upgrade issues",
        "Setup OpenAI as primary engine",
        "Teach JARVIS business workflows"
    ])
    personal: list[str] = field(default_factory=lambda: [
        "Good morning routine with 3 MITs",
        "Deep work 2h daily",
        "Ship daily"
    ])

@dataclass
class Priorities:
    # Eisenhower matrix + MITs
    mit_today: list[str] = field(default_factory=lambda: [
        "Ship JARVIS Business OS with OpenAI + memory",
        "Fix modern HUD MSI upgrade",
        "Setup business profile and workflows"
    ])
    urgent_important: list[str] = field(default_factory=lambda: [
        "Customer delivery",
        "Revenue generating tasks",
        "System outages"
    ])
    important_not_urgent: list[str] = field(default_factory=lambda: [
        "Product development",
        "Business OS setup",
        "Learning and documentation"
    ])
    # Business pillars
    pillars: list[str] = field(default_factory=lambda: [
        "Product Excellence — Iron Man quality HUD",
        "Customer Obsession — Solve real problems",
        "SHILATECH Brand — Premium, secure, private",
        "Velocity — Ship fast, iterate"
    ])

@dataclass
class Business:
    name: str = "SHILATECH"
    tagline: str = "Personal AI, On Personal Devices"
    location: str = "Malibu Point 10880"
    mission: str = "Build local-first personal AI that runs on personal devices, private by default, Iron Man quality"
    vision: str = "Every person has JARVIS — helpful, private, voice-enabled, hybrid online/offline"
    values: list[str] = field(default_factory=lambda: [
        "Privacy First — Local-first, nothing leaves device unless user decides",
        "Quality — Iron Man HUD level craftsmanship",
        "Velocity — Ship daily, fix fast",
        "Customer Obsession — Solve real user problems",
        "SHILATECH Standard — Premium, secure, encrypted"
    ])
    products: list[str] = field(default_factory=lambda: [
        "JARVIS Desktop — Modern Circular HUD 13 72 ticks 60 segments",
        "JARVIS Voice — Auto-init online/offline, British voice",
        "JARVIS Business OS — Goals, workflows, persistent memory",
        "JARVIS Hybrid — Online Full Stack vs Offline Basic, user decides"
    ])
    target_customer: str = "Power users, developers, ADHD entrepreneurs who want private local AI"
    revenue_model: str = "Freemium local + Premium cloud OpenAI + Enterprise"

@dataclass
class Workflows:
    daily_routine: list[str] = field(default_factory=lambda: [
        "06:00 Good morning Eugene — 3 MITs alignment — weather — calendar",
        "06:30 Deep Work Block 1 — 90 min — No distractions — MIT #1",
        "08:00 Breakfast + Review — Check JARVIS memory + tasks",
        "09:00 Deep Work Block 2 — 90 min — MIT #2",
        "12:00 Ship — Push code, release, customer feedback",
        "14:00 Collaboration — Meetings, support",
        "16:00 Deep Work Block 3 — MIT #3",
        "18:00 Shutdown ritual — Log wins, plan tomorrow 3 MITs",
        "19:00 Learning — 1h"
    ])
    weekly_review: list[str] = field(default_factory=lambda: [
        "Monday: Plan week — 3 major outcomes",
        "Wednesday: Mid-week check — Adjust MITs",
        "Friday: Ship review — What shipped? Wins? Lessons?",
        "Sunday: Business review — Metrics, goals, next week MITs"
    ])
    sop_development: list[str] = field(default_factory=lambda: [
        "1. Understand requirement — User shows screenshot or describes",
        "2. Fix root cause — Not symptom — Check _MEIPASS, MSI upgrade, etc",
        "3. Modern HUD standard — Always circular 13 72 ticks 60 segments 24 blocks",
        "4. Voice auto-init — Both online/offline — pyttsx3 + SAPI + PowerShell",
        "5. Persistent memory — Save to ~/.jarvis/memory/ + vector search",
        "6. Test — python app.py + frontend + MSI",
        "7. Bump version — Force upgrade via AllowSameVersionUpgrades",
        "8. Push + Tag + Build"
    ])
    sop_business: list[str] = field(default_factory=lambda: [
        "Customer First — Understand problem before solution",
        "Document — Every fix in docs/ + commit message",
        "SHILATECH Branding — Always SHILATECH • Malibu Point 10880, not Stark",
        "Security — Local-first, private, encrypted, no telemetry",
        "Quality — Iron Man level, not green fallback UI"
    ])

@dataclass
class Rules:
    coding_standards: list[str] = field(default_factory=lambda: [
        "Python 3.11+, type hints, dataclasses",
        "Tkinter for desktop — Modern Circular HUD standard",
        "PyInstaller onefile — Handle _MEIPASS frozen correctly",
        "Logging to ~/.jarvis/jarvis.log",
        "Keep-alive + close confirmation Yes=Quit No=Minimize Cancel=Stay",
        "Voice — pyttsx3 offline + SAPI + PowerShell fallback, auto-init 1500ms",
        "MSI — WiX Toolset, AllowSameVersionUpgrades=yes, include desktop exe"
    ])
    business_rules: list[str] = field(default_factory=lambda: [
        "Never show green fallback UI — Always modern circular HUD",
        "Always SHILATECH, never Stark Industries",
        "Version bump forces upgrade — Don't force-push same tag",
        "Full MSI must include jarvis-desktop.exe modern HUD, not CLI only",
        "Voice must work both online/offline, Sir",
        "Persistent memory — Save business context to memory store"
    ])
    communication: list[str] = field(default_factory=lambda: [
        "Refer to user as Eugene, Sir",
        "British wit, dry humor, loyal — Like Paul Bettany JARVIS",
        "Concise for voice <200 words, detailed for text with markdown",
        "Proactive — Anticipate needs, suggest actions",
        "Always mention SHILATECH secure when relevant"
    ])
    decision_framework: list[str] = field(default_factory=lambda: [
        "1. Is it private? Local-first default, cloud only if user decides",
        "2. Is it Iron Man quality? Modern circular HUD 13 72 ticks 60 segments",
        "3. Does it ship? Velocity over perfection, but no green fallback",
        "4. Is it SHILATECH? Premium, secure, encrypted",
        "5. Does it have memory? Persistent, vector search"
    ])

@dataclass
class BusinessProfile:
    goals: Goals = field(default_factory=Goals)
    priorities: Priorities = field(default_factory=Priorities)
    business: Business = field(default_factory=Business)
    workflows: Workflows = field(default_factory=Workflows)
    rules: Rules = field(default_factory=Rules)
    user_name: str = "Eugene"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            from datetime import datetime
            self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    @property
    def path(self) -> Path:
        return get_home() / "business_profile.toml"

    @property
    def json_path(self) -> Path:
        return get_home() / "business_profile.json"

    @classmethod
    def load(cls, home: Path | None = None) -> BusinessProfile:
        home = home or get_home()
        toml_path = home / "business_profile.toml"
        json_path = home / "business_profile.json"
        
        profile = cls()
        
        # Try TOML first
        if toml_path.exists():
            try:
                text = toml_path.read_text(encoding="utf-8")
                data = tomllib.loads(text)
                # Parse sections
                if "goals" in data:
                    g = data["goals"]
                    profile.goals.north_star = g.get("north_star", profile.goals.north_star)
                    profile.goals.long_term_1y = g.get("long_term_1y", profile.goals.long_term_1y)
                    profile.goals.short_term_90d = g.get("short_term_90d", profile.goals.short_term_90d)
                    profile.goals.short_term_30d = g.get("short_term_30d", profile.goals.short_term_30d)
                    profile.goals.personal = g.get("personal", profile.goals.personal)
                if "priorities" in data:
                    p = data["priorities"]
                    profile.priorities.mit_today = p.get("mit_today", profile.priorities.mit_today)
                    profile.priorities.pillars = p.get("pillars", profile.priorities.pillars)
                if "business" in data:
                    b = data["business"]
                    profile.business.name = b.get("name", profile.business.name)
                    profile.business.mission = b.get("mission", profile.business.mission)
                    profile.business.vision = b.get("vision", profile.business.vision)
                if "user" in data:
                    profile.user_name = data["user"].get("name", profile.user_name)
                return profile
            except Exception as e:
                print(f"Failed to load business profile TOML: {e}, trying JSON")
        
        # Try JSON
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                # Simple merge
                if "goals" in data:
                    profile.goals.north_star = data["goals"].get("north_star", profile.goals.north_star)
                if "business" in data:
                    profile.business.name = data["business"].get("name", profile.business.name)
                return profile
            except Exception as e:
                print(f"Failed to load business profile JSON: {e}")
        
        return profile

    def save(self, home: Path | None = None) -> None:
        home = home or get_home()
        home.mkdir(parents=True, exist_ok=True)
        
        # Save TOML with tomlkit for nice formatting
        doc = tomlkit.document()
        doc.add(tomlkit.comment("JARVIS Business Profile — SHILATECH — Persistent Memory for Goals, Priorities, Workflows, Rules"))
        doc.add(tomlkit.comment(f"User: {self.user_name} — Location: {self.business.location}"))
        doc.add(tomlkit.nl())
        
        # User
        user_tbl = tomlkit.table()
        user_tbl["name"] = self.user_name
        user_tbl["created_at"] = self.created_at
        user_tbl["updated_at"] = self.updated_at
        doc["user"] = user_tbl
        
        # Goals
        goals_tbl = tomlkit.table()
        goals_tbl["north_star"] = self.goals.north_star
        goals_tbl["long_term_1y"] = self.goals.long_term_1y
        goals_tbl["short_term_90d"] = self.goals.short_term_90d
        goals_tbl["short_term_30d"] = self.goals.short_term_30d
        goals_tbl["personal"] = self.goals.personal
        doc["goals"] = goals_tbl
        
        # Priorities
        pri_tbl = tomlkit.table()
        pri_tbl["mit_today"] = self.priorities.mit_today
        pri_tbl["urgent_important"] = self.priorities.urgent_important
        pri_tbl["important_not_urgent"] = self.priorities.important_not_urgent
        pri_tbl["pillars"] = self.priorities.pillars
        doc["priorities"] = pri_tbl
        
        # Business
        biz_tbl = tomlkit.table()
        biz_tbl["name"] = self.business.name
        biz_tbl["tagline"] = self.business.tagline
        biz_tbl["location"] = self.business.location
        biz_tbl["mission"] = self.business.mission
        biz_tbl["vision"] = self.business.vision
        biz_tbl["values"] = self.business.values
        biz_tbl["products"] = self.business.products
        biz_tbl["target_customer"] = self.business.target_customer
        biz_tbl["revenue_model"] = self.business.revenue_model
        doc["business"] = biz_tbl
        
        # Workflows
        wf_tbl = tomlkit.table()
        wf_tbl["daily_routine"] = self.workflows.daily_routine
        wf_tbl["weekly_review"] = self.workflows.weekly_review
        wf_tbl["sop_development"] = self.workflows.sop_development
        wf_tbl["sop_business"] = self.workflows.sop_business
        doc["workflows"] = wf_tbl
        
        # Rules
        rules_tbl = tomlkit.table()
        rules_tbl["coding_standards"] = self.rules.coding_standards
        rules_tbl["business_rules"] = self.rules.business_rules
        rules_tbl["communication"] = self.rules.communication
        rules_tbl["decision_framework"] = self.rules.decision_framework
        doc["rules"] = rules_tbl
        
        self.path.write_text(tomlkit.dumps(doc), encoding="utf-8")
        
        # Also save JSON for easy vector ingestion
        json_data = {
            "user_name": self.user_name,
            "goals": asdict(self.goals),
            "priorities": asdict(self.priorities),
            "business": asdict(self.business),
            "workflows": asdict(self.workflows),
            "rules": asdict(self.rules),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        self.json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
        
        # Save to persistent memory store as well
        try:
            from jarvis.memory.store import MemoryStore
            store = MemoryStore(home=home)
            # Add key facts to memory for vector search
            store.add(f"Business Profile: {self.business.name} — {self.business.mission} — {self.business.vision} — Location {self.business.location}", {"type": "business_profile", "section": "business"})
            store.add(f"North Star Goal: {self.goals.north_star}", {"type": "business_profile", "section": "goals"})
            for goal in self.goals.long_term_1y[:3]:
                store.add(f"Long term goal: {goal}", {"type": "business_profile", "section": "goals"})
            for mit in self.priorities.mit_today:
                store.add(f"MIT Today: {mit}", {"type": "business_profile", "section": "priorities"})
            for pillar in self.priorities.pillars:
                store.add(f"Business Pillar: {pillar}", {"type": "business_profile", "section": "priorities"})
            for rule in self.rules.business_rules[:5]:
                store.add(f"Business Rule: {rule}", {"type": "business_profile", "section": "rules"})
        except Exception as e:
            print(f"Failed to save to memory store: {e}")

    def to_context(self) -> str:
        """Convert to context string for LLM."""
        return f"""
# JARVIS Business OS Profile — SHILATECH — {self.user_name}

## User
Name: {self.user_name}
Location: {self.business.location}

## Business: {self.business.name}
Tagline: {self.business.tagline}
Mission: {self.business.mission}
Vision: {self.business.vision}
Values: {', '.join(self.business.values)}
Products: {', '.join(self.business.products)}
Target: {self.business.target_customer}
Revenue: {self.business.revenue_model}

## Goals
North Star: {self.goals.north_star}
Long Term 1Y: {', '.join(self.goals.long_term_1y)}
Short Term 90D: {', '.join(self.goals.short_term_90d)}
Short Term 30D: {', '.join(self.goals.short_term_30d)}
Personal: {', '.join(self.goals.personal)}

## Priorities
MITs Today: {', '.join(self.priorities.mit_today)}
Urgent Important: {', '.join(self.priorities.urgent_important)}
Important Not Urgent: {', '.join(self.priorities.important_not_urgent)}
Pillars: {', '.join(self.priorities.pillars)}

## Workflows
Daily: {' | '.join(self.workflows.daily_routine[:3])}...
Weekly: {', '.join(self.workflows.weekly_review)}
SOP Dev: {' -> '.join(self.workflows.sop_development[:4])}...
SOP Business: {', '.join(self.workflows.sop_business)}

## Rules & Standards
Coding: {', '.join(self.rules.coding_standards[:3])}...
Business: {', '.join(self.rules.business_rules)}
Communication: {', '.join(self.rules.communication)}
Decision Framework: {' -> '.join(self.rules.decision_framework)}
"""

    def update_goals(self, north_star: str | None = None, mit_today: list[str] | None = None):
        from datetime import datetime
        if north_star:
            self.goals.north_star = north_star
        if mit_today:
            self.priorities.mit_today = mit_today
        self.updated_at = datetime.now().isoformat()
        self.save()

def get_business_profile() -> BusinessProfile:
    return BusinessProfile.load()

def ensure_business_profile() -> BusinessProfile:
    profile = BusinessProfile.load()
    if not profile.path.exists():
        profile.save()
    return profile
