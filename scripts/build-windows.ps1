param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($pythonVersion -ne "3.14") {
    throw "RiffLock packaging requires Python 3.14. Active interpreter: $pythonVersion"
}

if ($Clean) {
    Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
}

python -m PyInstaller --noconfirm --clean riff_lock.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller packaging failed. Install project dependencies first with 'pip install -r requirements.txt'."
}

$exePath = Join-Path $root "dist\\RiffLock.exe"
if (-not (Test-Path $exePath)) {
    throw "Expected packaged executable was not created at $exePath"
}

Write-Host "Packaged executable created at $exePath"

