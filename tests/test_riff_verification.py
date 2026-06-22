from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from rifflock.audio import (
    RiffComparisonResult,
    RiffFeatureTemplate,
    RiffEnrollmentService,
)
from rifflock.auth import (
    LockoutService,
    LoginService,
    OwnerSetupRequest,
    OwnerSetupService,
    SessionService,
)
from rifflock.auth.login import PendingRiffVerification
from rifflock.auth.riff_verification import (
    GENERIC_RIFF_VERIFICATION_ERROR,
    RiffVerificationService,
)
from rifflock.config import AudioSettings
from rifflock.config import LockoutSettings
from rifflock.models import AuthAttemptRecord
from rifflock.storage import (
    AuthAttemptRepository,
    KeyVaultRepository,
    OwnerAccountRepository,
    RiffTemplateRepository,
    initialize_database,
)
from rifflock.utils.errors import AuthenticationError


def test_dashboard_is_blocked_until_riff_verification_succeeds(tmp_path: Path) -> None:
    login_service, verification_service, session_service, _, _, _ = _build_services(tmp_path, matches=True)

    login_result = login_service.login("owner@example.com", "StrongPass123!")

    assert login_result.next_screen == "riff_verification"
    assert login_result.session is None
    assert session_service.get_session() is None

    session = verification_service.verify(login_result.pending_riff_verification)

    assert session_service.get_session() == session


def test_riff_verification_successful_match_opens_dashboard_session(tmp_path: Path) -> None:
    _, verification_service, session_service, owner_repository, _, _ = _build_services(tmp_path, matches=True)
    owner = owner_repository.get_owner_account()
    assert owner is not None

    session = verification_service.verify(
        _pending_verification(owner.id, owner.email, "StrongPass123!")
    )

    assert session.owner_account_id == owner.id
    assert session.owner_email == owner.email
    assert session.riff_2fa_enabled is True
    assert session_service.get_session() == session


def test_riff_verification_failed_match_is_rejected_generically(tmp_path: Path) -> None:
    _, verification_service, session_service, owner_repository, _, auth_attempt_repository = _build_services(tmp_path, matches=False)
    owner = owner_repository.get_owner_account()
    assert owner is not None

    with pytest.raises(AuthenticationError) as error:
        verification_service.verify(_pending_verification(owner.id, owner.email, "StrongPass123!"))

    assert error.value.user_message == GENERIC_RIFF_VERIFICATION_ERROR
    assert session_service.get_session() is None
    attempts = auth_attempt_repository.list_by_identifier_and_type("owner@example.com", "riff")
    assert len(attempts) == 1
    assert attempts[0].failure_reason == "invalid_riff"


def test_login_with_2fa_enabled_requires_verification_before_session_exists(tmp_path: Path) -> None:
    login_service, _, session_service, _, _, _ = _build_services(tmp_path, matches=True)

    result = login_service.login("owner@example.com", "StrongPass123!")

    assert result.next_screen == "riff_verification"
    assert result.session is None
    assert result.pending_riff_verification is not None
    assert session_service.get_session() is None


def test_correct_riff_is_blocked_during_active_riff_lockout(tmp_path: Path) -> None:
    base_time = datetime(2026, 6, 22, 0, 0, 0, tzinfo=UTC)
    current_time = {"value": base_time}

    def clock():
        return current_time["value"]

    _, verification_service, session_service, owner_repository, _, auth_attempt_repository = _build_services(
        tmp_path,
        matches=True,
        clock=clock,
    )
    owner = owner_repository.get_owner_account()
    assert owner is not None
    lockout_service = LockoutService(
        auth_attempt_repository=auth_attempt_repository,
        lockout_settings=LockoutSettings(),
        clock=clock,
    )
    lockout_service.record_failed_riff_attempt("owner@example.com")
    lockout_service.record_failed_riff_attempt("owner@example.com")
    lockout_service.record_failed_riff_attempt("owner@example.com")

    with pytest.raises(AuthenticationError) as error:
        verification_service.verify(_pending_verification(owner.id, owner.email, "StrongPass123!"))

    assert error.value.user_message == GENERIC_RIFF_VERIFICATION_ERROR
    assert session_service.get_session() is None


