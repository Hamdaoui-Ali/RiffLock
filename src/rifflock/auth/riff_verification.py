"""Riff verification flow that completes login for 2FA-enabled owners."""

from __future__ import annotations

from logging import Logger

from rifflock.audio.compare import RiffSimilarityService
from rifflock.audio.enrollment import deserialize_riff_template
from rifflock.audio.features import RiffFeatureExtractionService
from rifflock.audio.recording import MicrophoneRecordingService
from rifflock.auth.lockout import LockoutService
from rifflock.auth.login import (
    AuthenticatedSession,
    PendingRiffVerification,
    SessionService,
)
from rifflock.crypto import KeyVaultService
from rifflock.models import RiffTemplateRecord
from rifflock.storage import KeyVaultRepository, OwnerAccountRepository, RiffTemplateRepository
from rifflock.utils.errors import AuthenticationError

GENERIC_RIFF_VERIFICATION_ERROR = "Riff verification failed."


class RiffVerificationService:
    """Verify a recorded riff and create the authenticated session on success."""

    def __init__(
        self,
        owner_repository: OwnerAccountRepository,
        key_vault_repository: KeyVaultRepository,
        riff_template_repository: RiffTemplateRepository,
        recording_service: MicrophoneRecordingService,
        feature_extraction_service: RiffFeatureExtractionService,
        similarity_service: RiffSimilarityService,
        session_service: SessionService,
        *,
        lockout_service: LockoutService | None = None,
        key_vault_service: KeyVaultService | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._owner_repository = owner_repository
        self._key_vault_repository = key_vault_repository
        self._riff_template_repository = riff_template_repository
        self._recording_service = recording_service
        self._feature_extraction_service = feature_extraction_service
        self._similarity_service = similarity_service
        self._session_service = session_service
        self._lockout_service = lockout_service
        self._key_vault_service = key_vault_service or KeyVaultService(key_vault_repository)
        self._logger = logger

    def verify(self, pending_verification: PendingRiffVerification) -> AuthenticatedSession:
        self._ensure_not_locked_out(pending_verification.owner_email)
        owner_account = self._owner_repository.get_by_id(pending_verification.owner_account_id)
        if owner_account is None or not owner_account.riff_2fa_enabled:
            raise self._reject_verification("Riff verification rejected because owner account is unavailable.")

        stored_template_record = self._riff_template_repository.get_by_owner_account_id(owner_account.id)
        stored_template = self._load_template(stored_template_record)

        recording = self._recording_service.record()
        candidate_template = self._feature_extraction_service.extract(
            recording.samples,
            recording.sample_rate,
        )
        comparison = self._similarity_service.compare(stored_template, candidate_template)
        if not comparison.passed:
            self._record_failed_attempt(pending_verification.owner_email)
            raise self._reject_verification("Riff verification rejected because similarity score was below threshold.")

        key_vault_record = self._key_vault_repository.get_by_owner_account_id(owner_account.id)
        if key_vault_record is None:
            raise self._reject_verification("Riff verification rejected because key vault record is missing.")

        try:
            unlocked_data_key = self._key_vault_service.unlock_data_key(
                pending_verification.password,
                key_vault_record,
            )
        except AuthenticationError as error:
            raise self._reject_verification(
                "Riff verification rejected because data key unlock failed.",
            ) from error

        session = self._session_service.create_session(owner_account, unlocked_data_key)
        if self._lockout_service is not None:
            self._lockout_service.reset_riff_failures(pending_verification.owner_email)
        if self._logger is not None:
            self._logger.info(
                "Riff verification succeeded for owner_account_id=%s",
                owner_account.id,
            )
        return session

    def _ensure_not_locked_out(self, identifier: str) -> None:
        if self._lockout_service is None:
            return
        status = self._lockout_service.get_riff_lockout_status(identifier)
        if status.is_locked:
            if self._logger is not None:
                self._logger.warning(
                    "Riff verification blocked by active lockout for identifier=%s",
                    identifier,
                )
            raise self._reject_verification(
                "Riff verification rejected because the identifier is under active lockout.",
            )

    def _record_failed_attempt(self, identifier: str) -> None:
        if self._lockout_service is None:
            return
        self._lockout_service.record_failed_riff_attempt(identifier)

    def _load_template(self, record: RiffTemplateRecord | None):
        if record is None:
            raise self._reject_verification("Riff verification rejected because stored template is missing.")
        try:
            return deserialize_riff_template(record.template_data)
        except Exception as error:
            raise self._reject_verification(
                "Riff verification rejected because stored template could not be loaded.",
            ) from error

    def _reject_verification(self, log_message: str) -> AuthenticationError:
        return AuthenticationError(
            GENERIC_RIFF_VERIFICATION_ERROR,
            log_message=log_message,
            security_sensitive=True,
        )
