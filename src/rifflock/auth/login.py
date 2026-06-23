"""Owner login and session management services."""

from __future__ import annotations

from dataclasses import dataclass, field
from logging import Logger

from rifflock.auth.lockout import LockoutService
from rifflock.auth.passwords import PasswordService
from rifflock.crypto import KeyVaultService
from rifflock.models import KeyVaultRecord, OwnerAccountRecord
from rifflock.storage import (
    AuthAttemptRepository,
    KeyVaultRepository,
    OwnerAccountRepository,
)
from rifflock.utils.errors import AuthenticationError

GENERIC_LOGIN_ERROR = "Invalid credentials."


@dataclass(frozen=True)
class AuthenticatedSession:
    owner_account_id: int
    owner_email: str
    unlocked_data_key: bytes
    riff_2fa_enabled: bool


@dataclass(frozen=True)
class PendingRiffVerification:
    owner_account_id: int
    owner_email: str
    password: str = field(repr=False)


@dataclass(frozen=True)
class LoginResult:
    session: AuthenticatedSession | None
    next_screen: str
    pending_riff_verification: PendingRiffVerification | None = None


class SessionService:
    """Manage the in-memory authenticated session."""

    def __init__(self) -> None:
        self._session: AuthenticatedSession | None = None

    def create_session(
        self,
        owner_account: OwnerAccountRecord,
        unlocked_data_key: bytes,
    ) -> AuthenticatedSession:
        session = AuthenticatedSession(
            owner_account_id=owner_account.id,
            owner_email=owner_account.email,
            unlocked_data_key=unlocked_data_key,
            riff_2fa_enabled=owner_account.riff_2fa_enabled,
        )
        self._session = session
        return session

    def get_session(self) -> AuthenticatedSession | None:
        return self._session

    def clear_session(self) -> None:
        self._session = None


class LoginService:
    """Validate owner credentials and start the authenticated login flow."""

    def __init__(
        self,
        owner_repository: OwnerAccountRepository,
        key_vault_repository: KeyVaultRepository,
        session_service: SessionService,
        auth_attempt_repository: AuthAttemptRepository | None = None,
        lockout_service: LockoutService | None = None,
        password_service: PasswordService | None = None,
        key_vault_service: KeyVaultService | None = None,
        logger: Logger | None = None,
        lockout_settings=None,
    ) -> None:
        self._owner_repository = owner_repository
        self._key_vault_repository = key_vault_repository
        self._session_service = session_service
        self._password_service = password_service or PasswordService()
        self._key_vault_service = key_vault_service or KeyVaultService(key_vault_repository)
        self._logger = logger
        self._auth_attempt_repository = auth_attempt_repository
        if lockout_service is not None:
            self._lockout_service = lockout_service
        elif auth_attempt_repository is not None and lockout_settings is not None:
            self._lockout_service = LockoutService(
                auth_attempt_repository=auth_attempt_repository,
                lockout_settings=lockout_settings,
                logger=logger,
            )
        else:
            self._lockout_service = None

    def login(self, email: str, password: str) -> LoginResult:
        normalized_email = email.strip().lower()
        self._ensure_not_locked_out(normalized_email)
        owner_account = self._owner_repository.get_by_email(normalized_email)

        if owner_account is None:
            self._handle_failed_login(normalized_email)

        is_valid_password = self._password_service.verify_password(
            password,
            owner_account.password_hash,
        )
        if not is_valid_password:
            self._handle_failed_login(normalized_email)

        if self._lockout_service is not None:
            self._lockout_service.reset_password_failures(normalized_email)

        if owner_account.riff_2fa_enabled:
            result = LoginResult(
                session=None,
                next_screen="riff_verification",
                pending_riff_verification=PendingRiffVerification(
                    owner_account_id=owner_account.id,
                    owner_email=owner_account.email,
                    password=password,
                ),
            )
        else:
            key_vault_record = self._key_vault_repository.get_by_owner_account_id(owner_account.id)
            if key_vault_record is None:
                raise AuthenticationError(
                    GENERIC_LOGIN_ERROR,
                    log_message="Login rejected because key vault record is missing.",
                    security_sensitive=True,
                )
            unlocked_data_key = self._unlock_data_key(password, key_vault_record)
            session = self._session_service.create_session(owner_account, unlocked_data_key)
            result = LoginResult(
                session=session,
                next_screen="dashboard",
            )

        if self._logger is not None:
            self._logger.info(
                "Owner login succeeded for email=%s next_screen=%s",
                owner_account.email,
                result.next_screen,
            )

        return result

    def logout(self) -> None:
        self._session_service.clear_session()
        if self._logger is not None:
            self._logger.info("Owner session cleared on logout.")

    def reset_failed_attempts(self, email: str) -> None:
        if self._lockout_service is None:
            return
        normalized_email = email.strip().lower()
        if not normalized_email:
            return
        self._lockout_service.reset_password_failures(normalized_email)
        if self._logger is not None:
            self._logger.info(
                "Password login attempts reset from login screen for identifier=%s",
                normalized_email,
            )

    def _unlock_data_key(self, password: str, key_vault_record: KeyVaultRecord) -> bytes:
        try:
            return self._key_vault_service.unlock_data_key(password, key_vault_record)
        except AuthenticationError as error:
            raise AuthenticationError(
                GENERIC_LOGIN_ERROR,
                log_message="Login rejected because data key unlock failed.",
                security_sensitive=True,
            ) from error

    def _handle_failed_login(self, identifier: str) -> None:
        if self._lockout_service is not None:
            self._lockout_service.record_failed_password_attempt(identifier)
        self._reject_login()

    def _ensure_not_locked_out(self, identifier: str) -> None:
        if self._lockout_service is None:
            return
        status = self._lockout_service.get_password_lockout_status(identifier)
        if status.is_locked:
            if self._logger is not None:
                self._logger.warning(
                    "Password login blocked by active lockout for identifier=%s",
                    identifier,
                )
            self._reject_login()

    def _reject_login(self) -> None:
        raise AuthenticationError(
            GENERIC_LOGIN_ERROR,
            log_message="Login rejected due to invalid credentials.",
            security_sensitive=True,
        )
