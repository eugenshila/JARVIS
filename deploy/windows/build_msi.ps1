# JARVIS Windows MSI Builder - SHILATECH v0.1.9.3 - Fixes disappearing issue
# Run on Windows 10/11 with Python 3.10+ and WiX Toolset installed
# Usage: .\build_msi.ps1 -Version 0.1.9.3 -OneFile (OneFile fixes disappearing)

param(
    [string]$Version = "0.1.9.3",
    [string]$PythonExe = "python",
    [switch]$SkipDeps,
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

Write-Host "=== JARVIS SHILATECH MSI Builder v$Version ===" -ForegroundColor Green
Write-Host "Fix: OneFile mode fixes opening but disappearing (single exe contains all DLLs)" -ForegroundColor Cyan

# Default to OneFile to fix disappearing - single exe no missing deps
if (-not $OneFile) {
    Write-Host "WARNING: Onedir build may cause disappearing if MSI only includes exe without _internal folder" -ForegroundColor Yellow
    Write-Host "Recommend: .\build_msi.ps1 -Version $Version -OneFile  # Fixes disappearing" -ForegroundColor Yellow
    # For backward compat, still allow onedir but warn
}

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

# 3. Build with PyInstaller - OneFile fixes disappearing
Write-Host "`n[4/6] Building EXE with PyInstaller (OneFile fixes disappearing)..." -ForegroundColor Cyan

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
    "--hidden-import", "jarvis.tools.network_tools",
    "--hidden-import", "jarvis.core.network",
    "--hidden-import", "jarvis.engine.auto_engine",
    "--hidden-import", "jarvis.agents.ironman",
    "--hidden-import", "jarvis.agents.adhd_coach",
    "--hidden-import", "jarvis.tools.adhd_tools",
    "--hidden-import", "jarvis.tools.adhd_advanced",
    "--hidden-import", "jarvis.tools.calendar_tools",
    "--hidden-import", "jarvis.tools.email_tools",
    "--hidden-import", "jarvis.tools.focus_enhanced",
    "--hidden-import", "jarvis.tools.face_tool",
    "--hidden-import", "jarvis.tools.startup_tools",
    "--hidden-import", "jarvis.speech.voice_io",
    "--hidden-import", "faiss",
    "--hidden-import", "sentence_transformers",
    "--hidden-import", "tavily",
    "--hidden-import", "ddgs",
    "--collect-all", "jarvis",
    "src/jarvis/cli/main.py"
)

