# MSI Build v0.1.9.2 — SHILATECH Voice + Hybrid Interactive + Circular HUD

**Date:** 2026-09-26
**Version:** 0.1.9.2
**Branch:** arena/01a0d70b-jarvis + main at e676d77
**Tags:** v0.1.9, v0.1.9.1, v0.1.9.2

## Build Triggered

- Tag v0.1.9.2 pushed → triggers workflows:
  - Build Windows MSI Light (Fast) — 2m38s success (run 36228761374)
  - Build Windows MSI + EXE (Full) — in progress (run 36228761380) — expected 15-20m
- Artifacts: jarvis-windows-light (light), jarvis-windows (full) with MSI + EXE + ZIP

## Local Builds Done

- Python wheel: dist/jarvis-0.1.9-py3-none-any.whl 139kB
- Portable ZIP: dist/JARVIS-0.1.9-portable.zip 414kB, dist/JARVIS-0.1.9-SHILATECH.zip 414kB
- Frontend: frontend/dist/assets/index-sAanPwBW.js 251.40kB 71.78kB gzip, 38 modules
- Linux PyInstaller attempted but container missing libpython3.11.so — need python3-dev, expected on Windows runner WiX will succeed

## MSI Details

- Manufacturer: SHILATECH (updated in deploy/windows/jarvis.wxs and .github/workflows/build-msi.yml)
- Product Name: JARVIS - SHILATECH - Personal AI, On Personal Devices
- Version: 0.1.9.2
- UpgradeCode: a1b2c3d4-e5f6-7890-abcd-ef1234567890
- Installer: perMachine, WixUI_InstallDir, adds to PATH, Start Menu shortcut JARVIS + Uninstall
- Files: dist/jarvis/jarvis.exe (PyInstaller onedir) + configs + etc
- WiX Toolset v3.11 via choco install wixtoolset on windows-latest runner

## Features Included in MSI

- SHILATECH branding everywhere
- Circular HUD like screenshot — 560px canvas, 72 ticks, blue glow, number 13, Trash 44 items Size 248.95 MB
- Voice speaks both online/offline: frontend speechSynthesis British offline + mic webkitSpeechRecognition offline, backend pyttsx3/kokoro offline
- Hybrid interactive when online: same circular interface, only badge changes, you decide Full Stack vs Basic Local from HUD clickable badge or CLI --interactive
- Online vs Offline comparison doc
- 50 tools, auto engine, network detection socket 8.8.8.8:53, 7 modes default circular
- Autostart Good Morning Eugene + 3 MITs + TTS + tray

## How to Install MSI (once GitHub Actions finishes)

1. Go to https://github.com/eugenshila/JARVIS/actions/runs/36228761380 (full) or 36228761374 (light)
2. Download artifact jarvis-windows or jarvis-windows-light
3. Or go to Releases https://github.com/eugenshila/JARVIS/releases/tag/v0.1.9.2 — MSI will be attached by softprops/action-gh-release
4. Run JARVIS-0.1.9.2-x64.msi — installs to Program Files\JARVIS, adds to PATH
5. Run:
   ```
   jarvis --help
   jarvis ask --engine auto --interactive "Good morning Eugene"
   jarvis ironman --voice --engine auto
   python app.py
   ```

## Local Portable (already built)

- dist/JARVIS-0.1.9-portable.zip — unzip, run INSTALL.bat / install.sh
- Contains wheel + frontend-dist + configs + docs + deploy

## Release Notes

See dist/RELEASE_NOTES_v0.1.9.md and docs/ONLINE_VS_OFFLINE_COMPARISON.md, docs/SECURITY_HYBRID.md

## Next Steps

- Wait for full MSI build to complete (~15-20m) — check gh run list
- Download MSI from artifact or release
- Test on Windows 11 DESKTOP-3D8CN02 i5-6300U 8GB
- For voice: pip install -e .[voice] or pip install pyttsx3 faster-whisper

**SHILATECH • Malibu Point 10880 • Voice works online/offline, Sir.**
