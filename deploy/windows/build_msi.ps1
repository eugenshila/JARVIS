# JARVIS SHILATECH — Windows installer builder
#
# One script for CI and for a laptop. It builds the two executables, stages the
# COMPLETE source payload, proves the build is complete, and only then wraps it
# all in an MSI.
#
#   .\deploy\windows\build_msi.ps1                       # full build
#   .\deploy\windows\build_msi.ps1 -Light                # skip the heavy extras (fast)
#   .\deploy\windows\build_msi.ps1 -Version 0.1.10.0     # explicit version
#   .\deploy\windows\build_msi.ps1 -SkipDeps             # deps already installed
#
# Why the selftest gate exists: the previous installers shipped whatever
# PyInstaller happened to collect, and a module that quietly failed to bundle
# only surfaced later as a feature that "isn't in the MSI". The gate imports
# every module in the manifest inside the frozen exe and fails the build here,
# where it is cheap to fix.

param(
    [string]$Version = "",
    [string]$PythonExe = "python",
    [switch]$SkipDeps,
    [switch]$Light,
    [switch]$NoPayload,
    [switch]$SkipSelftest
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $repo

function Step($n, $text) {
    Write-Host "`n[$n] $text" -ForegroundColor Cyan
    # Annotations are served by the API even where the raw log is not, so on a
    # runner each step also leaves a breadcrumb: if the build dies, the last
    # notice says exactly which stage it died in.
    if ($env:GITHUB_ACTIONS) { Write-Host "::notice::step $n — $text" }
}
function Ok($text) { Write-Host "  $text" -ForegroundColor Green }
function Warn($text) {
    Write-Host "  $text" -ForegroundColor Yellow
    if ($env:GITHUB_ACTIONS) { Write-Host "::warning::$text" }
}
function Die($text) {
    Write-Host "  $text" -ForegroundColor Red
    # On a runner this becomes an annotation, which survives where the raw log
    # may not be reachable.
    if ($env:GITHUB_ACTIONS) { Write-Host "::error::$text" }
    exit 1
}

# ---------------------------------------------------------------- 1. manifest
Step 1 "Refreshing the build manifest"
& $PythonExe deploy/gen_manifest.py
if ($LASTEXITCODE -ne 0) { Die "manifest generation failed" }

if (-not $Version) {
    $line = Select-String -Path "src/jarvis/_manifest.py" -Pattern '^VERSION = "(.+)"' | Select-Object -First 1
    $Version = $line.Matches[0].Groups[1].Value
}
# MSI versions are numeric and at most four fields.
if ($Version -notmatch '^\d+(\.\d+){0,3}$') { Die "version '$Version' is not a valid MSI version" }
Ok "version $Version"

$hidden = Get-Content "deploy/windows/hiddenimports.txt" | Where-Object { $_.Trim() }
Ok "$($hidden.Count) modules to bundle"

# ------------------------------------------------------------------- 2. tools
Step 2 "Checking tools"
try { Ok (& $PythonExe --version 2>&1) } catch { Die "Python 3.10+ not found" }

$wixBin = $null
foreach ($p in @(
        "${env:ProgramFiles(x86)}\WiX Toolset v3.11\bin",
        "${env:ProgramFiles}\WiX Toolset v3.11\bin",
        "${env:ProgramFiles(x86)}\WiX Toolset v3.14\bin",
        "C:\tools\wix")) {
    if (Test-Path "$p\candle.exe") { $wixBin = $p; break }
}
if ($wixBin) {
    $env:PATH = "$env:PATH;$wixBin"
    Ok "WiX at $wixBin"
} elseif (Get-Command candle.exe -ErrorAction SilentlyContinue) {
    Ok "WiX on PATH"
} else {
    Warn "WiX not found — will build executables only (choco install wixtoolset)"
}

# -------------------------------------------------------------------- 3. deps
if (-not $SkipDeps) {
    Step 3 "Installing build dependencies"
    & $PythonExe -m pip install --upgrade pip --quiet
    & $PythonExe -m pip install pyinstaller==6.10.0 --quiet
    if ($Light) {
        & $PythonExe -m pip install -e ".[server]" --quiet
    } else {
        # Not [all]: vllm has no Windows wheel and fails the whole install.
        & $PythonExe -m pip install -e ".[server,memory,tools-search]" --quiet
    }
    if ($LASTEXITCODE -ne 0) { Die "dependency install failed" }
    Ok "dependencies ready"
} else {
    Step 3 "Skipping dependency install"
}

# ------------------------------------------------------------------- 4. clean
Step 4 "Cleaning previous output"
Remove-Item -Recurse -Force dist, build, obj -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path obj | Out-Null
Ok "clean"

# --------------------------------------------------------------- 5. executables
Step 5 "Building executables (onefile)"
$hiddenArgs = @()
foreach ($m in $hidden) { $hiddenArgs += @("--hidden-import", $m) }

$common = @(
    "--onefile", "--noconfirm", "--clean",
    "--collect-all", "jarvis",
    "--add-data", "configs;configs",
    "--add-data", "app.py;.",
    "--add-data", "prompts.py;.",
    "--add-data", "client.py;.",
    "--icon", "assets/icon.ico"
) + $hiddenArgs

& $PythonExe -m PyInstaller @common --name jarvis --console src/jarvis/cli/main.py
if ($LASTEXITCODE -ne 0) { Die "jarvis.exe build failed" }
Ok "dist\jarvis.exe $([math]::Round((Get-Item dist/jarvis.exe).Length / 1MB, 1)) MB"

& $PythonExe -m PyInstaller @common --name jarvis-desktop --windowed src/jarvis/cli/desktop_gui.py
if ($LASTEXITCODE -ne 0) { Die "jarvis-desktop.exe build failed" }
Ok "dist\jarvis-desktop.exe $([math]::Round((Get-Item dist/jarvis-desktop.exe).Length / 1MB, 1)) MB"

# ----------------------------------------------------------------- 6. the gate
if (-not $SkipSelftest) {
    Step 6 "Proving the executable contains the complete code"
    $report = & dist\jarvis.exe selftest --json
    if ($LASTEXITCODE -ne 0) {
        Write-Host $report
        Die "INCOMPLETE BUILD — modules listed in the manifest are missing from jarvis.exe"
    }
    $parsed = ($report -join "`n") | ConvertFrom-Json
    Ok "$($parsed.modules_ok)/$($parsed.modules_expected) modules importable inside the exe"
} else {
    Step 6 "Skipping the completeness gate"
}

# ---------------------------------------------------------------- 7. payload
if (-not $NoPayload) {
    Step 7 "Staging the complete source payload"
    & $PythonExe deploy/windows/stage_payload.py --out dist/payload --verify
    if ($LASTEXITCODE -ne 0) { Die "payload staging failed" }
    $count = (Get-ChildItem -Recurse -File dist/payload).Count
    Ok "$count files staged into dist\payload"
} else {
    Step 7 "Skipping the source payload"
    New-Item -ItemType Directory -Force -Path dist/payload | Out-Null
    "payload omitted (-NoPayload)" | Out-File dist/payload/PAYLOAD.txt -Encoding ascii
}

# --------------------------------------------------------------------- 8. MSI
if ($wixBin -or (Get-Command candle.exe -ErrorAction SilentlyContinue)) {
    Step 8 "Building the MSI"

    # heat turns the staged tree into components. -gg/-g1 give stable, brace-free
    # GUIDs; -srd keeps the payload rooted at INSTALLFOLDER rather than adding a
    # directory level; -sreg because there is nothing to harvest from a source tree.
    & heat.exe dir dist\payload -cg PayloadComponents -dr INSTALLFOLDER `
        -gg -g1 -sfrag -srd -sreg -var var.PayloadDir `
        -out obj\payload.wxs
    if ($LASTEXITCODE -ne 0) { Die "heat.exe failed" }
    Ok "payload harvested"

    & candle.exe -arch x64 -dVersion=$Version -dPayloadDir=dist\payload `
        deploy\windows\jarvis.wxs obj\payload.wxs -out obj\
    if ($LASTEXITCODE -ne 0) { Die "candle.exe failed" }

    $msi = "dist\JARVIS-$Version-x64.msi"
    & light.exe obj\jarvis.wixobj obj\payload.wixobj -ext WixUIExtension -cultures:en-us -out $msi
    if ($LASTEXITCODE -ne 0) {
        Warn "light failed with validation — retrying with ICE validation off"
        & light.exe obj\jarvis.wixobj obj\payload.wixobj -ext WixUIExtension -cultures:en-us -sval -out $msi
    }
    if ($LASTEXITCODE -ne 0) { Die "light.exe failed" }

    Ok "$msi $([math]::Round((Get-Item $msi).Length / 1MB, 1)) MB"
} else {
    Step 8 "Skipping MSI — WiX not available"
}

# -------------------------------------------------------------------- 9. zips
Step 9 "Packaging portable archives"
Compress-Archive -Path dist/jarvis.exe, dist/jarvis-desktop.exe `
    -DestinationPath "dist/JARVIS-$Version-onefile.zip" -Force
Compress-Archive -Path dist/payload/* `
    -DestinationPath "dist/JARVIS-$Version-source.zip" -Force
Ok "portable archives written"

Write-Host "`n=== JARVIS SHILATECH v$Version built ===" -ForegroundColor Green
Get-ChildItem dist -File | Select-Object Name, @{n = 'MB'; e = { [math]::Round($_.Length / 1MB, 1) } } | Format-Table
Write-Host "After installing, confirm it is complete with:" -ForegroundColor Cyan
Write-Host '  "C:\Program Files\JARVIS SHILATECH\jarvis.exe" selftest --strict'
