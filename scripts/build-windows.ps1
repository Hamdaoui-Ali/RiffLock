param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($Clean) {
    Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
}

python -m PyInstaller --noconfirm --clean riff_lock.spec

$exePath = Join-Path $root "dist\\RiffLock.exe"
if (-not (Test-Path $exePath)) {
    throw "Expected packaged executable was not created at $exePath"
}

Write-Host "Packaged executable created at $exePath"
