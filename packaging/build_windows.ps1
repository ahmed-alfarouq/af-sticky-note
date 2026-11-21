<#
.SYNOPSIS
    Builds the production Windows executable and Inno Setup installer for Daily Sticky.

.DESCRIPTION
    1. Reads the version from APP_VERSION in app/config/settings.py (the only place it is set).
    2. Executes a clean PyInstaller build using packaging/DailySticky.spec.
    3. If Inno Setup (ISCC.exe) is installed, compiles installer/DailySticky.iss with that
       version and writes a SHA-256 checksum file next to the installer.
#>

param (
    [switch]$SkipInstaller = $false
)

$ErrorActionPreference = "Stop"

# 0. Locate the repository and read the version
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$SettingsFile = Join-Path $RepoRoot "app\config\settings.py"
$VersionLine = Select-String -Path $SettingsFile -Pattern '^APP_VERSION\s*=\s*"(?<v>\d+\.\d+\.\d+)"' | Select-Object -First 1
if (-not $VersionLine) {
    Write-Error "Could not read APP_VERSION (expected X.Y.Z) from app/config/settings.py."
}
$Version = $VersionLine.Matches[0].Groups["v"].Value

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " Building Daily Sticky $Version for Windows" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1. Clean previous build outputs
Write-Host "[1/3] Cleaning previous build artifacts..." -ForegroundColor Yellow
Remove-Item -Recurse -Force "$RepoRoot\build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$RepoRoot\dist\DailySticky" -ErrorAction SilentlyContinue

# 2. Run PyInstaller
Write-Host "[2/3] Executing PyInstaller build..." -ForegroundColor Yellow
pyinstaller --clean --noconfirm "$RepoRoot\packaging\DailySticky.spec"
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path "$RepoRoot\dist\DailySticky\DailySticky.exe")) {
    Write-Error "PyInstaller failed: DailySticky.exe not found in dist/DailySticky."
}

Write-Host "PyInstaller onedir distribution created at: dist/DailySticky" -ForegroundColor Green

# 3. Compile Inno Setup Installer
if (-not $SkipInstaller) {
    Write-Host "[3/3] Compiling Inno Setup installer..." -ForegroundColor Yellow

    # Search PATH, then the common Inno Setup 6 installation paths
    $InnoCompiler = $null
    $OnPath = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($OnPath) {
        $InnoCompiler = $OnPath.Source
    } else {
        $CommonPaths = @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
            "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
        )
        $InnoCompiler = $CommonPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
    }

    if (-not $InnoCompiler) {
        Write-Warning "Inno Setup compiler (ISCC.exe) was not found in PATH or standard Program Files locations."
        Write-Host "To compile the installer manually, install Inno Setup 6 and run:"
        Write-Host "ISCC /DMyAppVersion=$Version installer\DailySticky.iss"
    } else {
        & $InnoCompiler "/DMyAppVersion=$Version" "$RepoRoot\installer\DailySticky.iss"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Inno Setup failed with exit code $LASTEXITCODE."
        }

        $Installer = "$RepoRoot\dist\installer\DailySticky-Setup-$Version.exe"
        if (-not (Test-Path $Installer)) {
            Write-Error "Installer not found after compiling: $Installer"
        }

        $Hash = (Get-FileHash -Algorithm SHA256 -Path $Installer).Hash.ToLower()
        "$Hash  $(Split-Path -Leaf $Installer)" | Set-Content -Encoding ascii "$Installer.sha256"

        Write-Host "Installer compiled successfully in: dist\installer" -ForegroundColor Green
        Write-Host "SHA-256: $Hash" -ForegroundColor Green
    }
}

Write-Host "Build complete! (version $Version)" -ForegroundColor Cyan
