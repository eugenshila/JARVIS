"""Skill registry — loads from local folder and built-ins."""

from __future__ import annotations

import re
from pathlib import Path

from jarvis.core.config import get_home
from jarvis.skills.base import Skill


BUILTIN_SKILLS: list[Skill] = [
    Skill(
        name="meeting-brief",
        description="Build concise pre-meeting brief from details",
        prompt="Build a concise pre-meeting brief from the details below. Include: attendees and their roles (mark unknown roles), probable purpose and desired outcome, up to five things to bring, three useful questions, and one risk of arriving unprepared. Distinguish facts from guesses. If insufficient, say what's missing. Under 250 words.",
        tags=["productivity", "meeting"],
    ),
    Skill(
        name="code-explainer",
        description="Explain code clearly with examples",
        prompt="Explain the provided code: what it does, how it works, edge cases, and suggest improvements. Use bullet points and give a runnable example.",
        tags=["coding", "education"],
    ),
    Skill(
        name="research-synthesizer",
        description="Synthesize research with citations",
        prompt="Synthesize research findings: group by theme, cite sources, note conflicts, mark uncertainty, propose next steps. Keep factual and concise.",
        tags=["research"],
    ),
    Skill(
        name="email-drafter",
        description="Draft concise professional emails",
        prompt="Draft a concise, professional email from the context. Include subject, greeting, body with clear ask, and closing. Tone: friendly but professional.",
        tags=["writing", "email"],
    ),
    Skill(
        name="arxiv",
        description="Summarize arXiv papers",
        prompt="You are an arXiv assistant. Summarize the paper: problem, method, results, limitations. Extract key figures if mentioned.",
        tags=["research", "arxiv"],
    ),
]


def extract_prompt_from_md(md: str) -> str:
    # look for ## The prompt then fenced block
    m = re.search(r"(?im)^##\s+The prompt\s*$", md)
    if not m:
        return ""
    rest = md[m.end():]
    next_h = re.search(r"(?m)^##\s+", rest)
    if next_h:
        rest = rest[: next_h.start()]
    block = re.search(r"(?s)```[^\n]*\n(.*?)\n```", rest)
    return block.group(1).strip() if block else ""


class SkillRegistry:
    def __init__(self, home: Path | None = None):
        self.home = home or get_home()
        self.dir = self.home / "skills"
        self.dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[Skill]:
        skills = list(BUILTIN_SKILLS)
        # load from disk
        if self.dir.exists():
            for md_path in self.dir.rglob("*.md"):
                if md_path.stat().st_size > 200_000:
                    continue
                try:
                    text = md_path.read_text(encoding="utf-8", errors="replace")
                    prompt = extract_prompt_from_md(text)
                    if prompt:
                        skills.append(
                            Skill(
                                name=md_path.stem,
                                description=f"Imported from {md_path.name}",
                                prompt=prompt,
                                source=str(md_path),
                                path=md_path,
                            )
                        )
                except Exception:
                    continue
        return skills

    def get(self, name: str) -> Skill | None:
        for s in self.list():
            if s.name == name:
                return s
        return None

    def install_from_text(self, name: str, prompt: str, description: str = "") -> Skill:
        path = self.dir / f"{name}.md"
        path.write_text(f"## The prompt\n```\n{prompt}\n```\n", encoding="utf-8")
        return Skill(name=name, description=description or f"Local skill {name}", prompt=prompt, path=path)
