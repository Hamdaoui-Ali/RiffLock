# RiffLock Architecture Baseline

Last updated: 2026-06-22
Source issue: `HAM-105` / `RLD-000`

## Purpose

This document defines the minimum architecture baseline for the RiffLock MVP.

It translates `docs/sot.md` into implementation boundaries so later milestones can add code without mixing security-critical concerns.

## MVP System Shape

RiffLock is a local-first Windows desktop application written in Python.

The MVP is organized around these layers:

1. `ui/`
2. service-level domain modules in `auth/`, `audio/`, `crypto/`, and `files/`
3. `storage/`
4. `models/`
5. `utils/`

These layers must stay separated. UI code must not directly implement cryptography, SQLite queries, audio feature extraction, or file-format parsing.

## Repository Layout

The target repository layout for implementation is:

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
```

The functional ownership is:

- `main.py`: app bootstrap, startup wiring, dependency assembly
- `config.py`: AppData paths, constants, environment-sensitive settings
- `ui/`: screens, dialogs, navigation, user-facing validation messages
- `auth/`: password validation, password hashing, login orchestration, session state, lockout policy
- `audio/`: microphone capture, signal normalization, riff feature extraction, similarity comparison
- `crypto/`: key generation, key derivation, AES-GCM encryption/decryption, key-vault protection
- `files/`: `.rifflock` container parsing, protect/restore workflows, folder recursion safety
- `storage/`: SQLite schema, migrations, repositories, persistence boundaries
- `models/`: typed application models and DTOs
- `utils/`: safe logging, clocks, error types, filesystem helpers

## Core Separation Rules

The following boundaries are mandatory:

- UI only calls service-level APIs and never touches SQLite directly.
- Repositories only persist and fetch data; they do not hash passwords, derive keys, or encrypt files.
- File protection uses the decrypted data key supplied by session/auth flows and never verifies passwords on its own.
- Audio services never decide account access on their own; they return features, scores, and validation results.
- Logging helpers redact sensitive values before anything is written to disk.

## Authentication and Session Model

Authentication and key access are separate concerns.

The required sequence is:

1. Verify email and password against the stored account record.
2. If the password is correct, determine whether riff 2FA is enabled.
3. If riff 2FA is enabled, perform riff verification.
4. Only after required authentication succeeds, unlock the protected data key into memory.
5. Store the unlocked data key only in session memory for the lifetime of the authenticated session.

This rule is important:

- password verification proves the owner identity;
- key unlock grants access to encrypted content.

They must not collapse into one mixed function or module.

## Data Ownership

SQLite is the source of truth for application state and metadata.

Expected database ownership:

- `owner_account`: email, password hash, password policy version, timestamps
- `key_vault`: wrapped data-key blob and associated vault metadata
- `riff_template`: enrolled riff template metadata and encrypted stored material if needed
- `protected_items`: records for protected files and folders
- `auth_attempts`: password and riff failure history for lockout enforcement
- `app_settings`: user-configurable non-secret settings

Ownership rules:

- secrets are not stored in plain text in SQLite;
- repositories expose narrowly scoped methods per aggregate;
- schema changes must be versioned deliberately once migrations are introduced.

## Service Boundaries

The MVP should converge on these service types:

- `AccountSetupService`: first-run owner creation and initial key-vault creation
- `LoginService`: email/password validation and login orchestration
- `SessionService`: in-memory session lifecycle and unlocked key lifetime
- `LockoutService`: failed-attempt tracking and temporary lockout decisions
- `KeyVaultService`: data-key generation, wrapping, unwrapping, and re-protection
- `FileProtectionService`: encrypt a single file into `.rifflock`
- `FileRestoreService`: validate and restore a `.rifflock` artifact
- `FolderProtectionService`: recursive protect flow with partial-failure handling
- `RiffEnrollmentService`: multi-sample enrollment pipeline
- `RiffVerificationService`: compare a new recording against the enrolled template

## Startup Flow

The application startup contract is:

1. Resolve AppData paths.
2. Create required local directories if missing.
3. Initialize logging.
4. Initialize SQLite connection and schema.
5. Check whether an owner account exists.
6. Route to first-run setup or login UI.

## File Processing Model

The first supported path is single-file protection.

Rules:

- original files are never deleted silently;
- restore destinations are explicit and must not overwrite silently;
- folder protection builds on the single-file pipeline rather than using a separate crypto model;
- `.rifflock` parsing and validation live in `files/`, not in the UI.

## Error Handling Baseline

Errors should be classified before UI presentation:

- user-correctable validation errors
- authentication failures
- lockout conditions
- file format errors
- filesystem conflicts
- unexpected internal failures

UI shows safe messages. Internal traces may be logged, but secrets and plaintext content must never be included.

## MVP Limitations

The baseline architecture explicitly does not cover:

- multi-user account separation
- cloud sync or remote backup
- account recovery for forgotten passwords
- web application endpoints
- using raw riff audio as an encryption key
- enterprise identity or admin controls

These limitations are deliberate scope controls for the MVP.
