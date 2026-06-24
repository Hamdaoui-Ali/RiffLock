"""Repository layer for the local SQLite database."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import Generic, TypeVar

from rifflock.models import (
    AppSettingRecord,
    AuthAttemptRecord,
    KeyVaultRecord,
    OwnerAccountRecord,
    ProtectedItemRecord,
    RiffTemplateRecord,
)
from rifflock.storage.database import create_connection

RecordT = TypeVar("RecordT")


class BaseRepository(Generic[RecordT]):
    """Base repository that owns database connections for a table."""

    table_name: str

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        return create_connection(self.database_path)

    def delete(self, record_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                f"DELETE FROM {self.table_name} WHERE id = ?",
                (record_id,),
            )
            connection.commit()
        return cursor.rowcount > 0


class OwnerAccountRepository(BaseRepository[OwnerAccountRecord]):
    table_name = "owner_account"

    def save(self, record: OwnerAccountRecord) -> OwnerAccountRecord:
        with self._connect() as connection:
            if record.id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO owner_account (
                        email, password_hash, password_policy_version, riff_2fa_enabled, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.email,
                        record.password_hash,
                        record.password_policy_version,
                        int(record.riff_2fa_enabled),
                        record.created_at,
                        record.updated_at,
                    ),
                )
                connection.commit()
                return replace(record, id=int(cursor.lastrowid))

            connection.execute(
                """
                UPDATE owner_account
                SET email = ?, password_hash = ?, password_policy_version = ?, riff_2fa_enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    record.email,
                    record.password_hash,
                    record.password_policy_version,
                    int(record.riff_2fa_enabled),
                    record.updated_at,
                    record.id,
                ),
            )
            connection.commit()
        return record

    def get_by_id(self, record_id: int) -> OwnerAccountRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM owner_account WHERE id = ?",
                (record_id,),
            ).fetchone()
        return None if row is None else _owner_account_from_row(row)

    def get_by_email(self, email: str) -> OwnerAccountRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM owner_account WHERE email = ?",
                (email,),
            ).fetchone()
        return None if row is None else _owner_account_from_row(row)

    def get_owner_account(self) -> OwnerAccountRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM owner_account ORDER BY id ASC LIMIT 1",
            ).fetchone()
        return None if row is None else _owner_account_from_row(row)

    def has_owner_account(self) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM owner_account LIMIT 1",
            ).fetchone()
        return row is not None

    def update_password(
        self,
        *,
        owner_account_id: int,
        password_hash: str,
        password_policy_version: int,
        updated_at: str,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        if connection is None:
            with self._connect() as managed_connection:
                self.update_password(
                    owner_account_id=owner_account_id,
                    password_hash=password_hash,
                    password_policy_version=password_policy_version,
                    updated_at=updated_at,
                    connection=managed_connection,
                )
                managed_connection.commit()
            return

        connection.execute(
            """
            UPDATE owner_account
            SET password_hash = ?, password_policy_version = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                password_hash,
                password_policy_version,
                updated_at,
                owner_account_id,
            ),
        )


class KeyVaultRepository(BaseRepository[KeyVaultRecord]):
    table_name = "key_vault"

    def save(self, record: KeyVaultRecord) -> KeyVaultRecord:
        with self._connect() as connection:
            if record.id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO key_vault (
                        owner_account_id, vault_version, encryption_algorithm, kdf_algorithm, kdf_parameters,
                        salt, nonce, ciphertext, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.owner_account_id,
                        record.vault_version,
                        record.encryption_algorithm,
                        record.kdf_algorithm,
                        record.kdf_parameters,
                        record.salt,
                        record.nonce,
                        record.ciphertext,
                        record.created_at,
                        record.updated_at,
                    ),
                )
                connection.commit()
                return replace(record, id=int(cursor.lastrowid))

            connection.execute(
                """
                UPDATE key_vault
                SET owner_account_id = ?, vault_version = ?, encryption_algorithm = ?, kdf_algorithm = ?, kdf_parameters = ?,
                    salt = ?, nonce = ?, ciphertext = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    record.owner_account_id,
                    record.vault_version,
                    record.encryption_algorithm,
                    record.kdf_algorithm,
                    record.kdf_parameters,
                    record.salt,
                    record.nonce,
                    record.ciphertext,
                    record.updated_at,
                    record.id,
                ),
            )
            connection.commit()
        return record

    def get_by_owner_account_id(self, owner_account_id: int) -> KeyVaultRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM key_vault WHERE owner_account_id = ?",
                (owner_account_id,),
            ).fetchone()
        return None if row is None else KeyVaultRecord(**dict(row))

    def update_protected_data(
        self,
        *,
        record_id: int,
        kdf_parameters: str,
        salt: bytes,
        nonce: bytes,
        ciphertext: bytes,
        updated_at: str,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        if connection is None:
            with self._connect() as managed_connection:
                self.update_protected_data(
                    record_id=record_id,
                    kdf_parameters=kdf_parameters,
                    salt=salt,
                    nonce=nonce,
                    ciphertext=ciphertext,
                    updated_at=updated_at,
                    connection=managed_connection,
                )
                managed_connection.commit()
            return

        connection.execute(
            """
            UPDATE key_vault
            SET kdf_parameters = ?, salt = ?, nonce = ?, ciphertext = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                kdf_parameters,
                salt,
                nonce,
                ciphertext,
                updated_at,
                record_id,
            ),
        )


class RiffTemplateRepository(BaseRepository[RiffTemplateRecord]):
    table_name = "riff_template"

    def save(self, record: RiffTemplateRecord) -> RiffTemplateRecord:
        with self._connect() as connection:
            if record.id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO riff_template (
                        owner_account_id, template_version, template_data, recording_count,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.owner_account_id,
                        record.template_version,
                        record.template_data,
                        record.recording_count,
                        record.created_at,
                        record.updated_at,
                    ),
                )
                connection.commit()
                return replace(record, id=int(cursor.lastrowid))

            connection.execute(
                """
                UPDATE riff_template
                SET owner_account_id = ?, template_version = ?, template_data = ?,
                    recording_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    record.owner_account_id,
                    record.template_version,
                    record.template_data,
                    record.recording_count,
                    record.updated_at,
                    record.id,
                ),
            )
            connection.commit()
        return record

    def get_by_owner_account_id(self, owner_account_id: int) -> RiffTemplateRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM riff_template WHERE owner_account_id = ?",
                (owner_account_id,),
            ).fetchone()
        return None if row is None else RiffTemplateRecord(**dict(row))


