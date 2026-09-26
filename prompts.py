"""Prompt library loader — with built-ins and external support."""

from pathlib import Path
import re

STARTER = """Build a concise pre-meeting brief from the details below. Include: attendees and their roles (mark unknown roles), probable purpose and desired outcome, up to five things to bring, three useful questions, and one risk of arriving unprepared. Distinguish facts from guesses. If the event details are insufficient, say what is missing. Keep the brief under 250 words."""

BUILTIN_PROMPTS = {
    "Meeting brief (starter)": STARTER,
    "Code explainer": "Explain the provided code: what it does, how it works, edge cases, and suggest improvements. Use bullet points and give a runnable example.",
    "Deep research": "You are a deep research agent. Break queries into sub-questions, search web and local docs, synthesize with citations. Never invent sources. Mark uncertainty. Provide final report with sections: Summary, Findings, Citations, Open Questions.",
    "Morning digest": "Generate a morning digest: top emails (with actions), today's calendar (with prep), health snapshot, news highlights. Keep under 300 words. Prioritize actionable items. Distinguish facts from inferences.",
    "Email drafter": "Draft a concise, professional email from the context. Include subject, greeting, body with clear ask, and closing. Tone: friendly but professional. Keep under 150 words.",
    "Code assistant": "You are JARVIS code assistant. Help with coding: read files, execute code safely, explain, refactor. Ask before destructive actions. Provide runnable examples. Use markdown code blocks.",
    "Research synthesizer": "Synthesize research findings: group by theme, cite sources, note conflicts, mark uncertainty, propose next steps. Keep factual and concise.",
    "Chat simple": "You are JARVIS, a helpful personal AI that runs locally by default. Be concise, accurate, and private. Use only supplied context for personal facts. Mark inferences clearly.",
    "Scheduled monitor": "You are a monitoring agent. Track changes, remember state across runs, alert on important events. Be concise and actionable. Summarize what changed since last run.",
}


def extract_prompt(markdown: str) -> str:
    """Return the first fenced block under a 'The prompt' heading, if present."""
    section = re.search(r"(?im)^##\s+The prompt\s*$", markdown)
    if not section:
        return ""
    remainder = markdown[section.end():]
    next_heading = re.search(r"(?m)^##\s+", remainder)
    if next_heading:
        remainder = remainder[:next_heading.start()]
    block = re.search(r"(?s)```[^\n]*\n(.*?)\n```", remainder)
    return block.group(1).strip() if block else ""


def load_prompts(folder: Path) -> dict[str, str]:
    prompts = {}
    if not folder.is_dir():
        return prompts
    for path in sorted(folder.rglob("*.md")):
        try:
            if len(path.relative_to(folder).parts) > 4 or path.stat().st_size > 100_000:
                continue
            content = extract_prompt(path.read_text(encoding="utf-8-sig", errors="replace"))
            if content:
                prompts[str(path.relative_to(folder).with_suffix(""))] = content
        except Exception:
            continue
    return prompts


def list_builtin() -> dict[str, str]:
    return dict(BUILTIN_PROMPTS)
