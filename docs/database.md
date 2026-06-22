# RiffLock SQLite Schema

Last updated: 2026-06-22
Source issue: `HAM-133` / `RLD-029`

## Purpose

This document describes the SQLite schema used by the RiffLock MVP and the ownership of each table.

SQLite is the source of truth for local state and metadata. Secret material is stored only in protected form.

## Database location

The runtime database path is:

`C:\Users\<user>\AppData\Local\RiffLock\data\rifflock.db`

The packaged application must continue to use this AppData location instead of writing beside the executable.

## Schema summary

The MVP schema contains these tables:

- `owner_account`
- `key_vault`
- `riff_template`
- `protected_items`
- `auth_attempts`
- `app_settings`

## Table responsibilities

### `owner_account`

Stores the single local owner identity record.

Columns:

- `id`: integer primary key
- `email`: unique owner email
- `password_hash`: Argon2 verifier string
- `password_policy_version`: password-policy version marker
- `riff_2fa_enabled`: boolean-like integer flag
- `created_at`: ISO 8601 UTC timestamp
- `updated_at`: ISO 8601 UTC timestamp

Rules:

- there is only one effective owner account in the MVP
- passwords are never stored in plain text

### `key_vault`

Stores the wrapped application data key used to encrypt protected content.

Columns:

- `id`: integer primary key
- `owner_account_id`: unique foreign key to `owner_account`
- `vault_version`: vault format version
- `encryption_algorithm`: protected-key encryption algorithm
- `kdf_algorithm`: password-based derivation algorithm
- `kdf_parameters`: serialized derivation settings
- `salt`: derivation salt
- `nonce`: AES-GCM nonce
- `ciphertext`: wrapped data-key ciphertext
- `created_at`: ISO 8601 UTC timestamp
- `updated_at`: ISO 8601 UTC timestamp

Rules:

- the wrapped record protects one random 256-bit data key
- password changes re-wrap the same data key
- protected files do not each get their own vault entry

### `riff_template`

Stores the enrolled riff template for optional 2FA.

Columns:

- `id`: integer primary key
- `owner_account_id`: unique foreign key to `owner_account`
- `template_version`: template format version
- `template_data`: serialized template bytes
- `recording_count`: number of recordings used for enrollment
- `created_at`: ISO 8601 UTC timestamp
- `updated_at`: ISO 8601 UTC timestamp

Rules:

- the riff is used for authentication, not as an encryption key
- disabling riff 2FA removes the stored template

### `protected_items`

Stores metadata for protected files and folders.

Columns:

- `id`: integer primary key
- `item_type`: file or folder classification
- `source_path`: original source path
- `artifact_path`: protected artifact output path
- `status`: protection or restore status
- `file_size`: original size where applicable
- `created_at`: ISO 8601 UTC timestamp
- `updated_at`: ISO 8601 UTC timestamp

Rules:

- metadata supports dashboard and restore tracking
- encrypted payload bytes are not stored in SQLite

### `auth_attempts`

Stores login and riff-verification attempt history for lockout decisions.

Columns:

- `id`: integer primary key
- `attempt_type`: password or riff
- `identifier`: normalized email or owner identifier
- `was_successful`: boolean-like integer flag
- `failure_reason`: optional safe reason code
- `attempted_at`: ISO 8601 UTC timestamp

Rules:

- this table supports temporary lockout enforcement
- it must not store raw secrets or audio content

### `app_settings`

Stores non-secret owner preferences.

Columns:

- `id`: integer primary key
- `setting_key`: unique key name
- `setting_value`: serialized string value
- `updated_at`: ISO 8601 UTC timestamp

Current examples:

- riff recording duration
- riff similarity threshold

## Foreign-key rules

- `key_vault.owner_account_id` references `owner_account.id`
- `riff_template.owner_account_id` references `owner_account.id`
- both relationships use `ON DELETE CASCADE`

## Migration note

The MVP uses lightweight idempotent schema initialization and targeted column updates inside `src/rifflock/storage/database.py`.

If the schema becomes more complex, it should move to explicit versioned migrations.
