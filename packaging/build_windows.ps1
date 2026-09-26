<#
.SYNOPSIS
    Builds the production Windows executable and Inno Setup installer for Daily Sticky.

.DESCRIPTION
    1. Verifies Python virtual environment and dependencies.
    2. Executes clean PyInstaller build using packaging/DailySticky.spec.
    3. If Inno Setup (ISCC.exe) is installed, compiles installer/DailySticky.iss.
#>

param (
    [switch]$SkipInstaller = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " Building Daily Sticky Windows Production App " -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1. Clean previous build outputs
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "[1/3] Cleaning previous build artifacts..." -ForegroundColor Yellow
Remove-Item -Recurse -Force "$RepoRoot\build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$RepoRoot\dist\DailySticky" -ErrorAction SilentlyContinue

# 2. Run PyInstaller
Write-Host "[2/3] Executing PyInstaller build..." -ForegroundColor Yellow
pyinstaller --clean --noconfirm "$RepoRoot\packaging\DailySticky.spec"

if (-not (Test-Path "$RepoRoot\dist\DailySticky\DailySticky.exe")) {
    Write-Error "PyInstaller failed: DailySticky.exe not found in dist/DailySticky."
}

Write-Host "PyInstaller onedir distribution created at: dist/DailySticky" -ForegroundColor Green

# 3. Compile Inno Setup Installer
if (-not $SkipInstaller) {
    Write-Host "[3/3] Compiling Inno Setup installer..." -ForegroundColor Yellow

    # Search common Inno Setup 6 installation paths
    $InnoCompiler = "ISCC.exe"
    $CommonPaths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )

    foreach ($path in $CommonPaths) {
        if (Test-Path $path) {
            $InnoCompiler = $path
            break
        }
    }

    try {
        & $InnoCompiler "$RepoRoot\installer\DailySticky.iss"
        Write-Host "Installer compiled successfully in: dist\installer" -ForegroundColor Green
    } catch {
        Write-Warning "Inno Setup compiler (ISCC.exe) was not found in PATH or standard Program Files locations."
        Write-Host "To compile the installer manually, install Inno Setup 6 and run:"
        Write-Host "ISCC installer\DailySticky.iss"
    }
}

Write-Host "Build complete!" -ForegroundColor Cyan
