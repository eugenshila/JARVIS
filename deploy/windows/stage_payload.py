#!/usr/bin/env python3
"""Stage the COMPLETE source payload that ships inside the MSI.

The old installer shipped two frozen .exe files and nothing else — so an installed
machine had no source, no configs, no docs, no frontend and no way to run
``python app.py``. This script copies the whole working codebase into
``dist/payload/`` so WiX (heat.exe) can harvest it into the installer.

Usage:
    python deploy/windows/stage_payload.py [--out dist/payload] [--verify]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jarvis._manifest import PAYLOAD_FILES, VERSION  # noqa: E402

RUN_GUI_BAT = """@echo off
title JARVIS SHILATECH - Desktop HUD
cd /d "%~dp0"
echo Starting JARVIS Desktop (full Business OS HUD) ...
where python >nul 2>nul || (echo Python 3.10+ required - https://python.org && pause && exit /b 1)
python -m pip install -e .[server,memory,tools-search] --disable-pip-version-check >nul 2>nul
python app.py
if errorlevel 1 pause
"""

RUN_CLI_BAT = """@echo off
title JARVIS SHILATECH - CLI
cd /d "%~dp0"
where python >nul 2>nul || (echo Python 3.10+ required - https://python.org && pause && exit /b 1)
python -m pip install -e .[server,memory,tools-search] --disable-pip-version-check >nul 2>nul
python -m jarvis.cli.main %*
pause
"""

VERIFY_BAT = """@echo off
title JARVIS SHILATECH - Verify install is complete
cd /d "%~dp0"
echo Checking that this installation contains the complete code ...
if exist "%~dp0jarvis.exe" (
  "%~dp0jarvis.exe" selftest
) else (
  python -m jarvis.cli.main selftest
)
pause
"""


def stage(out: Path) -> tuple[int, list[str]]:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    copied = 0
    missing: list[str] = []
    for rel in PAYLOAD_FILES:
        src = ROOT / rel
        if not src.is_file():
            missing.append(rel)
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1

    (out / "RUN-JARVIS-DESKTOP.bat").write_text(RUN_GUI_BAT, encoding="ascii")
    (out / "RUN-JARVIS-CLI.bat").write_text(RUN_CLI_BAT, encoding="ascii")
    (out / "VERIFY-COMPLETE.bat").write_text(VERIFY_BAT, encoding="ascii")
    (out / "PAYLOAD.txt").write_text(
        f"JARVIS SHILATECH v{VERSION} — complete source payload\n"
        f"{copied} files\n\n"
        "This folder is the full codebase, installed alongside the executables.\n"
        "Run RUN-JARVIS-DESKTOP.bat for the full Business OS HUD (app.py),\n"
        "or VERIFY-COMPLETE.bat to confirm nothing is missing.\n",
        encoding="utf-8",
    )
    return copied, missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="dist/payload", help="output directory")
    ap.add_argument("--verify", action="store_true", help="fail if any manifest file is missing")
    args = ap.parse_args()

    out = (ROOT / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    copied, missing = stage(out)

    print(f"Staged {copied} files into {out}")
    if missing:
        print(f"WARNING: {len(missing)} manifest files missing from the repo:", file=sys.stderr)
        for m in missing[:20]:
            print(f"  - {m}", file=sys.stderr)
        if args.verify:
            return 1
    if args.verify and copied < 50:
        print(f"ERROR: payload only has {copied} files — build is incomplete", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
