"""
tools/file_processor.py — one tool for "do something with this file".

DESIGN
    Detect the type from the extension, then dispatch to the verbs that type
    supports. The important constraint, and the difference from the assistant
    this idea came from: **local libraries do the work; the model is only
    asked for the verbs that genuinely need judgement** (``summarize``,
    ``describe``). Extracting text from a PDF, counting rows in a CSV or
    listing a zip are deterministic operations and must not cost a token or
    require a network round trip.

    Every optional dependency is imported inside the function that needs it,
    so the tool loads and reports usefully on a machine with none of them
    installed.

TYPES AND VERBS
    text/code   summarize, extract_text, stats
    pdf         summarize, extract_text, stats
    docx        summarize, extract_text, stats
    csv/tsv     summarize, extract_text, stats, analyze
    json        summarize, extract_text, stats, validate
    image       describe, stats
    archive     list, stats
    audio/video stats
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from jarvis.tools.base import BaseTool, ToolSpec

MAX_BYTES = 25 * 1024 * 1024  # refuse to slurp something enormous
MAX_EXTRACT_CHARS = 20000
SUMMARY_INPUT_CHARS = 12000

_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "text": ("txt", "md", "rst", "log", "ini", "cfg", "toml", "yaml", "yml"),
    "code": (
        "py", "js", "ts", "jsx", "tsx", "html", "css", "java", "c", "h", "cpp",
        "cs", "go", "rs", "rb", "php", "swift", "kt", "sh", "bash", "ps1",
        "lua", "r", "sql", "vue", "svelte",
    ),
    "pdf": ("pdf",),
    "docx": ("docx",),
    "csv": ("csv", "tsv"),
    "json": ("json", "jsonl", "geojson"),
    "image": ("jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "ico"),
    "archive": ("zip",),
    "audio": ("mp3", "wav", "ogg", "m4a", "aac", "flac", "opus", "wma"),
    "video": ("mp4", "avi", "mov", "mkv", "webm", "wmv", "m4v"),
}

_VERBS: dict[str, tuple[str, ...]] = {
    "text": ("summarize", "extract_text", "stats"),
    "code": ("summarize", "extract_text", "stats"),
    "pdf": ("summarize", "extract_text", "stats"),
    "docx": ("summarize", "extract_text", "stats"),
    "csv": ("summarize", "extract_text", "stats", "analyze"),
    "json": ("summarize", "extract_text", "stats", "validate"),
    "image": ("describe", "stats"),
    "archive": ("list", "stats"),
    "audio": ("stats",),
    "video": ("stats",),
    "unknown": ("stats",),
}


def detect_type(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    for kind, exts in _EXTENSIONS.items():
        if ext in exts:
            return kind
    return "unknown"


def _human_size(n: int) -> str:
    step = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if step < 1024 or unit == "GB":
            return f"{step:.0f} {unit}" if unit == "B" else f"{step:.1f} {unit}"
        step /= 1024
    return f"{n} B"


# ── extraction (all local, no model) ──────────────────────────────────────────


def _extract_plain(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "PDF support needs pypdf: pip install pypdf"
            ) from exc
    reader = PdfReader(str(path))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_docx(path: Path) -> str:
    try:
        import docx  # type: ignore
    except ImportError as exc:
        raise RuntimeError("DOCX support needs python-docx: pip install python-docx") from exc
    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def extract_text(path: Path, kind: str) -> str:
    if kind == "pdf":
        return _extract_pdf(path)
    if kind == "docx":
        return _extract_docx(path)
    if kind in ("text", "code", "csv", "json"):
        return _extract_plain(path)
    raise RuntimeError(f"Cannot extract text from a {kind} file.")


# ── verbs ─────────────────────────────────────────────────────────────────────


def _stats(path: Path, kind: str) -> str:
    stat = path.stat()
    lines = [
        f"{path.name} — {kind}, {_human_size(stat.st_size)}",
        f"  path: {path}",
        f"  modified: {__import__('datetime').datetime.fromtimestamp(stat.st_mtime):%Y-%m-%d %H:%M}",
    ]
    if kind in ("text", "code", "csv", "json"):
        try:
            text = _extract_plain(path)
            lines.append(f"  lines: {text.count(chr(10)) + 1}, words: {len(text.split())}, chars: {len(text)}")
        except Exception:
            pass
    elif kind == "image":
        try:
            from PIL import Image  # type: ignore

            with Image.open(path) as img:
                lines.append(f"  dimensions: {img.width}x{img.height}, mode: {img.mode}")
        except ImportError:
            lines.append("  (install pillow for image dimensions)")
        except Exception as exc:
            lines.append(f"  (could not read image: {exc})")
    elif kind == "archive":
        try:
            with zipfile.ZipFile(path) as zf:
                lines.append(f"  entries: {len(zf.namelist())}")
        except Exception as exc:
            lines.append(f"  (could not read archive: {exc})")
    return "\n".join(lines)


def _analyze_csv(path: Path) -> str:
    import csv as csv_mod

    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv_mod.reader(handle, delimiter=delimiter)
        rows = []
        for i, row in enumerate(reader):
            if i > 50000:
                break
            rows.append(row)
    if not rows:
        return f"{path.name} is empty."

    header, body = rows[0], rows[1:]
    lines = [f"{path.name}: {len(body)} data row(s), {len(header)} column(s)", "", "Columns:"]
    for index, name in enumerate(header):
        values = [r[index] for r in body if index < len(r) and r[index] != ""]
        numeric: list[float] = []
        for value in values:
            try:
                numeric.append(float(value))
            except ValueError:
                pass
        filled = len(values)
        if numeric and len(numeric) >= max(1, filled * 0.8):
            lines.append(
                f"  {name}: numeric, min={min(numeric):g}, max={max(numeric):g}, "
                f"mean={sum(numeric) / len(numeric):.4g}, filled={filled}/{len(body)}"
            )
        else:
            distinct = len({v for v in values})
            lines.append(f"  {name}: text, {distinct} distinct value(s), filled={filled}/{len(body)}")
    return "\n".join(lines)


def _validate_json(path: Path) -> str:
    text = _extract_plain(path)
    if path.suffix.lower() == ".jsonl":
        bad = []
        count = 0
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            count += 1
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                bad.append(f"line {number}: {exc.msg}")
        if bad:
            return f"Invalid JSONL — {len(bad)} bad line(s):\n  " + "\n  ".join(bad[:10])
        return f"Valid JSONL: {count} record(s)."
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
    if isinstance(data, dict):
        return f"Valid JSON object with {len(data)} key(s): {', '.join(list(data)[:15])}"
    if isinstance(data, list):
        return f"Valid JSON array with {len(data)} item(s)."
    return f"Valid JSON scalar of type {type(data).__name__}."


def _list_archive(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        infos = zf.infolist()
        total = sum(i.file_size for i in infos)
        lines = [f"{path.name}: {len(infos)} entries, {_human_size(total)} uncompressed"]
        for info in infos[:50]:
            lines.append(f"  {info.filename} ({_human_size(info.file_size)})")
        if len(infos) > 50:
            lines.append(f"  … and {len(infos) - 50} more")
    return "\n".join(lines)


def _summarize(path: Path, kind: str, question: str, engine: Any = None) -> str:
    text = extract_text(path, kind).strip()
    if not text:
        return f"{path.name} contains no extractable text."
    clipped = text[:SUMMARY_INPUT_CHARS]
    if engine is None:
        try:
            from jarvis.engine.ladder import SMART, for_purpose

            engine = for_purpose(SMART)
        except Exception as exc:
            return (
                f"No model available to summarise ({exc}). "
                f"Extracted text begins:\n\n{clipped[:1500]}"
            )
    from jarvis.core.types import Message, Role

    instruction = question.strip() or "Summarise this document concisely, keeping concrete facts, numbers and names."
    try:
        response = engine.generate(
            [
                Message(
                    role=Role.SYSTEM,
                    content="You summarise documents accurately. Never invent content that is not present.",
                ),
                Message(
                    role=Role.USER,
                    content=f"{instruction}\n\nFILE: {path.name}\n\n---\n{clipped}\n---",
                ),
            ]
        )
    except Exception as exc:
        return f"Could not summarise {path.name}: {exc}"
    truncated = "\n\n(Note: only the first part of the file was read.)" if len(text) > SUMMARY_INPUT_CHARS else ""
    return response.content + truncated


def _describe_image(path: Path, question: str) -> str:
    try:
        from jarvis.tools.vision_tool import VisionTool
    except ImportError:
        return f"No vision tool available. {_stats(path, 'image')}"
    try:
        return VisionTool().run(
            image_path=str(path), prompt=question or "Describe this image."
        )
    except TypeError:
        return VisionTool().run(path=str(path))
    except Exception as exc:
        return f"Could not describe {path.name}: {exc}"


# ── the tool ──────────────────────────────────────────────────────────────────


class FileProcessorTool(BaseTool):
    spec = ToolSpec(
        name="file_process",
        description=(
            "Work with a file on disk: summarise it, extract its text, report "
            "statistics, analyse a CSV's columns, validate JSON, list a zip, or "
            "describe an image. Handles pdf, docx, txt, md, source code, csv/tsv, "
            "json, images, archives, audio and video. Use this instead of file_read "
            "for anything that is not plain text, and whenever the user asks what a "
            "document says or contains."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "action": {
                    "type": "string",
                    "enum": [
                        "auto", "summarize", "extract_text", "stats",
                        "analyze", "validate", "list", "describe",
                    ],
                    "description": "What to do. 'auto' picks the best verb for the file type.",
                    "default": "auto",
                },
                "question": {
                    "type": "string",
                    "description": "Optional specific question for summarize/describe",
                },
            },
            "required": ["path"],
        },
    )

    def run(self, path: str, action: str = "auto", question: str = "", **kwargs) -> str:
        target = Path(str(path)).expanduser()
        if not target.exists():
            return f"Error: no such file: {path}"
        if target.is_dir():
            entries = sorted(p.name for p in target.iterdir())[:50]
            return f"{path} is a directory with {len(entries)} entries:\n  " + "\n  ".join(entries)
        try:
            size = target.stat().st_size
        except OSError as exc:
            return f"Error: cannot stat {path}: {exc}"
        if size > MAX_BYTES:
            return f"Error: {target.name} is {_human_size(size)}; the limit is {_human_size(MAX_BYTES)}."

        kind = detect_type(target)
        supported = _VERBS.get(kind, ("stats",))
        verb = str(action or "auto").strip().lower()
        if verb == "auto":
            verb = supported[0]
        if verb not in supported:
            return (
                f"'{verb}' is not available for a {kind} file. "
                f"Try: {', '.join(supported)}."
            )

        try:
            if verb == "stats":
                return _stats(target, kind)
            if verb == "extract_text":
                text = extract_text(target, kind)
                if len(text) > MAX_EXTRACT_CHARS:
                    return text[:MAX_EXTRACT_CHARS] + f"\n\n… truncated at {MAX_EXTRACT_CHARS} chars."
                return text or f"{target.name} contains no extractable text."
            if verb == "analyze":
                return _analyze_csv(target)
            if verb == "validate":
                return _validate_json(target)
            if verb == "list":
                return _list_archive(target)
            if verb == "describe":
                return _describe_image(target, question)
            if verb == "summarize":
                return _summarize(target, kind, question, kwargs.get("engine"))
        except RuntimeError as exc:  # missing optional dependency, mostly
            return f"Error: {exc}"
        except Exception as exc:
            return f"Error processing {target.name}: {exc}"
        return f"Error: unsupported action {verb}."


def supported_actions(path: str) -> list[str]:
    """What this file type can do — used by the HUD's upload panel."""
    return list(_VERBS.get(detect_type(Path(path)), ("stats",)))


__all__ = ["FileProcessorTool", "detect_type", "extract_text", "supported_actions"]
