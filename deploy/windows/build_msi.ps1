# JARVIS Windows MSI Builder
# Run on Windows 10/11 with Python 3.10+ and WiX Toolset installed
# Usage: .\build_msi.ps1 -Version 0.1.0

param(
    [string]$Version = "0.1.0",
    [string]$PythonExe = "python",
    [switch]$SkipDeps,
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

Write-Host "=== JARVIS MSI Builder v$Version ===" -ForegroundColor Green

# 1. Check prerequisites
Write-Host "`n[1/6] Checking prerequisites..." -ForegroundColor Cyan

# Python
try {
    $pyVersion = & $PythonExe --version 2>&1
    Write-Host "  Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python not found. Install Python 3.10+ from python.org" -ForegroundColor Red
    Write-Host "  Make sure to check 'Add python.exe to PATH'" -ForegroundColor Yellow
    exit 1
}

# WiX Toolset
$wixFound = $false
$wixPaths = @(
    "${env:ProgramFiles(x86)}\WiX Toolset v3.11\bin\candle.exe",
    "${env:ProgramFiles}\WiX Toolset v3.11\bin\candle.exe",
    "C:\tools\wix\candle.exe"
)
foreach ($p in $wixPaths) {
    if (Test-Path $p) {
        $wixFound = $true
        $wixBin = Split-Path $p
        Write-Host "  WiX Toolset: Found at $wixBin" -ForegroundColor Green
        $env:PATH += ";$wixBin"
        break
    }
}
if (-not $wixFound) {
    Write-Host "  WARNING: WiX Toolset not found. Will build EXE only, not MSI" -ForegroundColor Yellow
    Write-Host "  Install WiX from: https://wixtoolset.org/releases/" -ForegroundColor Yellow
    Write-Host "  Or: choco install wixtoolset" -ForegroundColor Yellow
}

# PyInstaller
if (-not $SkipDeps) {
    Write-Host "`n[2/6] Installing build deps..." -ForegroundColor Cyan
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install pyinstaller==6.10.0
    & $PythonExe -m pip install -e .[all] --break-system-packages 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $PythonExe -m pip install -e .[all]
    }
}

# 2. Clean previous builds
Write-Host "`n[3/6] Cleaning..." -ForegroundColor Cyan
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
Remove-Item -Force *.spec -ErrorAction SilentlyContinue

# 3. Build with PyInstaller
Write-Host "`n[4/6] Building EXE with PyInstaller..." -ForegroundColor Cyan

$pyInstallerArgs = @(
    "--name", "jarvis",
    "--console",
    "--icon", "assets/icon.ico",
    "--add-data", "src/jarvis;jarvis",
    "--add-data", "configs;configs",
    "--hidden-import", "jarvis.engine.vllm_engine",
    "--hidden-import", "jarvis.engine.mlx_engine",
    "--hidden-import", "jarvis.engine.litellm_engine",
    "--hidden-import", "jarvis.memory.vector_store",
    "--hidden-import", "jarvis.tools.search_tools",
    "--hidden-import", "faiss",
    "--hidden-import", "sentence_transformers",
    "--hidden-import", "tavily",
    "--hidden-import", "ddgs",
    "--collect-all", "jarvis",
    "src/jarvis/cli/main.py"
)

if ($OneFile) {
    $pyInstallerArgs = @("--onefile") + $pyInstallerArgs
} else {
    $pyInstallerArgs = @("--onedir") + $pyInstallerArgs
}

# Check if icon exists, if not skip
if (-not (Test-Path "assets/icon.ico")) {
    $pyInstallerArgs = $pyInstallerArgs | Where-Object { $_ -ne "assets/icon.ico" -and $_ -ne "--icon" }
    Write-Host "  No icon.ico found, building without icon" -ForegroundColor Yellow
}

Write-Host "  Running: pyinstaller $($pyInstallerArgs -join ' ')" -ForegroundColor Gray
& $PythonExe -m PyInstaller @pyInstallerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "  PyInstaller failed!" -ForegroundColor Red
    exit 1
}

Write-Host "  EXE built at dist/jarvis/" -ForegroundColor Green

# 4. Build MSI with WiX if available
if ($wixFound) {
    Write-Host "`n[5/6] Building MSI with WiX..." -ForegroundColor Cyan

    # Generate WiX source if not exists
    $wxsFile = "deploy/windows/jarvis.wxs"
    if (-not (Test-Path $wxsFile)) {
        Write-Host "  ERROR: $wxsFile not found" -ForegroundColor Red
        exit 1
    }

    # Update version in WXS
    $wxsContent = Get-Content $wxsFile -Raw
    $wxsContent = $wxsContent -replace 'Version="0\.0\.0"', "Version=`"$Version`""
    $wxsContent | Set-Content "$wxsFile.tmp" -Encoding UTF8

    # Compile
    & candle.exe "$wxsFile.tmp" -o deploy/windows/jarvis.wixobj -arch x64
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  candle.exe failed" -ForegroundColor Red
        exit 1
    }

    & light.exe deploy/windows/jarvis.wixobj -o "dist/JARVIS-$Version-x64.msi" -ext WixUIExtension -cultures:en-us
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  light.exe failed" -ForegroundColor Red
        exit 1
    }

    Write-Host "  MSI built: dist/JARVIS-$Version-x64.msi" -ForegroundColor Green
    Remove-Item "$wxsFile.tmp" -Force
} else {
    Write-Host "`n[5/6] Skipping MSI (WiX not found), EXE only" -ForegroundColor Yellow
}

# 5. Create portable ZIP
Write-Host "`n[6/6] Creating portable ZIP..." -ForegroundColor Cyan
Compress-Archive -Path dist/jarvis/* -DestinationPath "dist/JARVIS-$Version-portable.zip" -Force
Write-Host "  ZIP: dist/JARVIS-$Version-portable.zip" -ForegroundColor Green

Write-Host "`n=== Build complete ===" -ForegroundColor Green
Write-Host "  EXE: dist/jarvis/jarvis.exe"
if ($wixFound) {
    Write-Host "  MSI: dist/JARVIS-$Version-x64.msi"
}
Write-Host "  ZIP: dist/JARVIS-$Version-portable.zip"
Write-Host "`nTo install:" -ForegroundColor Cyan
Write-Host "  1. Run MSI installer, or"
Write-Host "  2. Unzip portable and add to PATH, or"
Write-Host "  3. Run: python -m pip install -e ."
