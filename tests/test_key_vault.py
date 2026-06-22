from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from rifflock.crypto import DATA_KEY_LENGTH, ENCRYPTION_ALGORITHM, KDF_ALGORITHM, VAULT_VERSION, KeyVaultService
from rifflock.models import OwnerAccountRecord
from rifflock.storage import KeyVaultRepository, OwnerAccountRepository, create_connection, initialize_database
from rifflock.utils.errors import AuthenticationError


def test_generated_data_key_has_expected_length() -> None:
    service = KeyVaultService()
    data_key = service.generate_data_key()

    assert len(data_key) == DATA_KEY_LENGTH


def test_generated_data_keys_are_unique() -> None:
    service = KeyVaultService()

    assert service.generate_data_key() != service.generate_data_key()


def test_key_vault_data_can_be_stored_in_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)

    owner = _create_owner(database_path)
    repository = KeyVaultRepository(database_path)
    service = KeyVaultService(repository)

    bundle = service.store_new_key_vault(owner.id, "StrongPass123!")

    assert bundle.record.id is not None
    stored = repository.get_by_owner_account_id(owner.id)
    assert stored is not None
    assert stored.encryption_algorithm == ENCRYPTION_ALGORITHM
    assert stored.kdf_algorithm == KDF_ALGORITHM
    assert stored.vault_version == VAULT_VERSION


def test_correct_password_can_unlock_key_vault(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)

    owner = _create_owner(database_path)
    repository = KeyVaultRepository(database_path)
    service = KeyVaultService(repository)

    bundle = service.store_new_key_vault(owner.id, "StrongPass123!")
    unlocked_data_key = service.unlock_data_key("StrongPass123!", bundle.record)

    assert unlocked_data_key == bundle.data_key


def test_wrong_password_cannot_unlock_key_vault(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)

    owner = _create_owner(database_path)
    service = KeyVaultService(KeyVaultRepository(database_path))
    bundle = service.store_new_key_vault(owner.id, "StrongPass123!")

    with pytest.raises(AuthenticationError):
        service.unlock_data_key("WrongPass123!", bundle.record)


def test_reprotected_key_vault_keeps_same_data_key_and_rejects_old_password(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)

    owner = _create_owner(database_path)
    service = KeyVaultService(KeyVaultRepository(database_path))
    bundle = service.store_new_key_vault(owner.id, "StrongPass123!")

    updated_record = service.reprotect_data_key(
        current_password="StrongPass123!",
        new_password="NewStrongPass123!",
        record=bundle.record,
    )

    with pytest.raises(AuthenticationError):
        service.unlock_data_key("StrongPass123!", updated_record)

    assert service.unlock_data_key("NewStrongPass123!", updated_record) == bundle.data_key


def test_database_does_not_contain_plain_data_key(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)

    owner = _create_owner(database_path)
    service = KeyVaultService(KeyVaultRepository(database_path))
    bundle = service.store_new_key_vault(owner.id, "StrongPass123!")

    with create_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM key_vault WHERE owner_account_id = ?", (owner.id,)).fetchone()

    assert row is not None
    values = list(dict(row).values())
    assert bundle.data_key not in values
    assert row["ciphertext"] != bundle.data_key
    assert row["salt"] != bundle.data_key
    assert row["nonce"] != bundle.data_key


def _create_owner(database_path: Path) -> OwnerAccountRecord:
    repository = OwnerAccountRepository(database_path)
    return repository.save(
        OwnerAccountRecord(
            id=None,
            email="owner@example.com",
            password_hash="argon2-placeholder",
            password_policy_version=1,
            riff_2fa_enabled=False,
            created_at="2026-06-22T00:00:00Z",
            updated_at="2026-06-22T00:00:00Z",
        )
    )
