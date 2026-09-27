# JARVIS Windows MSI builder
param([string]$Version = "0.2.0",[string]$PythonExe = "python",[switch]$SkipDeps)
$ErrorActionPreference = "Stop"
Write-Host "=== Building JARVIS SHILATECH $Version ===" -ForegroundColor Green
if (-not (Get-Command $PythonExe -ErrorAction SilentlyContinue)) { throw "Python 3.10+ not found." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "Node.js/npm not found." }
$wix = $null
$candidates = @("\${env:ProgramFiles(x86)}\WiX Toolset v3.11\bin","\${env:ProgramFiles}\WiX Toolset v3.11\bin","C:\tools\wix")
foreach ($dir in $candidates) { if (Test-Path (Join-Path $dir "candle.exe")) { $wix = $dir; break } }
if (-not $wix) { throw "WiX Toolset v3.x is required to produce the MSI." }
$env:PATH += ";$wix"
if (-not $SkipDeps) {
  & $PythonExe -m pip install --upgrade pip
  & $PythonExe -m pip install "pyinstaller>=6.0"
  & $PythonExe -m pip install -e ".[voice,windows]"
  if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
  Push-Location frontend; npm ci; npm run build
  if ($LASTEXITCODE -ne 0) { Pop-Location; throw "HUD frontend build failed." }; Pop-Location
}
if (-not (Test-Path "frontend\dist\index.html")) { throw "frontend/dist/index.html is missing." }
Remove-Item -Recurse -Force dist,build -ErrorAction SilentlyContinue
$pyArgs = @("--onefile","--console","--name","jarvis","--add-data","src/jarvis;jarvis","--add-data","configs;configs","--add-data","frontend/dist;frontend/dist","--collect-all","jarvis","--collect-all","faster_whisper","--collect-all","ctranslate2","--hidden-import","jarvis.startup.windows_boot","--hidden-import","jarvis.startup.hud_companion","--hidden-import","faster_whisper","--hidden-import","sounddevice","--hidden-import","numpy","src/jarvis/startup/windows_boot.py")
if (Test-Path "assets/icon.ico") { $pyArgs = @("--icon","assets/icon.ico") + $pyArgs }
& $PythonExe -m PyInstaller @pyArgs
if ($LASTEXITCODE -ne 0 -or -not (Test-Path "dist\jarvis.exe")) { throw "PyInstaller build failed." }
$wxs = @"
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
<Product Id="*" Name="JARVIS - SHILATECH" Language="1033" Version="$Version" Manufacturer="SHILATECH" UpgradeCode="a1b2c3d4-e5f6-7890-abcd-ef1234567890">
<Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine" />
<MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." />
<MediaTemplate EmbedCab="yes" />
<Feature Id="ProductFeature" Title="JARVIS SHILATECH" Level="1"><ComponentRef Id="MainExecutable" /><ComponentRef Id="StartMenuShortcut" /><ComponentRef Id="AutoStart" /></Feature>
<UIRef Id="WixUI_InstallDir" /><Property Id="WIXUI_INSTALLDIR" Value="INSTALLFOLDER" />
<Directory Id="TARGETDIR" Name="SourceDir"><Directory Id="ProgramFiles64Folder"><Directory Id="INSTALLFOLDER" Name="JARVIS SHILATECH"><Component Id="MainExecutable" Guid="*"><File Id="JarvisExe" Source="dist\jarvis.exe" KeyPath="yes" /></Component></Directory></Directory>
<Directory Id="ProgramMenuFolder"><Directory Id="ApplicationProgramsFolder" Name="JARVIS SHILATECH"><Component Id="StartMenuShortcut" Guid="*"><Shortcut Id="StartMenuShortcut" Name="JARVIS SHILATECH" Description="Local JARVIS voice assistant" Target="[INSTALLFOLDER]jarvis.exe" WorkingDirectory="INSTALLFOLDER" /><Shortcut Id="UninstallProduct" Name="Uninstall JARVIS" Target="[System64Folder]msiexec.exe" Arguments="/x [ProductCode]" /><RemoveFolder Id="CleanUpShortCut" Directory="ApplicationProgramsFolder" On="uninstall" /><RegistryValue Root="HKCU" Key="Software\JARVIS" Name="installed" Type="integer" Value="1" KeyPath="yes" /></Component></Directory></Directory>
</Directory>
</Product></Wix>
"@
$wxsPath="deploy/windows/jarvis.generated.wxs"; $wixobj="deploy/windows/jarvis.generated.wixobj"
$wxs | Set-Content $wxsPath -Encoding UTF8
& candle.exe $wxsPath -o $wixobj -arch x64; if ($LASTEXITCODE -ne 0) { throw "WiX candle.exe failed." }
& light.exe $wixobj -o "dist/JARVIS-$Version-x64.msi" -ext WixUIExtension; if ($LASTEXITCODE -ne 0) { throw "WiX light.exe failed." }
Compress-Archive -Path "dist/jarvis.exe" -DestinationPath "dist/JARVIS-$Version-portable.zip" -Force
Remove-Item $wxsPath,$wixobj -Force -ErrorAction SilentlyContinue
Write-Host "=== BUILD COMPLETE ===" -ForegroundColor Green
Write-Host "EXE: dist/jarvis.exe"; Write-Host "MSI: dist/JARVIS-$Version-x64.msi"