class ProtectedItemRepository(BaseRepository[ProtectedItemRecord]):
    table_name = "protected_items"

    def save(self, record: ProtectedItemRecord) -> ProtectedItemRecord:
        with self._connect() as connection:
            if record.id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO protected_items (
                        item_type, source_path, artifact_path, status, file_size, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.item_type,
                        record.source_path,
                        record.artifact_path,
                        record.status,
                        record.file_size,
                        record.created_at,
                        record.updated_at,
                    ),
                )
                connection.commit()
                return replace(record, id=int(cursor.lastrowid))

            connection.execute(
                """
                UPDATE protected_items
                SET item_type = ?, source_path = ?, artifact_path = ?, status = ?,
                    file_size = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    record.item_type,
                    record.source_path,
                    record.artifact_path,
                    record.status,
                    record.file_size,
                    record.updated_at,
                    record.id,
                ),
            )
            connection.commit()
        return record

    def get_by_id(self, record_id: int) -> ProtectedItemRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM protected_items WHERE id = ?",
                (record_id,),
            ).fetchone()
        return None if row is None else ProtectedItemRecord(**dict(row))

    def get_by_artifact_path(self, artifact_path: str) -> ProtectedItemRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM protected_items WHERE artifact_path = ?",
                (artifact_path,),
            ).fetchone()
        return None if row is None else ProtectedItemRecord(**dict(row))

    def list_all(self) -> list[ProtectedItemRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM protected_items ORDER BY created_at ASC, id ASC",
            ).fetchall()
        return [ProtectedItemRecord(**dict(row)) for row in rows]


class AuthAttemptRepository(BaseRepository[AuthAttemptRecord]):
    table_name = "auth_attempts"

    def save(self, record: AuthAttemptRecord) -> AuthAttemptRecord:
        with self._connect() as connection:
            if record.id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO auth_attempts (
                        attempt_type, identifier, was_successful, failure_reason, attempted_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        record.attempt_type,
                        record.identifier,
                        int(record.was_successful),
                        record.failure_reason,
                        record.attempted_at,
                    ),
                )
                connection.commit()
                return replace(record, id=int(cursor.lastrowid))

            connection.execute(
                """
                UPDATE auth_attempts
                SET attempt_type = ?, identifier = ?, was_successful = ?, failure_reason = ?,
                    attempted_at = ?
                WHERE id = ?
                """,
                (
                    record.attempt_type,
                    record.identifier,
                    int(record.was_successful),
                    record.failure_reason,
                    record.attempted_at,
                    record.id,
                ),
            )
            connection.commit()
        return record

    def get_by_id(self, record_id: int) -> AuthAttemptRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM auth_attempts WHERE id = ?",
                (record_id,),
            ).fetchone()
        return None if row is None else _auth_attempt_from_row(row)

    def list_recent(self, limit: int = 100) -> list[AuthAttemptRecord]:
        bounded_limit = max(min(limit, 500), 1)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM auth_attempts
                ORDER BY attempted_at DESC, id DESC
                LIMIT ?
                """,
                (bounded_limit,),
            ).fetchall()
        return [_auth_attempt_from_row(row) for row in rows]
    def list_by_identifier_and_type(
        self,
        identifier: str,
        attempt_type: str,
    ) -> list[AuthAttemptRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM auth_attempts
                WHERE identifier = ? AND attempt_type = ?
                ORDER BY attempted_at ASC
                """,
                (identifier, attempt_type),
            ).fetchall()
        return [_auth_attempt_from_row(row) for row in rows]

    def delete_by_identifier_and_type(self, identifier: str, attempt_type: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM auth_attempts
                WHERE identifier = ? AND attempt_type = ?
                """,
                (identifier, attempt_type),
            )
            connection.commit()
        return cursor.rowcount


