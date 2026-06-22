# Packaging and Release

Last updated: 2026-06-22
Source issue: `HAM-132` / `RLD-028`

## Goal

Package RiffLock as a Windows desktop executable using PyInstaller without moving runtime state beside the executable.

## Packaging rules

- The packaged app entrypoint is `main.py`.
- Runtime data must continue to resolve under `C:\Users\<user>\AppData\Local\RiffLock`.
- SQLite, logs, vault data, temp files, samples, and exports must not be written into the `dist/` folder.
- The packaged executable name is `RiffLock.exe`.

## Build prerequisites

- Windows
- Python 3.12
- A virtual environment with `requirements.txt` installed

## Build command

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\scripts\build-windows.ps1 -Clean
```

The PyInstaller configuration lives in `riff_lock.spec`.

## Dependency notes

The spec explicitly collects data or submodules for:

- `customtkinter`
- `librosa`
- `sounddevice`
- `aubio`
- `argon2`
- `cryptography`

These are included because they are central to the UI, audio pipeline, password hashing, and key-vault logic.

## Manual packaged-app smoke test

1. Build `dist\RiffLock.exe`.
2. Launch the executable from Explorer or PowerShell.
3. Confirm first launch creates `C:\Users\<user>\AppData\Local\RiffLock`.
4. Confirm `data\rifflock.db`, `logs\`, `vault\`, and `temp\` are created under AppData.
5. Create the owner account from the setup screen.
6. Close the app and relaunch `RiffLock.exe`.
7. Confirm login still uses the AppData database created on first launch.

## Manual feature verification

1. Log in from the packaged executable.
2. Protect a test file and confirm a `.rifflock` artifact is created.
3. Restore the protected file and confirm contents match the original.
4. Open Settings and confirm AppData folder access still works.
5. If audio dependencies are available on the machine, run riff enrollment and riff verification.

## Clean-profile check

Where possible, repeat the first-launch smoke test on a clean Windows user profile to catch missing packaged dependencies or accidental local-environment coupling.
