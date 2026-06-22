# RiffLock Security Baseline

Last updated: 2026-06-22
Source issue: `HAM-105` / `RLD-000`

## Purpose

This document defines the concrete security rules for the RiffLock MVP.

If implementation code conflicts with this document, this document wins until a newer approved decision replaces it.

## Security Principles

- Passwords are never stored in plain text.
- The data encryption key is random and distinct from the password.
- File encryption uses AES-256-GCM.
- The guitar riff is an authentication factor, not an encryption key.
- Secrets, plaintext file contents, raw audio, and decrypted keys are never logged.
- Decrypted material exists only for the shortest practical time.
- Security-sensitive steps must be isolated from UI code.

## Password Handling Strategy

RiffLock will use `Argon2id` for password hashing in the MVP.

Decision:

- algorithm: `Argon2id`
- salt: unique random salt per password
- output: store only the encoded verifier string produced by the password hashing library
- rehash policy: support future rehash-on-login if parameters are strengthened later

Rationale:

- Argon2id is memory-hard and appropriate for password storage.
- The encoded hash format avoids inventing a custom password storage layout.

Rules:

- passwords are validated for strength before account creation or password change;
- password comparison uses constant-time library verification paths;
- password hashing and password verification live in `auth/`, not `crypto/`.

## Password Login vs Data-Key Unlock

These are separate operations.

Required flow:

1. Verify the password hash.
2. Enforce password lockout policy if needed.
3. Require riff verification when enabled.
4. Only then derive the password-based wrapping key.
5. Use the wrapping key to unwrap the stored data encryption key.

This separation prevents file-encryption logic from depending directly on password verification code.

## Key-Vault Strategy

The MVP uses a single random 256-bit data encryption key for content protection.

Decision:

1. Generate a random 32-byte data key during initial account setup.
2. Derive a wrapping key from the password using a dedicated KDF configuration.
3. Wrap the data key with AES-256-GCM.
4. Store the wrapped blob and its metadata in `key_vault`.
5. Keep the unwrapped data key in memory only during an authenticated session.

Stored vault metadata must include:

- vault format version
- KDF algorithm name
- KDF parameters
- salt
- AES-GCM nonce
- wrapped data-key ciphertext
- authentication tag if not bundled by the library format
- creation and rotation timestamps

Rules:

- the password itself is never stored in the vault;
- the same wrapped data key remains valid across protected files;
- changing the password re-wraps the same data key instead of re-encrypting every protected file.

## File Encryption Rules

Protected content uses `AESGCM` from `cryptography`.

Rules:

- each protected file uses a fresh random nonce;
- each protected file includes format versioning;
- authenticated encryption failures are treated as restore failures, not partial success;
- plaintext output is written only after full validation succeeds.

## `.rifflock` File Format Baseline

The exact binary layout may evolve, but the MVP format must include:

- magic header identifying `.rifflock`
- format version
- original filename metadata
- original file size
- encryption algorithm identifier
- nonce
- ciphertext payload

Rules:

- format parsing must reject unsupported versions;
- restore must fail safely on malformed metadata;
- the original source file must not be deleted automatically after protection;
- restore targets must not overwrite existing files silently.

## Audio Security Rules

The riff is a second authentication factor only.

Rules:

- raw audio is not used as an encryption key;
- raw audio is not written to logs;
- enrollment samples, if stored, must be encrypted at rest;
- silent, invalid, or extremely short recordings are rejected before comparison;
- similarity thresholds come from config/settings, not hardcoded UI logic.

## Lockout Baseline

Current MVP policy:

- 3 failed password attempts trigger temporary lockout
- 3 failed riff attempts trigger temporary lockout

The implementation must centralize these thresholds so later tuning does not require UI rewrites.

The precise lockout duration should default to a short MVP-safe value and remain configurable in code until product policy is finalized.

## Logging and Error Rules

Allowed to log:

- timestamps
- operation type
- high-level status
- safe file paths when useful
- sanitized exception categories

Never log:

- passwords
- password hashes beyond stored verifier handling
- encryption keys
- derived keys
- plaintext file contents
- raw audio buffers
- full riff templates if they expose recoverable biometric detail

Errors returned to UI must be safe and human-readable. Internal exceptions may be wrapped, but sensitive payloads must be removed first.

## Temporary Data Handling

Rules:

- temporary decrypted outputs must be explicitly controlled;
- temp locations must be inside the app-managed AppData tree;
- cleanup should run after restore/protect operations when temp artifacts are used;
- failures during cleanup must never expose plaintext in logs.

## MVP Limitations

The MVP security model does not provide:

- forgotten-password recovery
- hardware-backed key storage guarantees
- secure deletion guarantees for arbitrary user files
- anti-malware protection on the host machine
- biometric-grade identity assurance from riff audio
- multi-user isolation on shared Windows accounts

These limits must stay visible in code comments, UI copy where relevant, and user documentation.