class AppSettingRepository(BaseRepository[AppSettingRecord]):
    table_name = "app_settings"

    def save(self, record: AppSettingRecord) -> AppSettingRecord:
        with self._connect() as connection:
            if record.id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO app_settings (setting_key, setting_value, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        record.setting_key,
                        record.setting_value,
                        record.updated_at,
                    ),
                )
                connection.commit()
                return replace(record, id=int(cursor.lastrowid))

            connection.execute(
                """
                UPDATE app_settings
                SET setting_key = ?, setting_value = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    record.setting_key,
                    record.setting_value,
                    record.updated_at,
                    record.id,
                ),
            )
            connection.commit()
        return record

    def get_by_key(self, setting_key: str) -> AppSettingRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM app_settings WHERE setting_key = ?",
                (setting_key,),
            ).fetchone()
        return None if row is None else AppSettingRecord(**dict(row))


def _auth_attempt_from_row(row: sqlite3.Row) -> AuthAttemptRecord:
    data = dict(row)
    data["was_successful"] = bool(data["was_successful"])
    return AuthAttemptRecord(**data)


def _owner_account_from_row(row: sqlite3.Row) -> OwnerAccountRecord:
    data = dict(row)
    data["riff_2fa_enabled"] = bool(data["riff_2fa_enabled"])
    return OwnerAccountRecord(**data)
