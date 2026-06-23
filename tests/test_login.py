from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from rifflock.auth import (
    GENERIC_LOGIN_ERROR,
    LockoutService,
    LoginService,
    OwnerSetupRequest,
    OwnerSetupService,
    SessionService,
)
from rifflock.config import LockoutSettings
from rifflock.storage import KeyVaultRepository, OwnerAccountRepository, initialize_database
from rifflock.storage import AuthAttemptRepository
from rifflock.ui.routes import determine_initial_route
from rifflock.utils.errors import AuthenticationError


def test_session_creation() -> None:
    session_service = SessionService()
    session = session_service.create_session(
        owner_account=_owner_record(),
        unlocked_data_key=b"x" * 32,
    )

    assert session.owner_account_id == 1
    assert session.owner_email == "owner@example.com"
    assert session.unlocked_data_key == b"x" * 32
    assert session_service.get_session() == session


def test_logout_clears_session() -> None:
    session_service = SessionService()
    session_service.create_session(_owner_record(), b"x" * 32)

    session_service.clear_session()

    assert session_service.get_session() is None


def test_login_with_sqlite_account_creates_session(tmp_path: Path) -> None:
    login_service, _, _ = _build_login_service_with_owner(tmp_path)

    result = login_service.login("owner@example.com", "StrongPass123!")

    assert result.session is not None
    assert result.session.owner_account_id is not None
    assert result.session.owner_email == "owner@example.com"
    assert result.next_screen == "dashboard"


def test_login_unlocks_data_key_after_authentication(tmp_path: Path) -> None:
    login_service, _, setup_result = _build_login_service_with_owner(tmp_path)

    result = login_service.login("owner@example.com", "StrongPass123!")
    key_vault_record = KeyVaultRepository(_database_path(tmp_path)).get_by_owner_account_id(
        setup_result.owner_account.id
    )

    assert key_vault_record is not None
    assert result.session is not None
    assert result.session.unlocked_data_key != key_vault_record.ciphertext
    assert len(result.session.unlocked_data_key) == 32


def test_failed_login_does_not_reveal_whether_email_or_password_is_wrong(tmp_path: Path) -> None:
    login_service, _, _ = _build_login_service_with_owner(tmp_path)

    with pytest.raises(AuthenticationError) as wrong_email_error:
        login_service.login("missing@example.com", "StrongPass123!")

    with pytest.raises(AuthenticationError) as wrong_password_error:
        login_service.login("owner@example.com", "WrongPass123!")

    assert wrong_email_error.value.user_message == GENERIC_LOGIN_ERROR
    assert wrong_password_error.value.user_message == GENERIC_LOGIN_ERROR


def test_session_is_cleared_on_logout(tmp_path: Path) -> None:
    login_service, session_service, _ = _build_login_service_with_owner(tmp_path)

    login_service.login("owner@example.com", "StrongPass123!")
    assert session_service.get_session() is not None

    login_service.logout()

    assert session_service.get_session() is None


def test_login_route_appears_when_owner_account_exists(tmp_path: Path) -> None:
    database_path = _database_path(tmp_path)
    initialize_database(database_path)
    owner_setup_service = OwnerSetupService(
        owner_repository=OwnerAccountRepository(database_path),
        key_vault_repository=KeyVaultRepository(database_path),
    )
    owner_setup_service.create_owner_account(
        OwnerSetupRequest(
            email="owner@example.com",
            password="StrongPass123!",
            password_confirmation="StrongPass123!",
            password_loss_acknowledged=True,
        )
    )

    assert determine_initial_route(owner_setup_service).name == "login"


def test_riff_2fa_enabled_routes_to_riff_verification(tmp_path: Path) -> None:
    login_service, _, setup_result = _build_login_service_with_owner(tmp_path)
    repository = OwnerAccountRepository(_database_path(tmp_path))
    repository.save(
        replace(
            setup_result.owner_account,
            riff_2fa_enabled=True,
            updated_at="2026-06-22T00:10:00Z",
        )
    )

    result = login_service.login("owner@example.com", "StrongPass123!")

    assert result.next_screen == "riff_verification"
    assert result.session is None
    assert result.pending_riff_verification is not None
    assert result.pending_riff_verification.owner_account_id == setup_result.owner_account.id
    assert result.pending_riff_verification.owner_email == "owner@example.com"


def test_login_reset_failed_attempts_clears_password_lockout_history(tmp_path: Path) -> None:
    database_path = _database_path(tmp_path)
    login_service, _, _ = _build_login_service_with_owner(tmp_path)
    auth_attempt_repository = AuthAttemptRepository(database_path)
    lockout_service = LockoutService(
        auth_attempt_repository=auth_attempt_repository,
        lockout_settings=LockoutSettings(),
    )
    lockout_service.record_failed_password_attempt("owner@example.com")
    lockout_service.record_failed_password_attempt("owner@example.com")
    lockout_service.record_failed_password_attempt("owner@example.com")

    login_service.reset_failed_attempts("owner@example.com")

    assert auth_attempt_repository.list_by_identifier_and_type("owner@example.com", "password") == []
    result = login_service.login("owner@example.com", "StrongPass123!")
    assert result.next_screen == "dashboard"


def _build_login_service_with_owner(tmp_path: Path):
    database_path = _database_path(tmp_path)
    initialize_database(database_path)
    owner_repository = OwnerAccountRepository(database_path)
    key_vault_repository = KeyVaultRepository(database_path)
    auth_attempt_repository = AuthAttemptRepository(database_path)
    owner_setup_service = OwnerSetupService(owner_repository, key_vault_repository)
    setup_result = owner_setup_service.create_owner_account(
        OwnerSetupRequest(
            email="owner@example.com",
            password="StrongPass123!",
            password_confirmation="StrongPass123!",
            password_loss_acknowledged=True,
        )
    )
    session_service = SessionService()
    login_service = LoginService(
        owner_repository=owner_repository,
        key_vault_repository=key_vault_repository,
        session_service=session_service,
        auth_attempt_repository=auth_attempt_repository,
        lockout_settings=LockoutSettings(),
    )
    return login_service, session_service, setup_result


def _database_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "rifflock.db"


def _owner_record():
    from rifflock.models import OwnerAccountRecord

    return OwnerAccountRecord(
        id=1,
        email="owner@example.com",
        password_hash="unused",
        password_policy_version=1,
        riff_2fa_enabled=False,
        created_at="2026-06-22T00:00:00Z",
        updated_at="2026-06-22T00:00:00Z",
    )
