from __future__ import annotations

from pathlib import Path

import pytest

from rifflock.auth import MIN_PASSWORD_LENGTH, PasswordService
from rifflock.models import OwnerAccountRecord
from rifflock.storage import OwnerAccountRepository, initialize_database
from rifflock.utils.errors import ValidationError


def test_valid_and_invalid_email_addresses() -> None:
    service = PasswordService()

    assert service.validate_email(" Owner@Example.com ") == "owner@example.com"

    with pytest.raises(ValidationError):
        service.validate_email("owner-at-example.com")

    with pytest.raises(ValidationError):
        service.validate_email("owner@example")


def test_weak_password_rejection() -> None:
    service = PasswordService()

    weak_passwords = [
        "short1!A",
        "alllowercase1!",
        "ALLUPPERCASE1!",
        "NoDigitsHere!",
        "NoSymbolsHere1",
    ]

    for password in weak_passwords:
        with pytest.raises(ValidationError):
            service.validate_password_strength(password)


def test_password_hashing_does_not_store_plain_password() -> None:
    service = PasswordService()
    password = "StrongPass123!"

    password_hash = service.hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2id$")


def test_correct_password_verification() -> None:
    service = PasswordService()
    password = "StrongPass123!"
    password_hash = service.hash_password(password)

    assert service.verify_password(password, password_hash) is True


def test_wrong_password_rejection() -> None:
    service = PasswordService()
    password_hash = service.hash_password("StrongPass123!")

    assert service.verify_password("WrongPass123!", password_hash) is False


def test_password_hash_is_what_gets_stored_in_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)

    service = PasswordService()
    repository = OwnerAccountRepository(database_path)
    plain_password = "StrongPass123!"
    password_hash = service.hash_password(plain_password)

    saved_record = repository.save(
        OwnerAccountRecord(
            id=None,
            email="owner@example.com",
            password_hash=password_hash,
            password_policy_version=1,
            riff_2fa_enabled=False,
            created_at="2026-06-22T00:00:00Z",
            updated_at="2026-06-22T00:00:00Z",
        )
    )

    stored_record = repository.get_by_id(saved_record.id)

    assert stored_record is not None
    assert stored_record.password_hash != plain_password
    assert stored_record.password_hash == password_hash
    assert service.verify_password(plain_password, stored_record.password_hash) is True
    assert len(plain_password) >= MIN_PASSWORD_LENGTH
