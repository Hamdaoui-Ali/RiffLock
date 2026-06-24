from __future__ import annotations

import sqlite3
from pathlib import Path

from rifflock.models import (
    AppSettingRecord,
    AuthAttemptRecord,
    KeyVaultRecord,
    OwnerAccountRecord,
    ProtectedItemRecord,
    RiffTemplateRecord,
)
from rifflock.storage import (
    AppSettingRepository,
    AuthAttemptRepository,
    KeyVaultRepository,
    OwnerAccountRepository,
    ProtectedItemRepository,
    RiffTemplateRepository,
    create_connection,
    initialize_database,
)


def test_database_initialization_is_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "rifflock.db"

    initialize_database(database_path)
    initialize_database(database_path)

    assert database_path.exists()

    with create_connection(database_path) as connection:
        foreign_keys_enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert foreign_keys_enabled == 1
    assert {
        "owner_account",
        "key_vault",
        "riff_template",
        "protected_items",
        "auth_attempts",
        "app_settings",
    }.issubset(table_names)


def test_repositories_can_save_read_update_and_delete_records(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)

    owner_repo = OwnerAccountRepository(database_path)
    vault_repo = KeyVaultRepository(database_path)
    riff_repo = RiffTemplateRepository(database_path)
    protected_item_repo = ProtectedItemRepository(database_path)
    auth_attempt_repo = AuthAttemptRepository(database_path)
    settings_repo = AppSettingRepository(database_path)

    owner = owner_repo.save(
        OwnerAccountRecord(
            id=None,
            email="owner@example.com",
            password_hash="argon2-hash",
            password_policy_version=1,
            riff_2fa_enabled=False,
            created_at="2026-06-22T00:00:00Z",
            updated_at="2026-06-22T00:00:00Z",
        )
    )
    assert owner.id is not None
    assert owner_repo.get_by_email(owner.email) == owner

    updated_owner = owner_repo.save(
        OwnerAccountRecord(
            id=owner.id,
            email="owner@example.com",
            password_hash="argon2-hash-v2",
            password_policy_version=2,
            riff_2fa_enabled=False,
            created_at=owner.created_at,
            updated_at="2026-06-22T00:05:00Z",
        )
    )
    assert owner_repo.get_by_id(updated_owner.id) == updated_owner

    vault = vault_repo.save(
        KeyVaultRecord(
            id=None,
            owner_account_id=owner.id,
            vault_version=1,
            encryption_algorithm="AES-256-GCM",
            kdf_algorithm="argon2id",
            kdf_parameters='{"memory_cost": 65536}',
            salt=b"salt",
            nonce=b"nonce",
            ciphertext=b"ciphertext",
            created_at="2026-06-22T00:00:01Z",
            updated_at="2026-06-22T00:00:01Z",
        )
    )
    assert vault_repo.get_by_owner_account_id(owner.id) == vault

    riff_template = riff_repo.save(
        RiffTemplateRecord(
            id=None,
            owner_account_id=owner.id,
            template_version=1,
            template_data=b"template-data",
            recording_count=3,
            created_at="2026-06-22T00:00:02Z",
            updated_at="2026-06-22T00:00:02Z",
        )
    )
    assert riff_repo.get_by_owner_account_id(owner.id) == riff_template

    protected_item = protected_item_repo.save(
        ProtectedItemRecord(
            id=None,
            item_type="file",
            source_path=r"C:\input\demo.txt",
            artifact_path=r"C:\exports\demo.rifflock",
            status="protected",
            file_size=128,
            created_at="2026-06-22T00:00:03Z",
            updated_at="2026-06-22T00:00:03Z",
        )
    )
    assert protected_item_repo.get_by_id(protected_item.id) == protected_item

    auth_attempt = auth_attempt_repo.save(
        AuthAttemptRecord(
            id=None,
            attempt_type="password",
            identifier="owner@example.com",
            was_successful=False,
            failure_reason="invalid_password",
            attempted_at="2026-06-22T00:00:04Z",
        )
    )
    assert auth_attempt_repo.get_by_id(auth_attempt.id) == auth_attempt

    newer_auth_attempt = auth_attempt_repo.save(
        AuthAttemptRecord(
            id=None,
            attempt_type="riff",
            identifier="owner@example.com",
            was_successful=False,
            failure_reason="invalid_riff",
            attempted_at="2026-06-22T00:00:06Z",
        )
    )
    assert auth_attempt_repo.list_recent(limit=1) == [newer_auth_attempt]

    setting = settings_repo.save(
        AppSettingRecord(
            id=None,
            setting_key="riff_threshold",
            setting_value="0.80",
            updated_at="2026-06-22T00:00:05Z",
        )
    )
    assert settings_repo.get_by_key("riff_threshold") == setting

    assert protected_item_repo.delete(protected_item.id) is True
    assert protected_item_repo.get_by_id(protected_item.id) is None


def test_foreign_key_constraints_apply_to_owner_linked_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)

    vault_repo = KeyVaultRepository(database_path)

    try:
        vault_repo.save(
            KeyVaultRecord(
                id=None,
                owner_account_id=999,
                vault_version=1,
                encryption_algorithm="AES-256-GCM",
                kdf_algorithm="argon2id",
                kdf_parameters="{}",
                salt=b"salt",
                nonce=b"nonce",
                ciphertext=b"ciphertext",
                created_at="2026-06-22T00:00:01Z",
                updated_at="2026-06-22T00:00:01Z",
            )
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("expected foreign key constraint to reject missing owner")
