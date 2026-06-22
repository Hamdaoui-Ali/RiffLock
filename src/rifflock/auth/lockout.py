"""Failed-attempt tracking and temporary lockout services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from logging import Logger

from rifflock.config import LockoutSettings
from rifflock.models import AuthAttemptRecord
from rifflock.storage import AuthAttemptRepository


@dataclass(frozen=True)
class LockoutStatus:
    is_locked: bool
    failed_attempt_count: int
    locked_until: datetime | None


class LockoutService:
    """Track password failures and enforce temporary lockout."""

    def __init__(
        self,
        auth_attempt_repository: AuthAttemptRepository,
        lockout_settings: LockoutSettings,
        logger: Logger | None = None,
        clock=None,
    ) -> None:
        self._auth_attempt_repository = auth_attempt_repository
        self._lockout_settings = lockout_settings
        self._logger = logger
        self._clock = clock or _utc_now

    def get_password_lockout_status(self, identifier: str) -> LockoutStatus:
        return self._get_lockout_status(
            identifier=identifier,
            attempt_type="password",
            attempt_limit=self._lockout_settings.password_attempt_limit,
            reset_callback=self.reset_password_failures,
        )

    def get_riff_lockout_status(self, identifier: str) -> LockoutStatus:
        return self._get_lockout_status(
            identifier=identifier,
            attempt_type="riff",
            attempt_limit=self._lockout_settings.riff_attempt_limit,
            reset_callback=self.reset_riff_failures,
        )

    def record_failed_password_attempt(self, identifier: str) -> LockoutStatus:
        status = self._record_failed_attempt(
            identifier=identifier,
            attempt_type="password",
            failure_reason="invalid_credentials",
        )
        if self._logger is not None:
            self._logger.warning(
                "Password login failure recorded for identifier=%s failed_attempts=%s locked=%s",
                identifier,
                status.failed_attempt_count,
                status.is_locked,
            )
        return status

    def record_failed_riff_attempt(self, identifier: str) -> LockoutStatus:
        status = self._record_failed_attempt(
            identifier=identifier,
            attempt_type="riff",
            failure_reason="invalid_riff",
        )
        if self._logger is not None:
            self._logger.warning(
                "Riff verification failure recorded for identifier=%s failed_attempts=%s locked=%s",
                identifier,
                status.failed_attempt_count,
                status.is_locked,
            )
        return status

    def reset_password_failures(self, identifier: str) -> None:
        self._reset_failures(identifier=identifier, attempt_type="password")
        if self._logger is not None:
            self._logger.info(
                "Password failure history reset for identifier=%s",
                identifier,
            )

    def reset_riff_failures(self, identifier: str) -> None:
        self._reset_failures(identifier=identifier, attempt_type="riff")
        if self._logger is not None:
            self._logger.info(
                "Riff failure history reset for identifier=%s",
                identifier,
            )

    def _get_lockout_status(
        self,
        *,
        identifier: str,
        attempt_type: str,
        attempt_limit: int,
        reset_callback,
    ) -> LockoutStatus:
        attempts = self._auth_attempt_repository.list_by_identifier_and_type(
            identifier=identifier,
            attempt_type=attempt_type,
        )
        failures = [attempt for attempt in attempts if not attempt.was_successful]
        failure_count = len(failures)

        if failure_count < attempt_limit:
            return LockoutStatus(
                is_locked=False,
                failed_attempt_count=failure_count,
                locked_until=None,
            )

        latest_failure = max(_parse_utc(attempt.attempted_at) for attempt in failures)
        locked_until = latest_failure + timedelta(
            seconds=self._lockout_settings.duration_seconds
        )

        if self._clock() >= locked_until:
            reset_callback(identifier)
            return LockoutStatus(
                is_locked=False,
                failed_attempt_count=0,
                locked_until=None,
            )

        return LockoutStatus(
            is_locked=True,
            failed_attempt_count=failure_count,
            locked_until=locked_until,
        )

    def _record_failed_attempt(
        self,
        *,
        identifier: str,
        attempt_type: str,
        failure_reason: str,
    ) -> LockoutStatus:
        self._auth_attempt_repository.save(
            AuthAttemptRecord(
                id=None,
                attempt_type=attempt_type,
                identifier=identifier,
                was_successful=False,
                failure_reason=failure_reason,
                attempted_at=_to_timestamp(self._clock()),
            )
        )
        if attempt_type == "password":
            return self.get_password_lockout_status(identifier)
        return self.get_riff_lockout_status(identifier)

    def _reset_failures(self, *, identifier: str, attempt_type: str) -> None:
        self._auth_attempt_repository.delete_by_identifier_and_type(
            identifier=identifier,
            attempt_type=attempt_type,
        )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _to_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