if ($OneFile) {
    $pyInstallerArgs = @("--onefile") + $pyInstallerArgs
    Write-Host "  Building ONEFILE - fixes disappearing, single exe contains all deps" -ForegroundColor Green
} else {
    $pyInstallerArgs = @("--onedir") + $pyInstallerArgs
    Write-Host "  Building ONEDIR - may cause disappearing if MSI only packages exe without _internal" -ForegroundColor Yellow
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

if ($OneFile) {
    Write-Host "  EXE built at dist/jarvis.exe (onefile - no disappearing)" -ForegroundColor Green
} else {
    Write-Host "  EXE built at dist/jarvis/ (onedir - need heat harvesting for MSI)" -ForegroundColor Green
}

# 4. Build MSI with WiX if available
if ($wixFound) {
    Write-Host "`n[5/6] Building MSI with WiX (onefile fixes disappearing)..." -ForegroundColor Cyan

    $wxsFile = "deploy/windows/jarvis.wxs"
    if (-not (Test-Path $wxsFile)) {
        Write-Host "  ERROR: $wxsFile not found" -ForegroundColor Red
        exit 1
    }

    # Update version in WXS
    $wxsContent = Get-Content $wxsFile -Raw
    $wxsContent = $wxsContent -replace 'Version="0\.0\.0"', "Version=`"$Version`""
    $wxsContent | Set-Content "$wxsFile.tmp" -Encoding UTF8

    if ($OneFile) {
        # Simple WXS for onefile - single exe, no missing deps, fixes disappearing
        $simpleWxs = @"
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="JARVIS - SHILATECH - Personal AI" Language="1033" Version="$Version" Manufacturer="SHILATECH" UpgradeCode="a1b2c3d4-e5f6-7890-abcd-ef1234567890">
    <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine" Description="JARVIS SHILATECH Local-first Personal AI Voice Hybrid - Fixes disappearing" />
    <MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." />
    <MediaTemplate EmbedCab="yes" />
    <Feature Id="ProductFeature" Title="JARVIS SHILATECH" Level="1">
      <ComponentRef Id="MainExecutable" />
      <ComponentRef Id="PathEnv" />
      <ComponentRef Id="StartMenuShortcut" />
    </Feature>
    <UIRef Id="WixUI_InstallDir" />
    <Property Id="WIXUI_INSTALLDIR" Value="INSTALLFOLDER" />
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFiles64Folder">
        <Directory Id="INSTALLFOLDER" Name="JARVIS SHILATECH">
          <Component Id="MainExecutable" Guid="*">
            <File Id="JarvisExe" Source="dist\jarvis.exe" KeyPath="yes" />
          </Component>
        </Directory>
      </Directory>
      <Directory Id="ProgramMenuFolder">
        <Directory Id="ApplicationProgramsFolder" Name="JARVIS SHILATECH">
          <Component Id="StartMenuShortcut" Guid="*">
            <Shortcut Id="ApplicationStartMenuShortcut" Name="JARVIS SHILATECH" Description="Personal AI, Voice speaks online/offline, Good Morning Eugene" Target="[INSTALLFOLDER]jarvis.exe" WorkingDirectory="INSTALLFOLDER"/>
            <Shortcut Id="UninstallProduct" Name="Uninstall JARVIS" Description="Uninstall JARVIS SHILATECH" Target="[System64Folder]msiexec.exe" Arguments="/x [ProductCode]"/>
            <RemoveFolder Id="CleanUpShortCut" Directory="ApplicationProgramsFolder" On="uninstall"/>
            <RegistryValue Root="HKCU" Key="Software\JARVIS" Name="installed" Type="integer" Value="1" KeyPath="yes"/>
          </Component>
        </Directory>
      </Directory>
    </Directory>
    <DirectoryRef Id="TARGETDIR">
      <Component Id="PathEnv" Guid="*">
        <Environment Id="PATH" Name="PATH" Value="[INSTALLFOLDER]" Permanent="no" Part="last" Action="set" System="yes" />
        <RegistryValue Root="HKCU" Key="Software\JARVIS" Name="path" Type="integer" Value="1" KeyPath="yes"/>
      </Component>
    </DirectoryRef>
  </Product>
</Wix>
"@
        $simpleWxs | Out-File -FilePath "$wxsFile.tmp" -Encoding utf8
    }

    # Compile
    & candle.exe "$wxsFile.tmp" -o deploy/windows/jarvis.wixobj -arch x64
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  candle.exe failed" -ForegroundColor Red
        exit 1
    }

    & light.exe deploy/windows/jarvis.wixobj -o "dist/JARVIS-$Version-x64.msi" -ext WixUIExtension -cultures:en-us
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  light with UI ext failed, trying without" -ForegroundColor Yellow
        & light.exe deploy/windows/jarvis.wixobj -o "dist/JARVIS-$Version-x64.msi" -cultures:en-us
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  light.exe failed" -ForegroundColor Red
        exit 1
    }

    Write-Host "  MSI built: dist/JARVIS-$Version-x64.msi (onefile - fixes disappearing)" -ForegroundColor Green
    Remove-Item "$wxsFile.tmp" -Force
} else {
    Write-Host "`n[5/6] Skipping MSI (WiX not found), EXE only" -ForegroundColor Yellow
}

# 5. Create portable ZIP
Write-Host "`n[6/6] Creating portable ZIP..." -ForegroundColor Cyan
if ($OneFile) {
    Compress-Archive -Path dist/jarvis.exe -DestinationPath "dist/JARVIS-$Version-onefile.zip" -Force
    Write-Host "  ZIP onefile: dist/JARVIS-$Version-onefile.zip" -ForegroundColor Green
} else {
    Compress-Archive -Path dist/jarvis/* -DestinationPath "dist/JARVIS-$Version-portable.zip" -Force
    Write-Host "  ZIP: dist/JARVIS-$Version-portable.zip" -ForegroundColor Green
}

Write-Host "`n=== Build complete SHILATECH v$Version ===" -ForegroundColor Green
if ($OneFile) {
    Write-Host "  EXE: dist/jarvis.exe (onefile - fixes disappearing)" -ForegroundColor Green
} else {
    Write-Host "  EXE: dist/jarvis/jarvis.exe (onedir - may need heat for MSI)" -ForegroundColor Yellow
}
if ($wixFound) {
    Write-Host "  MSI: dist/JARVIS-$Version-x64.msi (SHILATECH, fixes disappearing)" -ForegroundColor Green
}
Write-Host "`nTo install:" -ForegroundColor Cyan
Write-Host "  1. Run MSI installer, or"
Write-Host "  2. Unzip portable and add to PATH, or"
Write-Host "  3. Run: python -m pip install -e . && python app.py  # Always works, no disappearing"
Write-Host "`nIf still disappearing:" -ForegroundColor Yellow
Write-Host "  - Run from CMD: jarvis.exe --help to see error"
Write-Host "  - Use python app.py (Tkinter stays open)"
Write-Host "  - Frontend: cd frontend && npm run dev -> http://localhost:5173"
Write-Host "  - See docs/DISAPPEARING_FIX.md"
