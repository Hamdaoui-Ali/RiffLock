# RiffLock Source of Truth

Last updated: 2026-06-22
Primary owner: Ali Hamdaoui
Project: RiffLock
Active Linear project: https://linear.app/hamdaoui-ali/project/rifflock-1b661f05188f

## Purpose

This document is the working source of truth for RiffLock implementation inside this repository.

It consolidates:

- the active Linear project created on 2026-06-22;
- the archived technical specification created on 2026-06-21;
- the current active backlog structure and implementation order.

If backlog items and this document diverge, use this rule:

1. Security and architecture rules in this document win unless they are explicitly replaced by a newer approved decision.
2. Active Linear issues define implementation order and acceptance criteria.
3. If a conflict exists, update both this document and the relevant Linear issue before coding further.

## Product Summary

RiffLock is a Windows desktop application built in Python for protecting local files and folders.

Its core idea is local file protection with two-factor authentication:

- factor 1: email and password;
- factor 2: an optional secret guitar riff recorded through the laptop microphone.

The riff is used for authentication, not as the encryption key.

## Product Goal

The product goal is to provide a personal, local-first security tool that goes beyond password-only access by combining:

- secure local authentication;
- local key management;
- encrypted file protection;
- an original music-based second factor.

For the MVP, the app must make the following end-to-end flow work reliably:

1. First launch detects whether an owner account exists.
2. The owner creates a local account.
3. The app generates and protects a local data encryption key.
4. The owner logs in with email and password.
5. The owner can protect a local file into a `.rifflock` artifact.
6. The owner can restore a protected file after successful authentication.
7. The owner can enable riff-based 2FA.
8. Future login requires riff verification when 2FA is enabled.

## Non-Goals for MVP

These should not drive early implementation unless explicitly re-approved:

- multi-user support;
- web app or browser workflows;
- cloud sync;
- shared vaults;
- direct use of riff audio as an encryption key;
- advanced recovery system for forgotten passwords;
- full enterprise-grade identity management.

## Product Direction

RiffLock is explicitly:

- a Windows desktop app;
- a single-user personal app;
- a local file and folder protection tool;
- a Python codebase;
- a local SQLite-based application;
- a local AES-256-GCM encryption system.

It is explicitly not a web application.

## Core User Model

There is one user role only: the owner.

The owner can:

- create the local account;
- log in;
- enable or disable riff 2FA;
- enroll a riff;
- verify a riff during login;
- protect files;
- restore files;
- protect folders;
- review protected items;
- review authentication attempts and history;
- change the password;
- manage settings.

## Authentication Model

### First launch

If no owner account exists:

- show setup screen;
- collect email, password, and password confirmation;
- require password-loss warning acknowledgement;
- generate the protected data key during setup.

### Standard login

If an owner account exists:

- show login screen;
- validate email and password;
- unlock the protected data key into memory for the session.

### Riff-based 2FA login

If riff 2FA is enabled:

1. Validate password first.
2. Open riff verification step.
3. Record audio from microphone.
4. Extract riff features.
5. Compare with stored riff template.
6. Grant access only if similarity passes the configured threshold.

## Security Model

### Security principles

- Passwords are never stored in plain text.
- Use a strong password hashing strategy such as Argon2id or bcrypt.
- The file encryption key is random and separate from the password.
- Files are encrypted with AES-256-GCM.
- The riff is not an encryption key.
- Sensitive values must never be logged.
- Temporary decrypted outputs must be controlled and cleaned safely.
- Sensitive operations require password confirmation where appropriate.

### Key model

The correct encryption model is:

1. Generate a random 256-bit data encryption key.
2. Use that key to encrypt protected files.
3. Protect that key in a local key vault.
4. Use a password-derived key to unlock the protected data key.
5. Require successful riff verification before using the unlocked key when riff 2FA is enabled.

### Lockout rules

Current recommended MVP rules from spec and backlog:

- 3 failed password attempts -> temporary lockout;
- 3 failed riff attempts -> temporary lockout.

If the implementation changes these values, the rule must be updated here and in Linear.

## File Protection Model

### Single-file protection

The first-class MVP flow is single-file protection:

1. User selects a file.
2. App encrypts the file using AES-256-GCM.
3. Output is stored as a `.rifflock` file.
4. Metadata is stored in SQLite.
5. Original file must not be deleted silently.

### Restore flow

1. User selects a `.rifflock` file.
2. App validates the file format.
3. App restores the original content only after valid authentication and key access.
4. Existing output files must not be overwritten silently.

### Folder protection

