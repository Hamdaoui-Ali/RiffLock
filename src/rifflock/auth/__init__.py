"""Authentication domain package."""

from rifflock.auth.passwords import MIN_PASSWORD_LENGTH, PasswordService
from rifflock.auth.login import (
    AuthenticatedSession,
    GENERIC_LOGIN_ERROR,
    LoginResult,
    LoginService,
    PendingRiffVerification,
    SessionService,
)
from rifflock.auth.lockout import LockoutService, LockoutStatus
from rifflock.auth.setup import OwnerSetupRequest, OwnerSetupResult, OwnerSetupService

__all__ = [
    "AuthenticatedSession",
    "GENERIC_LOGIN_ERROR",
    "LockoutService",
    "LockoutStatus",
    "LoginResult",
    "LoginService",
    "MIN_PASSWORD_LENGTH",
    "OwnerSetupRequest",
    "OwnerSetupResult",
    "OwnerSetupService",
    "PendingRiffVerification",
    "PasswordService",
    "SessionService",
]
