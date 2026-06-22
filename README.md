# RiffLock

RiffLock is a Windows desktop application for protecting local files and folders with password-based authentication and optional guitar-riff 2FA.

RiffLock is local-first. It stores application state in the Windows AppData directory, uses a separate wrapped data key for encryption, and treats the guitar riff as an authentication factor rather than an encryption key.

## Recovery warning

If you forget your RiffLock password, you may not be able to open your protected files again. Keep your password somewhere safe.

## Current status

This repository contains the MVP implementation for:

- first-run owner account setup
- password login and in-memory session key access
- single-file and folder protection
- file restore from `.rifflock` artifacts
- optional riff-based 2FA enrollment and login verification
- settings, password change, and local packaging support

## Installation

### Install from source

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

This installs the runtime dependencies plus the test and packaging tools used in this repo.

### Build a Windows executable

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\scripts\build-windows.ps1 -Clean
```

The packaged executable is expected at `dist\RiffLock.exe`.

## Project layout

```text
src/rifflock/
tests/
docs/
requirements.txt
requirements-dev.txt
pytest.ini
```

## Technical documentation

- [docs/architecture.md](docs/architecture.md): architecture boundaries and service ownership
- [docs/security.md](docs/security.md): password, key-vault, logging, and security rules
- [docs/file-format.md](docs/file-format.md): `.rifflock` container format
- [docs/database.md](docs/database.md): SQLite schema and table responsibilities
- [docs/audio.md](docs/audio.md): riff recording and feature extraction approach
- [docs/packaging.md](docs/packaging.md): Windows packaging and release smoke tests
- [docs/run-and-test.md](docs/run-and-test.md): step-by-step local run and verification guide

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Package Windows executable

```powershell
.\scripts\build-windows.ps1 -Clean
```

The PyInstaller configuration is in `riff_lock.spec`. The packaged app should still create its database, logs, vault, and temp folders under `C:\Users\<user>\AppData\Local\RiffLock`.

Detailed packaging and manual smoke-test steps are in [docs/packaging.md](docs/packaging.md).

## Run the app

```powershell
python main.py
```

## Test command

```powershell
python -m pytest -q
```

## First-time setup flow

1. Launch the app on a machine with no existing owner account.
2. Enter the owner email, password, and password confirmation.
3. Read and acknowledge the password-loss warning.
4. Complete account creation.
5. The app creates the wrapped data key and local SQLite database in AppData.

## Login flow

1. Enter the owner email and password.
2. If password login succeeds and riff 2FA is disabled, the app unlocks the protected data key into session memory.
3. If riff 2FA is enabled, the app opens the riff verification step before creating the authenticated session.

## Protect file flow

1. Sign in.
2. Choose a file from the dashboard.
3. Accept the default vault output location or choose a custom output path.
4. The app encrypts the file into a `.rifflock` artifact and stores metadata in SQLite.
5. The original file remains unchanged.

## Protect folder flow

1. Sign in.
2. Choose a folder from the dashboard.
3. Confirm recursive protection.
4. The app protects supported files and preserves the folder-oriented output structure.
5. Partial failures are surfaced as explicit results rather than silent skips.

## Restore flow

1. Sign in with access to the unlocked session data key.
2. Select a `.rifflock` artifact.
3. Choose a restore destination.
4. The app validates the container format and decrypts the payload.
5. Existing files are never overwritten silently.

## Riff 2FA setup

1. Open Settings.
2. Start riff enrollment and confirm the account password.
3. Record the required riff samples through the microphone.
4. After enrollment, future login requires password validation followed by riff verification.
5. Riff 2FA can be disabled later with password confirmation.

## Known MVP limitations

- single local owner account only
- Windows desktop target only
- no cloud sync or remote backup
- no forgotten-password recovery
- no enterprise identity or account management
- riff audio is not a biometric guarantee and is not used as the encryption key
- packaging smoke tests are documented, but clean-profile packaged validation remains a manual step

## Run tests

```powershell
pytest
```
