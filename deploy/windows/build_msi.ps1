# Build the JARVIS Windows executable and MSI.
#
# Usage:
#   .\deploy\windows\build_msi.ps1 -Version 0.2.0
#   .\deploy\windows\build_msi.ps1 -Version 0.2.0 -SkipDeps
#
# The MSI deliberately packages PyInstaller one-file executables. That keeps the
# installer from omitting DLLs or one of the package's runtime modules while also
# installing the native desktop HUD host.
[CmdletBinding()]
param(
    [ValidatePattern('^\d+\.\d+\.\d+(\.\d+)?$')]
    [string]$Version = "0.2.0",
    [string]$PythonExe = "python",
    [switch]$SkipDeps,
    # Kept as an explicit, backwards-compatible switch because older build
    # instructions documented -OneFile. MSI builds are always one-file.
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Dist = Join-Path $Root "dist"
$FrontendDist = Join-Path $Root "frontend\dist"
$WixObject = Join-Path $Root "deploy\windows\jarvis.wixobj"
$MsiPath = Join-Path $Dist "JARVIS-$Version-x64.msi"

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$File,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$File failed with exit code $LASTEXITCODE."
    }
}

Push-Location $Root
try {
    Write-Host "=== Building JARVIS SHILATECH $Version ===" -ForegroundColor Green

    if (-not (Get-Command $PythonExe -ErrorAction SilentlyContinue)) {
        throw "Python 3.10+ was not found: $PythonExe"
    }

    # WiX is installed by the workflow on CI, but this also supports the
    # standard local WiX v3.11/v3.14 installation locations.
    $wixCandidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "WiX Toolset v3.14\bin"),
        (Join-Path ${env:ProgramFiles(x86)} "WiX Toolset v3.11\bin"),
        (Join-Path ${env:ProgramFiles} "WiX Toolset v3.14\bin"),
        (Join-Path ${env:ProgramFiles} "WiX Toolset v3.11\bin"),
        "C:\tools\wix"
    )
    $wixBin = $null
    foreach ($candidate in $wixCandidates) {
        if ($candidate -and (Test-Path (Join-Path $candidate "candle.exe"))) {
            $wixBin = $candidate
            break
        }
    }
    if (-not $wixBin -and (Get-Command candle.exe -ErrorAction SilentlyContinue)) {
        $wixBin = Split-Path (Get-Command candle.exe).Source
    }
    if (-not $wixBin) {
        throw "WiX Toolset v3.11 or v3.14 is required to produce the MSI."
    }
    $env:PATH = "$wixBin;$env:PATH"
    if (-not (Get-Command candle.exe -ErrorAction SilentlyContinue) -or
        -not (Get-Command light.exe -ErrorAction SilentlyContinue)) {
        throw "WiX candle.exe/light.exe could not be found in $wixBin."
    }

    if (-not $SkipDeps) {
        if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
            throw "Node.js/npm is required to build the bundled HUD. Install Node.js 20+ or use -SkipDeps after building frontend/dist."
        }

        Invoke-Native $PythonExe @("-m", "pip", "install", "--upgrade", "pip")
        Invoke-Native $PythonExe @("-m", "pip", "install", "pyinstaller>=6.0")
        Invoke-Native $PythonExe @("-m", "pip", "install", "-e", ".[voice,windows]")

        # Ship a small offline Whisper model so the first microphone use does
        # not depend on a Hugging Face download or internet access.
        if (-not (Test-Path "whisper-model\model.bin")) {
            $downloadWhisper = @'
from pathlib import Path
import shutil
from huggingface_hub import snapshot_download
source = Path(snapshot_download("Systran/faster-whisper-tiny.en"))
target = Path("whisper-model")
target.mkdir(parents=True, exist_ok=True)
for item in source.iterdir():
    if item.is_file():
        shutil.copy2(item, target / item.name)
'@
            Invoke-Native $PythonExe @("-c", $downloadWhisper)
        }

        Push-Location (Join-Path $Root "frontend")
        try {
            Invoke-Native "npm" @("ci")
            Invoke-Native "npm" @("run", "build")
        }
        finally {
            Pop-Location
        }
    }

    if (-not (Test-Path (Join-Path $FrontendDist "index.html"))) {
        throw "frontend/dist/index.html is missing. Run 'cd frontend; npm ci; npm run build' first."
    }

    Remove-Item -Recurse -Force $Dist, (Join-Path $Root "build") -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $Dist -Force | Out-Null

    $iconArgs = @()
    if (Test-Path "assets/icon.ico") {
        $iconArgs = @("--icon", "assets/icon.ico")
    }
    # The neural Piper model and runtime are downloaded by CI before this
    # script runs. Keep local builds useful when those optional assets are not
    # present, but include them whenever they are available.
    $voiceArgs = @()
    if (Test-Path "voice") {
        $voiceArgs += @("--add-data", "voice;voice")
    }
    if (Test-Path "piper") {
        $voiceArgs += @("--add-data", "piper;piper")
    }
    if (Test-Path "whisper-model") {
        $voiceArgs += @("--add-data", "whisper-model;whisper-model")
    }

    # Boot launcher used by the installer auto-start entry. It starts Ollama,
    # serves the bundled HUD/API, and starts the hands-free voice companion.
    $pyArgs = $iconArgs + $voiceArgs + @(
        "--clean", "--noconfirm", "--onefile", "--console",
        "--name", "jarvis",
        "--paths", "src",
        "--add-data", "src/jarvis;jarvis",
        "--add-data", "configs;configs",
        "--add-data", "frontend/dist;frontend/dist",
        "--collect-all", "jarvis",
        "--collect-all", "faster_whisper",
        "--collect-all", "ctranslate2",
        "--hidden-import", "jarvis.startup.windows_boot",
        "--hidden-import", "jarvis.startup.boot_sequence",
        "--hidden-import", "jarvis.startup.morning_brief",
        "--hidden-import", "jarvis.voice",
        "--hidden-import", "jarvis.startup.hud_companion",
        "--hidden-import", "jarvis.tools.adhd_state",
        "--hidden-import", "jarvis.tools.app_launcher",
        "--hidden-import", "jarvis.tools.connection_tools",
        "--hidden-import", "jarvis.tools.career_tools",
        "--hidden-import", "jarvis.connectors.jautomatic",
        "--hidden-import", "jarvis.connectors.google",
        "--hidden-import", "google_auth_oauthlib.flow",
        "--hidden-import", "google.auth.transport.requests",
        "--hidden-import", "google.oauth2.credentials",
        "--hidden-import", "googleapiclient.discovery",
        "--hidden-import", "faster_whisper",
        "--hidden-import", "sounddevice",
        "--hidden-import", "numpy",
        "src/jarvis/startup/windows_boot.py"
    )
    Invoke-Native $PythonExe (@("-m", "PyInstaller") + $pyArgs)

    $exePath = Join-Path $Dist "jarvis.exe"
    if (-not (Test-Path $exePath)) {
        throw "PyInstaller completed but $exePath was not created."
    }

    # Native desktop HUD host used by Start Menu/manual launches. It serves the
    # same production React HUD as development and opens it in WebView2 with an
    # Edge/browser fallback instead of the old unrelated Tkinter approximation.
    $desktopArgs = $iconArgs + $voiceArgs + @(
        "--clean", "--noconfirm", "--onefile", "--windowed",
        "--name", "jarvis-desktop",
        "--paths", "src",
        "--add-data", "frontend/dist;frontend/dist",
        "--add-data", "configs;configs",
        "--collect-all", "jarvis",
        "--collect-all", "webview",
        "--collect-all", "uvicorn",
        "--hidden-import", "jarvis.server.api",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        "src/jarvis/cli/desktop_gui.py"
    )
    Invoke-Native $PythonExe (@("-m", "PyInstaller") + $desktopArgs)

    $desktopExePath = Join-Path $Dist "jarvis-desktop.exe"
    if (-not (Test-Path $desktopExePath)) {
        throw "PyInstaller completed but $desktopExePath was not created."
    }

    # Compile the checked-in WXS so local builds and CI use exactly the same
    # installer definition. ProductVersion is supplied as a WiX variable;
    # this avoids generating a second, easy-to-drift WXS file in the workspace.
    $wxsPath = Join-Path $Root "deploy\windows\jarvis.wxs"
    Invoke-Native "candle.exe" @(
        "-nologo", "-arch", "x64", "-dProductVersion=$Version",
        $wxsPath, "-o", $WixObject
    )
    Invoke-Native "light.exe" @(
        "-nologo", $WixObject, "-ext", "WixUIExtension", "-o", $MsiPath
    )
    if (-not (Test-Path $MsiPath)) {
        throw "WiX completed but $MsiPath was not created."
    }

    $zipPath = Join-Path $Dist "JARVIS-$Version-portable.zip"
    Compress-Archive -Path @($exePath, $desktopExePath) -DestinationPath $zipPath -Force

    Write-Host "=== BUILD COMPLETE ===" -ForegroundColor Green
    Write-Host "Boot EXE: $exePath"
    Write-Host "Desktop HUD EXE: $desktopExePath"
    Write-Host "MSI: $MsiPath"
    Write-Host "ZIP: $zipPath"
}
finally {
    Remove-Item $WixObject -Force -ErrorAction SilentlyContinue
    Pop-Location
}
