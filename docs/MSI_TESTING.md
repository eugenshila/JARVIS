# Testing the MSI

## Get a build

Every push to an `arena/**` branch builds a test installer — no tag, no
release. Open the run, and download the `jarvis-windows-light-<version>`
artifact:

<https://github.com/eugenshila/JARVIS/actions/workflows/build-msi-light.yml>

It contains:

| File | What it is |
|---|---|
| `JARVIS-<version>-x64.msi` | the installer (~43 MB) |
| `JARVIS-<version>-onefile.zip` | both executables, no installer |
| `JARVIS-<version>-source.zip` | the complete source payload on its own |
| `jarvis.exe`, `jarvis-desktop.exe` | the raw executables |

A tag (`v0.1.10.1`) additionally publishes a GitHub Release with the same
files attached; the full workflow does the same with vector memory and web
search bundled.

## Install

Double-click the MSI, or from an elevated prompt:

```powershell
msiexec /i JARVIS-0.1.10.0-x64.msi /l*v install.log
```

It installs per-machine to `C:\Program Files\JARVIS SHILATECH\`, adds that
folder to `PATH`, and creates a Start Menu group.

## Confirm it contains the complete code

This is the check that used to be impossible:

```powershell
jarvis selftest --strict
```

or Start Menu → **JARVIS SHILATECH → Verify JARVIS is complete**. A good build
reports:

```
jarvis modules   OK   75/75 present
root scripts     OK   app.py, client.py, prompts.py
source payload   OK   205/205 files at C:\Program Files\JARVIS SHILATECH
COMPLETE — ... are present, Sir.
```

`--strict` also fails if the installed source payload is short, so a truncated
install cannot pass quietly. Exit code is non-zero when anything is missing.

## What is actually installed

```
C:\Program Files\JARVIS SHILATECH\
  jarvis.exe              CLI — chat, agents, business, serve, web, selftest
  jarvis-desktop.exe      Tkinter circular HUD
  app.py  client.py  prompts.py
  src\jarvis\...          the full Python package
  web\                    the holographic interface (React + Three.js + bridge)
  configs\  docs\  examples\  tests\  deploy\
  RUN-JARVIS-DESKTOP.bat  RUN-JARVIS-CLI.bat  VERIFY-COMPLETE.bat
```

207 files are packaged in the MSI: the two executables plus 205 payload files.

## Try each face

```powershell
jarvis doctor                     # environment check
jarvis ask "status report" --mock # no network, no keys
jarvis chat --interactive
jarvis business init              # Business OS
jarvis web                        # holographic UI (needs Node 20+)
```

The desktop HUD is the Start Menu's **JARVIS Desktop HUD**, or
`RUN-JARVIS-DESKTOP.bat` in the install folder, which runs `python app.py`
against the installed source.

## If something is wrong

1. `jarvis selftest --strict` — says precisely what is missing.
2. `%USERPROFILE%\.jarvis\jarvis.log` — the HUD logs there, including crashes.
3. `msiexec /i ... /l*v install.log` — verbose installer log.
4. In CI the same checks run before the artifact is uploaded, and every stage
   leaves an annotation on the run, so a failed build says which stage failed
   without opening the log.

## Uninstall

Start Menu → **Uninstall JARVIS SHILATECH**, or Settings → Apps, or:

```powershell
msiexec /x JARVIS-0.1.10.0-x64.msi
```

Reinstalling the same version replaces the files rather than installing
alongside them (`AllowSameVersionUpgrades`), so a rebuilt test MSI always wins.
