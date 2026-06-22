"""First-time owner account setup service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from logging import Logger

from rifflock.auth.passwords import PasswordService
from rifflock.crypto import KeyVaultService
from rifflock.models import OwnerAccountRecord
from rifflock.storage import KeyVaultRepository, OwnerAccountRepository
from rifflock.utils.errors import AuthenticationError, StorageError, ValidationError


@dataclass(frozen=True)
class OwnerSetupRequest:
    email: str
    password: str
    password_confirmation: str
    password_loss_acknowledged: bool


@dataclass(frozen=True)
class OwnerSetupResult:
    owner_account: OwnerAccountRecord
    next_screen: str


class OwnerSetupService:
    """Create the single local owner account and initial key vault."""

    def __init__(
        self,
        owner_repository: OwnerAccountRepository,
        key_vault_repository: KeyVaultRepository,
        password_service: PasswordService | None = None,
        key_vault_service: KeyVaultService | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._owner_repository = owner_repository
        self._key_vault_repository = key_vault_repository
        self._password_service = password_service or PasswordService()
        self._key_vault_service = key_vault_service or KeyVaultService(key_vault_repository)
        self._logger = logger

    def should_show_setup(self) -> bool:
        return not self._owner_repository.has_owner_account()

    def create_owner_account(self, request: OwnerSetupRequest) -> OwnerSetupResult:
        if not self.should_show_setup():
            raise ValidationError("Owner account setup is not available.")

        normalized_email = self._password_service.validate_email(request.email)
        self._validate_request(request)
        password_hash = self._password_service.hash_password(request.password)
        timestamp = _utc_now()

        owner_record = self._owner_repository.save(
            OwnerAccountRecord(
                id=None,
                email=normalized_email,
                password_hash=password_hash,
                password_policy_version=1,
                riff_2fa_enabled=False,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )

        try:
            self._key_vault_service.store_new_key_vault(owner_record.id, request.password)
        except Exception as error:
            self._owner_repository.delete(owner_record.id)
            if isinstance(error, AuthenticationError):
                raise
            raise StorageError(
                "Unable to finish account setup.",
                log_message="Owner account setup failed while creating the key vault.",
                security_sensitive=True,
            ) from error

        if self._logger is not None:
            self._logger.info(
                "Owner account setup completed for email=%s",
                normalized_email,
            )

        return OwnerSetupResult(owner_account=owner_record, next_screen="dashboard")

    def _validate_request(self, request: OwnerSetupRequest) -> None:
        self._password_service.validate_password_strength(request.password)
        if request.password != request.password_confirmation:
            raise ValidationError("Password confirmation does not match.")
        if not request.password_loss_acknowledged:
            raise ValidationError("You must acknowledge the password-loss warning.")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
