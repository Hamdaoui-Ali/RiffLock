"""Utility package."""

from rifflock.utils.errors import (
    AudioProcessingError,
    AuthenticationError,
    CryptoOperationError,
    FileOperationError,
    RiffLockError,
    StorageError,
    ValidationError,
    to_user_message,
)
from rifflock.utils.logging import configure_file_logger, log_exception, sanitize_text, sanitize_value

__all__ = [
    "AudioProcessingError",
    "AuthenticationError",
    "CryptoOperationError",
    "FileOperationError",
    "RiffLockError",
    "StorageError",
    "ValidationError",
    "configure_file_logger",
    "log_exception",
    "sanitize_text",
    "sanitize_value",
    "to_user_message",
]