def test_riff_failures_reset_after_successful_verification(tmp_path: Path) -> None:
    _, verification_service, session_service, owner_repository, _, auth_attempt_repository = _build_services(tmp_path, matches=True)
    owner = owner_repository.get_owner_account()
    assert owner is not None

    auth_attempt_repository.save(
        AuthAttemptRecord(
            id=None,
            attempt_type="riff",
            identifier="owner@example.com",
            was_successful=False,
            failure_reason="invalid_riff",
            attempted_at="2026-06-22T00:00:00Z",
        )
    )
    auth_attempt_repository.save(
        AuthAttemptRecord(
            id=None,
            attempt_type="riff",
            identifier="owner@example.com",
            was_successful=False,
            failure_reason="invalid_riff",
            attempted_at="2026-06-22T00:00:01Z",
        )
    )

    session = verification_service.verify(_pending_verification(owner.id, owner.email, "StrongPass123!"))

    assert session_service.get_session() == session
    assert auth_attempt_repository.list_by_identifier_and_type("owner@example.com", "riff") == []


class _FakeRecordingService:
    def record(self):
        from rifflock.audio.recording import AudioRecording

        return AudioRecording(
            samples=np.array([0.5, 0.4, 0.3], dtype=np.float32),
            sample_rate=22050,
            duration_seconds=1,
        )


class _FakeFeatureExtractionService:
    def __init__(self, template: RiffFeatureTemplate) -> None:
        self._template = template

    def extract(self, samples, sample_rate):
        return self._template


class _FakeSimilarityService:
    def __init__(self, *, matches: bool, threshold: float) -> None:
        self._matches = matches
        self._threshold = threshold

    def compare(self, stored_template, candidate_template):
        return RiffComparisonResult(
            score=0.95 if self._matches else 0.20,
            passed=self._matches,
            threshold=self._threshold,
        )


def _build_services(tmp_path: Path, *, matches: bool, clock=None):
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)
    owner_repository = OwnerAccountRepository(database_path)
    key_vault_repository = KeyVaultRepository(database_path)
    riff_template_repository = RiffTemplateRepository(database_path)
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
    owner_repository.save(
        replace(
            setup_result.owner_account,
            riff_2fa_enabled=True,
            updated_at="2026-06-22T00:10:00Z",
        )
    )
    enrollment_service = RiffEnrollmentService(
        owner_repository=owner_repository,
        riff_template_repository=riff_template_repository,
        recording_service=_FakeRecordingService(),
        feature_extraction_service=_FakeFeatureExtractionService(
            _template([1.0, 2.0, 3.0, 4.0])
        ),
    )
    enrollment_service.enroll(setup_result.owner_account.id, "StrongPass123!")

    session_service = SessionService()
    lockout_service = LockoutService(
        auth_attempt_repository=auth_attempt_repository,
        lockout_settings=LockoutSettings(),
        clock=clock,
    )
    login_service = LoginService(
        owner_repository=owner_repository,
        key_vault_repository=key_vault_repository,
        session_service=session_service,
    )
    verification_service = RiffVerificationService(
        owner_repository=owner_repository,
        key_vault_repository=key_vault_repository,
        riff_template_repository=riff_template_repository,
        recording_service=_FakeRecordingService(),
        feature_extraction_service=_FakeFeatureExtractionService(
            _template([1.0, 2.0, 3.0, 4.0]) if matches else _template([9.0, 8.0, 7.0, 6.0])
        ),
        similarity_service=_FakeSimilarityService(
            matches=matches,
            threshold=AudioSettings().similarity_threshold,
        ),
        session_service=session_service,
        lockout_service=lockout_service,
    )
    return (
        login_service,
        verification_service,
        session_service,
        owner_repository,
        riff_template_repository,
        auth_attempt_repository,
    )


def _template(values: list[float]) -> RiffFeatureTemplate:
    return RiffFeatureTemplate(
        vector=np.asarray(values, dtype=np.float32),
        sample_rate=22050,
    )


def _pending_verification(owner_account_id: int, owner_email: str, password: str):
    return PendingRiffVerification(
        owner_account_id=owner_account_id,
        owner_email=owner_email,
        password=password,
    )
