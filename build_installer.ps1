[CmdletBinding()]
param(
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version = "1.0.0",
    [switch]$SkipTests,
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw "Windows installer builds must run on Windows. From Linux, run the GitHub Actions workflow instead."
}
if (-not [System.Environment]::Is64BitProcess) {
    throw "Use 64-bit Python so the generated installer matches its x64 target."
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @()
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE`: $FilePath $Arguments"
    }
}

Write-Host "======================================================="
Write-Host " Building Progressive Enterprises $Version for Windows"
Write-Host "======================================================="

$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($null -eq $pyLauncher) {
        throw "Python 3.12+ was not found. Install 64-bit Python, then run this script again."
    }
    Invoke-Checked -FilePath $pyLauncher.Source -Arguments @("-3.12", "-m", "venv", ".venv")
}

if (-not $SkipDependencyInstall) {
    Write-Host "`n[1/6] Installing build dependencies..."
    Invoke-Checked -FilePath $pythonExe -Arguments @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-Checked -FilePath $pythonExe -Arguments @("-m", "pip", "install", "-r", "requirements.txt")
} else {
    Write-Host "`n[1/6] Dependency installation skipped."
}

if (-not $SkipTests) {
    Write-Host "`n[2/6] Running automated tests..."
    $oldQtPlatform = $env:QT_QPA_PLATFORM
    $oldDataDir = $env:PROGRESSIVE_DATA_DIR
    $testDataDir = Join-Path ([System.IO.Path]::GetTempPath()) ("ProgressiveEnterprises-Tests-" + [guid]::NewGuid())
    try {
        $env:QT_QPA_PLATFORM = "offscreen"
        $env:PROGRESSIVE_DATA_DIR = $testDataDir
        Invoke-Checked -FilePath $pythonExe -Arguments @("-m", "unittest", "discover", "-s", "tests", "-v")
    } finally {
        $env:QT_QPA_PLATFORM = $oldQtPlatform
        $env:PROGRESSIVE_DATA_DIR = $oldDataDir
        if (Test-Path $testDataDir) {
            Remove-Item -LiteralPath $testDataDir -Recurse -Force
        }
    }
} else {
    Write-Host "`n[2/6] Tests skipped."
}

Write-Host "`n[3/6] Checking data-safety rules..."
$installerSource = Get-Content "progressive.iss" -Raw
if ($installerSource -match '(?im)^\s*\[UninstallDelete\]\s*$') {
    throw "Unsafe installer rule found: [UninstallDelete] is not permitted."
}
if ($installerSource -match '(?i)progressive\.db|settings\.json|prefs\.json|launcher\.json') {
    throw "The installer must not package or manipulate live business-data files."
}

Write-Host "`n[4/6] Bundling the application with PyInstaller..."
foreach ($generatedDir in @("build", "dist")) {
    $generatedPath = Join-Path $projectRoot $generatedDir
    if (Test-Path $generatedPath) {
        Remove-Item -LiteralPath $generatedPath -Recurse -Force
    }
}
$buildMetadataDir = Join-Path $projectRoot "build"
New-Item -ItemType Directory -Path $buildMetadataDir -Force | Out-Null
Set-Content -LiteralPath (Join-Path $buildMetadataDir "build_version.txt") -Value $Version -Encoding Ascii -NoNewline

$versionParts = $Version.Split('.')
$major = [int]$versionParts[0]
$minor = [int]$versionParts[1]
$patch = [int]$versionParts[2]
$versionInfo = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($major, $minor, $patch, 0),
    prodvers=($major, $minor, $patch, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'Progressive Enterprises'),
        StringStruct('FileDescription', 'Progressive Enterprises Business Suite'),
        StringStruct('FileVersion', '$Version'),
        StringStruct('InternalName', 'Progressive Enterprises'),
        StringStruct('LegalCopyright', 'Copyright Progressive Enterprises and Emberflock Labs'),
        StringStruct('OriginalFilename', 'Progressive Enterprises.exe'),
        StringStruct('ProductName', 'Progressive Enterprises'),
        StringStruct('ProductVersion', '$Version')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@
