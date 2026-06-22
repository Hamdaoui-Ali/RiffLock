"""Typed record models used by the SQLite repository layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OwnerAccountRecord:
    id: int | None
    email: str
    password_hash: str
    password_policy_version: int
    riff_2fa_enabled: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class KeyVaultRecord:
    id: int | None
    owner_account_id: int
    vault_version: int
    encryption_algorithm: str
    kdf_algorithm: str
    kdf_parameters: str
    salt: bytes
    nonce: bytes
    ciphertext: bytes
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class RiffTemplateRecord:
    id: int | None
    owner_account_id: int
    template_version: int
    template_data: bytes
    recording_count: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ProtectedItemRecord:
    id: int | None
    item_type: str
    source_path: str
    artifact_path: str
    status: str
    file_size: int | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AuthAttemptRecord:
    id: int | None
    attempt_type: str
    identifier: str
    was_successful: bool
    failure_reason: str | None
    attempted_at: str


@dataclass(frozen=True)
class AppSettingRecord:
    id: int | None
    setting_key: str
    setting_value: str
    updated_at: str
