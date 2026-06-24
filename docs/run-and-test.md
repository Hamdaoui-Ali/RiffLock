# RiffLock Run and Test Guide

Last updated: 2026-06-22

## Purpose

This guide explains how to:

- install everything needed for the repo
- run the app locally
- run the automated tests
- manually verify the main MVP flows
- tell whether the app is working correctly

## 1. Prerequisites

You need:

- Windows
- Python 3.14
- a microphone if you want to test riff 2FA

## 2. Open the project

Open PowerShell in the repository root:

```powershell
cd C:\path\to\RiffLock
```

## 3. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.venv\Scripts\Activate.ps1
```

## 4. Install dependencies

Install everything with one command:

```powershell
pip install -r requirements.txt
```

This installs:

- app runtime dependencies
- test tooling
- packaging tooling

## 5. Run the app

Start the desktop app with:

```powershell
python main.py
```

## 6. What should happen on first launch

If no owner account exists yet:

1. the setup screen should appear
2. you should see the password-loss warning
3. you should be able to enter email and password
4. account creation should require the warning acknowledgment

The app should create its local data under:

`C:\Users\<your-user>\AppData\Local\RiffLock`

You should see these folders appear there:

- `data`
- `vault`
- `temp`
- `logs`
- `samples`
- `exports`

You should also see the SQLite database here:

`C:\Users\<your-user>\AppData\Local\RiffLock\data\rifflock.db`

## 7. What should happen after setup

After creating the owner account:

1. close and reopen the app if needed
2. the login flow should use the saved local database
3. logging in with the correct password should succeed
4. logging in with the wrong password should fail

## 8. Run the automated tests

Run the full suite:

```powershell
python -m pytest -q
```

If everything is healthy, you should see all tests pass.

Current expected result in this repo:

- full suite passes
- no failures

## 9. Manual test checklist

Use this checklist to confirm the app works end to end.

### First launch and setup

1. Delete or move the AppData folder only if you want a clean first-launch test:
   `C:\Users\<your-user>\AppData\Local\RiffLock`
2. Run `python main.py`
3. Confirm the setup screen appears
4. Confirm the recovery warning is visible
5. Try creating an account without acknowledging the warning
6. Confirm account creation is blocked
7. Create the account correctly

Working result:

- setup screen appears
- warning is visible
- acknowledgment is required
- account is created successfully

Broken result:

- app opens to the wrong screen
- warning is missing
- account can be created without acknowledgment
- setup crashes

### Login without riff 2FA

1. Start the app
2. Log in with the correct email and password
3. Confirm the dashboard opens
4. Log out if applicable
5. Try a wrong password

Working result:

- correct credentials open the dashboard
- wrong credentials are rejected
- no secret values appear in error messages

Broken result:

- correct login fails
- wrong login succeeds
- app leaks internal or sensitive details in errors

### Failed password lockout

1. Enter the wrong password three times
2. Try the correct password immediately after

Working result:

- login is temporarily blocked after the threshold

Broken result:

- unlimited wrong attempts are allowed
- correct login works during active lockout

### Protect a single file

1. Log in
2. Select a small test file from the dashboard
3. Accept the default output path or choose one manually

Working result:

- a `.rifflock` file is created
- the original file is still there
- no silent overwrite occurs

Broken result:

- no artifact is created
- original file is deleted or modified
- existing output is overwritten silently

### Restore a single file

1. Log in
2. Select a `.rifflock` file
3. Choose a restore destination

Working result:

- the restored file contents match the original
- restore fails safely for invalid or tampered files
- existing output files are not overwritten silently

Broken result:

- restored content is wrong
- corrupt files restore as if valid
- output is overwritten without warning

### Protect a folder

1. Log in
2. Choose a folder with nested files
3. Confirm recursive protection

Working result:

- nested files are protected
- folder structure is preserved
- temporary/system files are skipped where expected
- partial failures are reported explicitly

Broken result:

- only top-level files are protected
- output structure is wrong
- failures are silent

### Password change

1. Open Settings
2. Change the password using the current password
3. Log out
4. Log back in with the new password
5. Try the old password

Working result:

- new password works
- old password no longer works

Broken result:

- old password still works
- new password fails
- login state becomes inconsistent

### Restore an old file after password change

1. Protect a file before changing the password
2. Change the password
3. Log in with the new password
4. Restore the old protected file

Working result:

- the old file still restores correctly

Broken result:

- restore fails because of the password change

### Riff 2FA enrollment and login

1. Open Settings
2. Start riff enrollment
3. Confirm the password
4. Complete the recording flow
5. Log out
6. Log back in with password
7. Complete riff verification

Working result:

- password step succeeds first
- riff verification is required after password login
- successful riff verification opens the session

Broken result:

- riff 2FA enables without password confirmation
- dashboard opens before riff verification
- correct riff never works

### Failed riff lockout

1. With riff 2FA enabled, fail riff verification three times
2. Try again with the correct riff

Working result:

- riff verification is temporarily blocked after the threshold

Broken result:

- unlimited failed riff attempts are allowed
- correct riff works during active lockout

### App restart persistence

1. Set up the account
2. Protect at least one file
3. Close the app
4. Reopen the app
5. Log in again

Working result:

- account still exists
- login still works
- previous protected items remain usable

Broken result:

- app behaves like first launch again
- database state is missing

## 10. Check logs safely

Logs are stored in:

`C:\Users\<your-user>\AppData\Local\RiffLock\logs`

What you should expect:

- timestamps
- safe status messages
- sanitized error information

What you should not see:

- plain passwords
- encryption keys
- decrypted file contents
- raw audio data
- full secret template data

If logs contain secrets, that is a security bug.

## 11. If the app does not start

Check these first:

1. confirm the virtual environment is activated
2. confirm dependencies installed successfully
3. run `python -m pytest -q`
4. inspect the latest file in the AppData `logs` folder

Common causes:

- missing Python package
- audio dependency problems
- microphone/device issues
- local environment mismatch

## 12. Optional packaging test

If you want to build the Windows executable:

```powershell
.\scripts\build-windows.ps1 -Clean
```

If packaging succeeds, verify:

- `dist\RiffLock.exe` exists
- the packaged app still uses AppData
- first launch, login, protect, restore, and riff recording still work

## 13. Quick success signal

The app is in a good state if all of these are true:

- `python -m pytest -q` passes
- first launch shows setup correctly
- login works
- file protect and restore work
- password change works
- riff 2FA works if a microphone is available
- logs do not expose sensitive data

