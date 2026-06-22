from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
from rifflock.storage import (
    AuthAttemptRepository,
    KeyVaultRepository,
    OwnerAccountRepository,
    initialize_database,
)
from rifflock.utils.errors import AuthenticationError


def test_failed_attempt_counting(tmp_path: Path) -> None:
    _, lockout_service, _, _, _ = _build_login_components(tmp_path)

    status = lockout_service.record_failed_password_attempt("owner@example.com")
    assert status.failed_attempt_count == 1
    status = lockout_service.record_failed_password_attempt("owner@example.com")
    assert status.failed_attempt_count == 2


def test_failed_riff_attempt_counting(tmp_path: Path) -> None:
    _, lockout_service, _, _, _ = _build_login_components(tmp_path)

    status = lockout_service.record_failed_riff_attempt("owner@example.com")
    assert status.failed_attempt_count == 1
    status = lockout_service.record_failed_riff_attempt("owner@example.com")
    assert status.failed_attempt_count == 2


def test_lockout_triggers_after_threshold(tmp_path: Path) -> None:
    _, lockout_service, _, _, _ = _build_login_components(tmp_path)

    lockout_service.record_failed_password_attempt("owner@example.com")
    lockout_service.record_failed_password_attempt("owner@example.com")
    status = lockout_service.record_failed_password_attempt("owner@example.com")

    assert status.is_locked is True
    assert status.failed_attempt_count == 3
    assert status.locked_until is not None


def test_riff_lockout_triggers_after_threshold(tmp_path: Path) -> None:
    _, lockout_service, _, _, _ = _build_login_components(tmp_path)

    lockout_service.record_failed_riff_attempt("owner@example.com")
    lockout_service.record_failed_riff_attempt("owner@example.com")
    status = lockout_service.record_failed_riff_attempt("owner@example.com")

    assert status.is_locked is True
    assert status.failed_attempt_count == 3
    assert status.locked_until is not None


def test_lockout_expires_after_duration(tmp_path: Path) -> None:
    base_time = datetime(2026, 6, 22, 0, 0, 0, tzinfo=UTC)
    current_time = {"value": base_time}

    def clock():
        return current_time["value"]

    _, lockout_service, auth_attempt_repository, _, _ = _build_login_components(
        tmp_path,
        clock=clock,
    )

    lockout_service.record_failed_password_attempt("owner@example.com")
    lockout_service.record_failed_password_attempt("owner@example.com")
    lockout_service.record_failed_password_attempt("owner@example.com")

    current_time["value"] = base_time + timedelta(seconds=61)
    status = lockout_service.get_password_lockout_status("owner@example.com")

    assert status.is_locked is False
    assert status.failed_attempt_count == 0
    assert auth_attempt_repository.list_by_identifier_and_type("owner@example.com", "password") == []


def test_riff_lockout_expires_after_duration(tmp_path: Path) -> None:
    base_time = datetime(2026, 6, 22, 0, 0, 0, tzinfo=UTC)
    current_time = {"value": base_time}

    def clock():
        return current_time["value"]

    _, lockout_service, auth_attempt_repository, _, _ = _build_login_components(
        tmp_path,
        clock=clock,
    )

    lockout_service.record_failed_riff_attempt("owner@example.com")
    lockout_service.record_failed_riff_attempt("owner@example.com")
    lockout_service.record_failed_riff_attempt("owner@example.com")

    current_time["value"] = base_time + timedelta(seconds=61)
    status = lockout_service.get_riff_lockout_status("owner@example.com")

    assert status.is_locked is False
    assert status.failed_attempt_count == 0
    assert auth_attempt_repository.list_by_identifier_and_type("owner@example.com", "riff") == []


def test_failed_attempts_reset_after_successful_login(tmp_path: Path) -> None:
    login_service, lockout_service, auth_attempt_repository, _, _ = _build_login_components(tmp_path)

    lockout_service.record_failed_password_attempt("owner@example.com")
    lockout_service.record_failed_password_attempt("owner@example.com")
    result = login_service.login("owner@example.com", "StrongPass123!")

    assert result.next_screen == "dashboard"
    assert auth_attempt_repository.list_by_identifier_and_type("owner@example.com", "password") == []


def test_correct_password_is_blocked_during_active_lockout(tmp_path: Path) -> None:
    login_service, lockout_service, _, _, _ = _build_login_components(tmp_path)

    lockout_service.record_failed_password_attempt("owner@example.com")
    lockout_service.record_failed_password_attempt("owner@example.com")
    lockout_service.record_failed_password_attempt("owner@example.com")

    with pytest.raises(AuthenticationError) as error:
        login_service.login("owner@example.com", "StrongPass123!")

    assert error.value.user_message == GENERIC_LOGIN_ERROR


def _build_login_components(tmp_path: Path, clock=None):
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)
    owner_repository = OwnerAccountRepository(database_path)
    key_vault_repository = KeyVaultRepository(database_path)
    auth_attempt_repository = AuthAttemptRepository(database_path)
    owner_setup_service = OwnerSetupService(owner_repository, key_vault_repository)
    owner_setup_service.create_owner_account(
        OwnerSetupRequest(
            email="owner@example.com",
            password="StrongPass123!",
            password_confirmation="StrongPass123!",
            password_loss_acknowledged=True,
        )
    )
    lockout_service = LockoutService(
        auth_attempt_repository=auth_attempt_repository,
        lockout_settings=LockoutSettings(),
        clock=clock,
    )
    session_service = SessionService()
    login_service = LoginService(
        owner_repository=owner_repository,
        key_vault_repository=key_vault_repository,
        auth_attempt_repository=auth_attempt_repository,
        session_service=session_service,
        lockout_service=lockout_service,
    )
    return (
        login_service,
        lockout_service,
        auth_attempt_repository,
        session_service,
        owner_setup_service,
    )
