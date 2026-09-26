#!/usr/bin/env python3
"""
Build all JARVIS artifacts — EXE, ZIP, and MSI metadata.
Runs on Linux/macOS/Windows. MSI requires Windows + WiX, but we generate spec.

Usage:
  python deploy/build_all.py --version 0.1.0
"""

import argparse
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent.parent
DIST = ROOT / "dist"

def run(cmd, cwd=ROOT):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed with {result.returncode}")
        sys.exit(result.returncode)

def main():
    parser = argparse.ArgumentParser(description="Build JARVIS artifacts")
    parser.add_argument("--version", default="0.1.0", help="Version")
    parser.add_argument("--onefile", action="store_true", help="Build single file EXE")
    args = parser.parse_args()

    version = args.version
    print(f"=== Building JARVIS v{version} ===")

    # Clean
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("Installing PyInstaller...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller==6.10.0", "--break-system-packages"])

    # Build EXE
    print("\n[1/3] Building EXE with PyInstaller...")
    pyi_args = [
        sys.executable, "-m", "PyInstaller",
        "--name", "jarvis",
        "--console",
        "--collect-all", "jarvis",
        "--add-data", f"{ROOT / 'configs'}:configs" if sys.platform != "win32" else f"{ROOT / 'configs'};configs",
        "--hidden-import", "jarvis.engine.vllm_engine",
        "--hidden-import", "jarvis.engine.mlx_engine",
        "--hidden-import", "jarvis.engine.litellm_engine",
        "--hidden-import", "jarvis.engine.gemma_engine",
        "--hidden-import", "jarvis.memory.vector_store",
        "--hidden-import", "jarvis.tools.search_tools",
        str(ROOT / "src" / "jarvis" / "cli" / "main.py"),
    ]
    if args.onefile:
        pyi_args.insert(3, "--onefile")
    else:
        pyi_args.insert(3, "--onedir")

    # Icon if exists
    icon = ROOT / "assets" / "icon.ico"
    if icon.exists():
        pyi_args.extend(["--icon", str(icon)])

    run(pyi_args)

    # Create ZIP
    print(f"\n[2/3] Creating portable ZIP...")
    import zipfile
    jarvis_dist = DIST / "jarvis"
    zip_path = DIST / f"JARVIS-{version}-portable.zip"
    if jarvis_dist.exists():
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in jarvis_dist.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(DIST))
        print(f"ZIP created: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print(f"WARNING: {jarvis_dist} not found, skipping ZIP")

    # MSI metadata (Windows only can build real MSI)
    print(f"\n[3/3] MSI info...")
    msi_path = DIST / f"JARVIS-{version}-x64.msi"
    if sys.platform == "win32":
        print("On Windows, run deploy/windows/build_msi.ps1 to build real MSI")
        print(f"Would create: {msi_path}")
    else:
        print(f"MSI can only be built on Windows with WiX Toolset.")
        print(f"On Linux/macOS, EXE and ZIP are built. For MSI:")
        print(f"  - Push tag v{version} to trigger GitHub Actions Windows build")
        print(f"  - Or build on Windows: .\\deploy\\windows\\build_msi.ps1 -Version {version}")
        # Create a placeholder README for MSI
        (DIST / f"JARVIS-{version}-MSI-README.txt").write_text(
            f"JARVIS v{version} MSI Builder\n"
            f"========================\n\n"
            f"Real MSI must be built on Windows with WiX Toolset v3.11\n"
            f"See deploy/windows/README.md and docs/install/WINDOWS_MSI_GUIDE.md\n\n"
            f"Quick build on Windows:\n"
            f"  .\\deploy\\windows\\build_msi.ps1 -Version {version}\n\n"
            f"Or via GitHub Actions:\n"
            f"  git tag v{version} && git push origin v{version}\n\n"
            f"This portable ZIP works without MSI:\n"
            f"  {zip_path.name}\n"
        )

    print("\n=== Build complete ===")
    for f in DIST.iterdir():
        if f.is_file():
            size = f.stat().st_size / 1024 / 1024
            print(f"  {f.name} — {size:.1f} MB")
    if (DIST / "jarvis").exists():
        print(f"  jarvis/ folder — EXE + deps")

if __name__ == "__main__":
    main()
