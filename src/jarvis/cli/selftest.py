"""``jarvis selftest`` — prove that a build (MSI / EXE / source checkout) is COMPLETE.

Every module listed in the auto-generated manifest is imported, the bundled root
scripts (app.py, prompts.py, client.py) are located, and the installed source
payload is checked. Exit code is non-zero when anything is missing, so CI can gate
a release on it and a user can run it from the Start Menu after installing.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _manifest():
    from jarvis import _manifest

    return _manifest


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_roots() -> list[Path]:
    """Directories that may hold bundled data / the installed payload."""
    roots: list[Path] = []
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))
        exe_dir = Path(sys.executable).resolve().parent
        roots += [exe_dir, exe_dir / "payload"]
    else:
        here = Path(__file__).resolve()
        repo = here.parent.parent.parent.parent
        roots += [repo, repo / "payload"]
    return [r for r in roots if r.exists()]


def check_modules() -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
    """Import every manifest module.

    Two very different failures hide behind one ImportError, and conflating them
    is what made the old builds hard to diagnose:

      * the module is genuinely NOT IN THE BUILD (or its jarvis imports are) —
        fatal, that is an incomplete package;
      * the module is present but an optional third-party dependency is not
        installed (tkinter, faiss, litellm) — a note, not a defect.
    """
    ok: list[str] = []
    missing_code: list[tuple[str, str]] = []
    missing_dep: list[tuple[str, str]] = []
    for name in _manifest().MODULES:
        try:
            importlib.import_module(name)
            ok.append(name)
        except ModuleNotFoundError as exc:
            absent = (exc.name or "")
            detail = f"needs {absent}" if absent else str(exc)
            if absent == name or absent.startswith("jarvis"):
                missing_code.append((name, f"ModuleNotFoundError: {exc}"))
            else:
                missing_dep.append((name, detail))
        except Exception as exc:  # noqa: BLE001 - any other failure is real
            missing_code.append((name, f"{type(exc).__name__}: {exc}"))
    return ok, missing_code, missing_dep


def check_optional() -> list[tuple[str, bool]]:
    out = []
    for name in _manifest().OPTIONAL_THIRD_PARTY:
        try:
            importlib.import_module(name)
            out.append((name, True))
        except Exception:  # noqa: BLE001
            out.append((name, False))
    return out


def check_root_scripts() -> list[tuple[str, Path | None]]:
    found: list[tuple[str, Path | None]] = []
    for name in _manifest().ROOT_SCRIPTS:
        hit = None
        for root in bundle_roots():
            candidate = root / name
            if candidate.is_file():
                hit = candidate
                break
        found.append((name, hit))
    return found


def check_payload() -> tuple[Path | None, int, int]:
    """Locate the installed source payload and count how many manifest files exist."""
    expected = _manifest().PAYLOAD_FILES
    best: tuple[Path | None, int] = (None, 0)
    for root in bundle_roots():
        present = sum(1 for rel in expected if (root / rel).is_file())
        if present > best[1]:
            best = (root, present)
    return best[0], best[1], len(expected)


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output for CI")
@click.option("--strict", is_flag=True, help="Also fail when the source payload is incomplete")
def selftest(as_json: bool, strict: bool):
    """Verify this build contains the complete JARVIS code (modules + scripts + payload)."""
    m = _manifest()
    ok, failed, needs_deps = check_modules()
    optional = check_optional()
    scripts = check_root_scripts()
    payload_root, payload_present, payload_total = check_payload()

    missing_scripts = [n for n, p in scripts if p is None]
    payload_complete = payload_present == payload_total
    incomplete = bool(failed) or bool(missing_scripts)
    if strict and not payload_complete:
        incomplete = True

    if as_json:
        click.echo(
            json.dumps(
                {
                    "version": m.VERSION,
                    "frozen": is_frozen(),
                    "executable": sys.executable,
                    "modules_expected": m.MODULE_COUNT,
                    "modules_ok": len(ok),
                    "modules_failed": [{"module": n, "error": e} for n, e in failed],
                    "modules_needing_deps": [{"module": n, "needs": e} for n, e in needs_deps],
                    "root_scripts": {n: (str(p) if p else None) for n, p in scripts},
                    "optional": dict(optional),
                    "payload_root": str(payload_root) if payload_root else None,
                    "payload_present": payload_present,
                    "payload_total": payload_total,
                    "complete": not incomplete,
                },
                indent=2,
            )
        )
        raise SystemExit(1 if incomplete else 0)

    console.print(
        Panel.fit(
            f"[bold cyan]JARVIS SHILATECH — Build Selftest[/]\n"
            f"Version: [bold]{m.VERSION}[/]\n"
            f"Mode: {'frozen executable (MSI/EXE)' if is_frozen() else 'source checkout'}\n"
            f"Executable: {sys.executable}",
            border_style="cyan",
        )
    )

    table = Table(title="Completeness", show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Result")
    table.add_column("Detail")
    table.add_row(
        "jarvis modules",
        "[green]OK[/]" if not failed else "[red]MISSING[/]",
        f"{len(ok) + len(needs_deps)}/{m.MODULE_COUNT} present"
        + (f" ({len(needs_deps)} awaiting optional deps)" if needs_deps else ""),
    )
    table.add_row(
        "root scripts",
        "[green]OK[/]" if not missing_scripts else "[red]MISSING[/]",
        ", ".join(n for n, _ in scripts) if not missing_scripts else ", ".join(missing_scripts),
    )
    table.add_row(
        "source payload",
        "[green]OK[/]" if payload_complete else ("[yellow]PARTIAL[/]" if payload_present else "[red]ABSENT[/]"),
        f"{payload_present}/{payload_total} files at {payload_root or 'n/a'}",
    )
    missing_optional = [n for n, present in optional if not present]
    table.add_row(
        "optional extras",
        "[green]ALL[/]" if not missing_optional else "[yellow]PARTIAL[/]",
        "missing: " + ", ".join(missing_optional) if missing_optional else "all present",
    )
    console.print(table)

    if needs_deps:
        note = Table(title="Present, but an optional dependency is not installed", header_style="bold yellow")
        note.add_column("Module")
        note.add_column("Needs")
        for name, dep in needs_deps[:20]:
            note.add_row(name, dep)
        console.print(note)

    if failed:
        bad = Table(title="Modules that failed to import", header_style="bold red")
        bad.add_column("Module")
        bad.add_column("Error")
        for name, err in failed[:40]:
            bad.add_row(name, err[:110])
        console.print(bad)

    if incomplete:
        console.print(
            Panel.fit(
                "[bold red]INCOMPLETE BUILD[/]\n"
                "This installation is missing code listed in the manifest.\n"
                "Rebuild with: [bold]python deploy/gen_manifest.py && "
                "pwsh deploy/windows/build_msi.ps1 -Version "
                f"{m.VERSION}[/]",
                border_style="red",
            )
        )
        raise SystemExit(1)

    console.print(
        Panel.fit(
            f"[bold green]COMPLETE[/] — all {m.MODULE_COUNT} modules"
            + (f" ({len(needs_deps)} waiting on optional extras)" if needs_deps else "")
            + ", "
            f"{len(m.ROOT_SCRIPTS)} root scripts"
            + (f" and {payload_total} payload files" if payload_complete else "")
            + " are present, Sir.",
            border_style="green",
        )
    )
