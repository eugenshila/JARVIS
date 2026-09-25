"""Load reusable Markdown prompts without executing untrusted content."""

from pathlib import Path
import re


STARTER = """Build a concise pre-meeting brief from the details below. Include: attendees and their roles (mark unknown roles), probable purpose and desired outcome, up to five things to bring, three useful questions, and one risk of arriving unprepared. Distinguish facts from guesses. If the event details are insufficient, say what is missing. Keep the brief under 250 words."""


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
    prompts = {"Meeting brief (starter)": STARTER}
    if not folder.is_dir():
        return prompts
    for path in sorted(folder.rglob("*.md")):
        if len(path.relative_to(folder).parts) > 4 or path.stat().st_size > 100_000:
            continue
        content = extract_prompt(path.read_text(encoding="utf-8-sig", errors="replace"))
        if content:
            prompts[str(path.relative_to(folder).with_suffix(""))] = content
    return prompts
