"""User-facing and internal application error types."""

from __future__ import annotations


class RiffLockError(Exception):
    """Base application error with safe UI and logging messages."""

    def __init__(
        self,
        user_message: str,
        *,
        log_message: str | None = None,
        security_sensitive: bool = False,
    ) -> None:
        super().__init__(log_message or user_message)
        self.user_message = user_message
        self.log_message = log_message or user_message
        self.security_sensitive = security_sensitive


class ValidationError(RiffLockError):
    """Input or workflow validation failure."""


class StorageError(RiffLockError):
    """Database or local persistence failure."""


class FileOperationError(RiffLockError):
    """File protection or restore failure."""


class AudioProcessingError(RiffLockError):
    """Audio recording or feature extraction failure."""


class CryptoOperationError(RiffLockError):
    """Sensitive crypto failure that must stay generic in the UI."""


class AuthenticationError(RiffLockError):
    """Authentication failure that must stay generic in the UI."""


def to_user_message(error: Exception) -> str:
    """Convert an exception into a safe UI message."""

    if isinstance(error, RiffLockError):
        if error.security_sensitive:
            return "The operation could not be completed. Please try again."
        return error.user_message

    return "An unexpected error occurred. Please try again."
