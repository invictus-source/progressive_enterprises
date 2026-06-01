$ErrorActionPreference = "Stop"

Write-Host "======================================================="
Write-Host " Building Progressive Enterprises Windows Installer"
Write-Host "======================================================="

Write-Host "`n[1/4] Bundling application with PyInstaller (via spec)..."
# Use the spec file -- it handles all Qt plugin paths automatically
.venv\Scripts\pyinstaller --noconfirm "Progressive Enterprises.spec"

Write-Host "`n[2/4] Writing qt.conf next to the .exe..."
# PyInstaller onedir layout: exe is at dist\<name>\, internals in _internal\
# qt.conf must sit NEXT TO the .exe and point into _internal\PySide6\plugins
$qtConfContent = @"
[Paths]
Plugins = ./_internal/PySide6/plugins
"@
$qtConfContent | Out-File -FilePath "dist\Progressive Enterprises\qt.conf" -Encoding ascii -NoNewline
Write-Host "   qt.conf written to dist\Progressive Enterprises\qt.conf"

# Verify critical plugin DLLs are present
Write-Host "`n   Verifying plugin presence..."
$stylesPath  = "dist\Progressive Enterprises\_internal\PySide6\plugins\styles"
$platformPath = "dist\Progressive Enterprises\_internal\PySide6\plugins\platforms"
if (Test-Path "$stylesPath\qmodernwindowsstyle.dll") {
    Write-Host "   [OK] styles\qmodernwindowsstyle.dll" -ForegroundColor Green
} else {
    Write-Host "   [WARN] styles plugin missing!" -ForegroundColor Yellow
}
if (Test-Path "$platformPath\qwindows.dll") {
    Write-Host "   [OK] platforms\qwindows.dll" -ForegroundColor Green
} else {
    Write-Host "   [WARN] platforms\qwindows.dll missing!" -ForegroundColor Yellow
}

Write-Host "`n[3/4] Checking for Inno Setup Compiler..."
$isccInstalled  = Get-Command "iscc" -ErrorAction SilentlyContinue
$defaultIsccPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
$localIsccPath   = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"

if (-not $isccInstalled -and -not (Test-Path $defaultIsccPath) -and -not (Test-Path $localIsccPath)) {
    Write-Host "Inno Setup is missing. Installing via winget..." -ForegroundColor Yellow
    winget install -e --id JRSoftware.InnoSetup --accept-source-agreements --accept-package-agreements
    Start-Sleep -Seconds 3
}

Write-Host "`n[4/4] Compiling Setup.exe..."
if (Test-Path $defaultIsccPath) {
    & $defaultIsccPath "progressive.iss"
} elseif (Test-Path $localIsccPath) {
    & $localIsccPath "progressive.iss"
} elseif (Get-Command "iscc" -ErrorAction SilentlyContinue) {
    iscc "progressive.iss"
} else {
    Write-Host "Could not find ISCC.exe. Please restart your terminal and run this script again." -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Build Successful! The installer is located in the 'installers' directory." -ForegroundColor Green