Folder protection is included in the current active backlog, but it should build on the single-file model and preserve safety:

- recursive processing;
- structure preservation;
- partial-failure safety;
- explicit user feedback.

## Audio and Riff Model

The riff flow should follow this pipeline:

1. Record audio from the laptop microphone.
2. Normalize audio.
3. Reject silent or invalid input.
4. Extract stable feature data from the recording.
5. Build a comparable riff template.
6. Compare a new recording to the stored template.
7. Produce a similarity score.
8. Accept or reject based on a configurable threshold.

Likely libraries:

- `sounddevice` for recording;
- `librosa` for feature extraction;
- `aubio` only if a future iteration needs extra pitch or onset analysis beyond the current pipeline.

## Confirmed Technology Stack

- Python
- CustomTkinter
- SQLite
- cryptography AESGCM
- sounddevice
- librosa
- PyInstaller
- pytest

## Suggested Repository Structure

```text
src/rifflock/
  main.py
  config.py
  ui/
  auth/
  audio/
  crypto/
  files/
  storage/
  models/
  utils/

tests/
docs/
README.md
requirements.txt
requirements-dev.txt
pytest.ini
```

## Required Local App Storage

Base directory:

`C:\Users\<user>\AppData\Local\RiffLock`

Required subdirectories:

- `data/`
- `vault/`
- `temp/`
- `logs/`
- `samples/`
- `exports/`

## Suggested Local Database Scope

The SQLite layer should at minimum support:

- `owner_account`
- `key_vault`
- `riff_template`
- `protected_items`
- `auth_attempts`
- `app_settings`

## MVP Backlog Structure

The active Linear project currently uses these milestones:

0. Architecture and Security Baseline
1. Foundation
2. Owner Account, Password Login, and Session
3. File Protection Core
4. Main Desktop UI for File Protection
5. Guitar Riff 2FA Core
6. Settings, Password Change, and Recovery
7. Packaging, Release, and Final Hardening

## Recommended Implementation Order

This is the practical order to work through the current backlog:

1. `HAM-105` Define MVP architecture and security rules.
2. `HAM-69` Initialize project structure and dependencies.
3. `HAM-106` Add app configuration and local storage folders.
4. `HAM-107` Create SQLite database schema and repositories.
5. `HAM-108` Add safe logging and error handling foundation.
6. `HAM-109` Implement password validation and hashing service.
7. `HAM-110` Implement key derivation and encrypted key vault.
8. `HAM-111` Build first-time owner account setup.
9. `HAM-112` Build login screen and session management.
10. `HAM-113` Implement failed login tracking and lockout.
11. `HAM-114` Define `.rifflock` protected file format.
12. `HAM-115` Implement single-file protection service.
13. `HAM-116` Implement single-file restore service.
14. `HAM-117` Implement protected item repository and status management.
15. `HAM-118` and later UI flows.
16. `HAM-123` to `HAM-128` riff recording, feature extraction, enrollment, verification, and lockout.
17. `HAM-129` to `HAM-131` settings, password change, and recovery warning.
18. `HAM-132` to `HAM-134` packaging, docs, and final regression pass.

## Current Project Reality

As of 2026-06-22:

- the active Linear project is defined and structured;
- the local workspace contains almost no implementation yet;
- there is no initialized git repository in this folder;
- this document is the first consolidated local reference inside the repo.

## Coding Rules for This Repository

- Keep security-sensitive logic isolated from UI code.
- Do not mix password verification with file encryption logic.
- Do not log secrets, raw audio, decrypted file contents, or encryption keys.
- Prefer explicit module boundaries over large mixed files.
- Build and verify the single-file protect/restore path before expanding scope.
- Treat the active Linear issue acceptance criteria as implementation contracts.

## Open Decisions to Resolve Early

These areas should be made explicit before deeper implementation:

- final password hashing choice: Argon2id or bcrypt;
- precise key-vault format and derivation parameters;
- exact `.rifflock` binary format layout;
- whether encrypted riff audio samples are stored for playback in MVP;
- exact lockout durations and reset behavior;
- whether folder protection is fully MVP or treated as MVP+.

## Reference Sources

- Active Linear project: `RiffLock` created on 2026-06-22
- Active issues: `HAM-105` through `HAM-134`
- Archived technical specification document from 2026-06-21:
  `RiffLock - Project Context and Technical Specification`

## Maintenance Rule

When major scope, security, or architecture decisions change:

1. update this document;
2. update the relevant Linear issue or create a new decision issue;
3. keep naming and implementation aligned with the documented model.