Set-Content -LiteralPath (Join-Path $buildMetadataDir "windows_version_info.txt") -Value $versionInfo -Encoding Ascii
Invoke-Checked -FilePath $pythonExe -Arguments @("-m", "PyInstaller", "--noconfirm", "--clean", "Progressive Enterprises.spec")

$appDir = Join-Path $projectRoot "dist\Progressive Enterprises"
$appExe = Join-Path $appDir "Progressive Enterprises.exe"
$qtPlatformPlugin = Join-Path $appDir "_internal\PySide6\plugins\platforms\qwindows.dll"
if (-not (Test-Path $appExe)) { throw "Packaged executable is missing: $appExe" }
if (-not (Test-Path $qtPlatformPlugin)) { throw "Qt Windows platform plugin is missing: $qtPlatformPlugin" }
if (-not (Test-Path (Join-Path $appDir "_internal\assets\logo.ico"))) { throw "Packaged application icon is missing." }

$qtConf = "[Paths]`r`nPlugins = ./_internal/PySide6/plugins`r`n"
Set-Content -LiteralPath (Join-Path $appDir "qt.conf") -Value $qtConf -Encoding Ascii -NoNewline

Write-Host "`n[5/6] Running the packaged Windows self-test..."
$selfTestDataDir = Join-Path ([System.IO.Path]::GetTempPath()) ("ProgressiveEnterprises-SelfTest-" + [guid]::NewGuid())
$oldDataDir = $env:PROGRESSIVE_DATA_DIR
try {
    $env:PROGRESSIVE_DATA_DIR = $selfTestDataDir
    $process = Start-Process -FilePath $appExe -ArgumentList "--self-test" -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        $selfTestError = Join-Path $selfTestDataDir "self_test_error.log"
        if (Test-Path $selfTestError) {
            Write-Host "Packaged self-test traceback:" -ForegroundColor Red
            Get-Content -LiteralPath $selfTestError | Write-Host
        }
        throw "Packaged application self-test failed with exit code $($process.ExitCode)."
    }
} finally {
    $env:PROGRESSIVE_DATA_DIR = $oldDataDir
    if (Test-Path $selfTestDataDir) {
        Remove-Item -LiteralPath $selfTestDataDir -Recurse -Force
    }
}

Write-Host "`n[6/6] Compiling the Inno Setup installer..."
$isccCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    $isccCommand = Get-Command "iscc" -ErrorAction SilentlyContinue
    if ($isccCommand) { $iscc = $isccCommand.Source }
}
if (-not $iscc -and -not $SkipDependencyInstall) {
    $winget = Get-Command "winget" -ErrorAction SilentlyContinue
    if ($winget) {
        Invoke-Checked -FilePath $winget.Source -Arguments @("install", "-e", "--id", "JRSoftware.InnoSetup", "--accept-source-agreements", "--accept-package-agreements")
        $iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
}
if (-not $iscc) {
    throw "Inno Setup 6 was not found. Install it or rerun without -SkipDependencyInstall."
}

Invoke-Checked -FilePath $iscc -Arguments @("/DMyAppVersion=$Version", "progressive.iss")

$installer = Join-Path $projectRoot "installers\ProgressiveEnterprises_Setup_${Version}_x64.exe"
if (-not (Test-Path $installer)) { throw "Expected installer was not created: $installer" }
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash.ToLowerInvariant()
$hashFile = "$installer.sha256"
Set-Content -LiteralPath $hashFile -Value "$hash  $([System.IO.Path]::GetFileName($installer))" -Encoding Ascii

Write-Host "`nBuild successful." -ForegroundColor Green
Write-Host "Installer: $installer"
Write-Host "SHA256:    $hash"
