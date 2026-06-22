"""Password validation and hashing services."""

from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from rifflock.utils.errors import AuthenticationError, ValidationError

EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.IGNORECASE)

MIN_PASSWORD_LENGTH = 12


class PasswordService:
    """Isolated service for email and password validation."""

    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def validate_email(self, email: str) -> str:
        normalized_email = email.strip().lower()
        if not normalized_email or not EMAIL_PATTERN.fullmatch(normalized_email):
            raise ValidationError("Enter a valid email address.")
        return normalized_email

    def validate_password_strength(self, password: str) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValidationError(
                "Password must be at least 12 characters and include upper, lower, digit, and symbol characters."
            )
        if password.lower() == password:
            raise ValidationError(
                "Password must be at least 12 characters and include upper, lower, digit, and symbol characters."
            )
        if password.upper() == password:
            raise ValidationError(
                "Password must be at least 12 characters and include upper, lower, digit, and symbol characters."
            )
        if not any(character.isdigit() for character in password):
            raise ValidationError(
                "Password must be at least 12 characters and include upper, lower, digit, and symbol characters."
            )
        if password.isalnum():
            raise ValidationError(
                "Password must be at least 12 characters and include upper, lower, digit, and symbol characters."
            )

    def hash_password(self, password: str) -> str:
        self.validate_password_strength(password)
        return self._hasher.hash(password)

    def verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            return self._hasher.verify(stored_hash, password)
        except VerifyMismatchError:
            return False
        except (InvalidHashError, VerificationError) as error:
            raise AuthenticationError(
                "Unable to verify credentials.",
                log_message=f"Password verification failed due to invalid stored hash: {type(error).__name__}",
                security_sensitive=True,
            ) from error
