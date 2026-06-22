from __future__ import annotations

from pathlib import Path

import pytest

from rifflock.auth import OwnerSetupRequest, OwnerSetupService
from rifflock.storage import KeyVaultRepository, OwnerAccountRepository, initialize_database
from rifflock.ui.routes import determine_initial_route
from rifflock.utils import configure_file_logger
from rifflock.utils.errors import ValidationError


def test_setup_validation_rules(tmp_path: Path) -> None:
    service = _build_setup_service(tmp_path)

    with pytest.raises(ValidationError):
        service.create_owner_account(
            OwnerSetupRequest(
                email="invalid-email",
                password="StrongPass123!",
                password_confirmation="StrongPass123!",
                password_loss_acknowledged=True,
            )
        )

    with pytest.raises(ValidationError):
        service.create_owner_account(
            OwnerSetupRequest(
                email="owner@example.com",
                password="weak",
                password_confirmation="weak",
                password_loss_acknowledged=True,
            )
        )

    with pytest.raises(ValidationError):
        service.create_owner_account(
            OwnerSetupRequest(
                email="owner@example.com",
                password="StrongPass123!",
                password_confirmation="StrongPass123!diff",
                password_loss_acknowledged=True,
            )
        )

    with pytest.raises(ValidationError):
        service.create_owner_account(
            OwnerSetupRequest(
                email="owner@example.com",
                password="StrongPass123!",
                password_confirmation="StrongPass123!",
                password_loss_acknowledged=False,
            )
        )


def test_account_creation_is_saved_in_sqlite_and_routes_to_dashboard(tmp_path: Path) -> None:
    service = _build_setup_service(tmp_path)

    result = service.create_owner_account(
        OwnerSetupRequest(
            email="Owner@example.com",
            password="StrongPass123!",
            password_confirmation="StrongPass123!",
            password_loss_acknowledged=True,
        )
    )

    owner_repository = OwnerAccountRepository(_database_path(tmp_path))
    stored_owner = owner_repository.get_owner_account()

    assert stored_owner is not None
    assert stored_owner.email == "owner@example.com"
    assert stored_owner.password_hash != "StrongPass123!"
    assert stored_owner.riff_2fa_enabled is False
    assert result.next_screen == "dashboard"


def test_key_vault_is_created_during_owner_setup(tmp_path: Path) -> None:
    service = _build_setup_service(tmp_path)

    result = service.create_owner_account(
        OwnerSetupRequest(
            email="owner@example.com",
            password="StrongPass123!",
            password_confirmation="StrongPass123!",
            password_loss_acknowledged=True,
        )
    )

    key_vault_repository = KeyVaultRepository(_database_path(tmp_path))
    stored_vault = key_vault_repository.get_by_owner_account_id(result.owner_account.id)

    assert stored_vault is not None
    assert stored_vault.ciphertext
    assert stored_vault.owner_account_id == result.owner_account.id


def test_setup_does_not_log_password(tmp_path: Path) -> None:
    database_path = _database_path(tmp_path)
    initialize_database(database_path)
    logs_dir = tmp_path / "logs"
    logger = configure_file_logger(
        logs_dir,
        _logging_settings(),
        logger_name="rifflock.tests.owner_setup",
    )

    service = OwnerSetupService(
        owner_repository=OwnerAccountRepository(database_path),
        key_vault_repository=KeyVaultRepository(database_path),
        logger=logger,
    )

    service.create_owner_account(
        OwnerSetupRequest(
            email="owner@example.com",
            password="StrongPass123!",
            password_confirmation="StrongPass123!",
            password_loss_acknowledged=True,
        )
    )

    log_contents = (logs_dir / "owner-setup.log").read_text(encoding="utf-8")
    assert "StrongPass123!" not in log_contents
    assert "owner@example.com" in log_contents


def test_setup_screen_only_shows_when_owner_is_missing(tmp_path: Path) -> None:
    service = _build_setup_service(tmp_path)

    assert service.should_show_setup() is True
    assert determine_initial_route(service).name == "setup"

    service.create_owner_account(
        OwnerSetupRequest(
            email="owner@example.com",
            password="StrongPass123!",
            password_confirmation="StrongPass123!",
            password_loss_acknowledged=True,
        )
    )

    assert service.should_show_setup() is False
    assert determine_initial_route(service).name == "login"


def _build_setup_service(tmp_path: Path) -> OwnerSetupService:
    database_path = _database_path(tmp_path)
    initialize_database(database_path)
    return OwnerSetupService(
        owner_repository=OwnerAccountRepository(database_path),
        key_vault_repository=KeyVaultRepository(database_path),
    )


def _database_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "rifflock.db"


def _logging_settings():
    from rifflock.config import LoggingSettings

    return LoggingSettings(file_name="owner-setup.log", max_bytes=4096, backup_count=1)
