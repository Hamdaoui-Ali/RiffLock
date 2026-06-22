"""Safe file logging utilities for RiffLock."""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from rifflock.config import LoggingSettings
from rifflock.utils.errors import RiffLockError

SENSITIVE_KEYS = {
    "audio",
    "ciphertext",
    "file_content",
    "key",
    "nonce",
    "password",
    "password_hash",
    "raw_audio",
    "riff",
    "riff_template",
    "salt",
    "secret",
    "template_data",
    "token",
}

SENSITIVE_PATTERNS = (
    re.compile(
        r"(?i)\b(password|secret|token|key|ciphertext|salt|nonce|riff_template|raw_audio)"
        r"\s*=\s*([^\s,;]+)"
    ),
    re.compile(
        r"(?i)\b(password|secret|token|key|ciphertext|salt|nonce|riff_template|raw_audio|file_content)"
        r"\s*=\s*([^\s,;]+)"
    ),
    re.compile(
        r"(?i)\b(password|secret|token|key|ciphertext|salt|nonce|riff_template|raw_audio|file_content)"
        r"\s*:\s*([^\s,;]+)"
    ),
)


def sanitize_value(value: Any, *, key: str | None = None) -> Any:
    """Mask sensitive values before they are logged."""

    normalized_key = (key or "").lower()
    if normalized_key in SENSITIVE_KEYS:
        return "***"

    if isinstance(value, dict):
        return {item_key: sanitize_value(item_value, key=item_key) for item_key, item_value in value.items()}

    if isinstance(value, (list, tuple, set)):
        sanitized = [sanitize_value(item, key=key) for item in value]
        if isinstance(value, tuple):
            return tuple(sanitized)
        if isinstance(value, set):
            return set(sanitized)
        return sanitized

    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"

    if isinstance(value, str):
        return sanitize_text(value)

    return value


def sanitize_text(text: str) -> str:
    """Mask secret-like key/value pairs in log strings."""

    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(lambda match: f"{match.group(1)}=***", sanitized)
    return sanitized


class SensitiveDataFilter(logging.Filter):
    """Sanitize log records before they reach disk."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = sanitize_value(record.msg)

        if isinstance(record.args, dict):
            record.args = sanitize_value(record.args)
        elif isinstance(record.args, tuple):
            record.args = tuple(sanitize_value(value) for value in record.args)

        for attribute_name in ("context", "details"):
            if hasattr(record, attribute_name):
                setattr(
                    record,
                    attribute_name,
                    sanitize_value(getattr(record, attribute_name)),
                )

        return True


def configure_file_logger(
    logs_dir: Path | str,
    settings: LoggingSettings,
    *,
    logger_name: str = "rifflock",
) -> logging.Logger:
    """Configure a rotating file logger rooted in the managed logs directory."""

    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)
    log_file_path = logs_path / settings.file_name

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not any(
        isinstance(handler, RotatingFileHandler)
        and Path(getattr(handler, "baseFilename", "")) == log_file_path
        for handler in logger.handlers
    ):
        handler = RotatingFileHandler(
            log_file_path,
            maxBytes=settings.max_bytes,
            backupCount=settings.backup_count,
            encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        handler.addFilter(SensitiveDataFilter())
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
        )
        logger.addHandler(handler)

    return logger


def log_exception(
    logger: logging.Logger,
    message: str,
    error: Exception,
    *,
    context: dict[str, Any] | None = None,
) -> None:
    """Write a sanitized exception log entry."""

    safe_context = sanitize_value(context or {})

    if isinstance(error, RiffLockError):
        details = "redacted" if error.security_sensitive else sanitize_text(error.log_message)
        logger.error(
            "%s | error_type=%s | details=%s | context=%s",
            sanitize_text(message),
            type(error).__name__,
            details,
            safe_context,
        )
        return

    logger.error(
        "%s | error_type=%s | details=%s | context=%s",
        sanitize_text(message),
        type(error).__name__,
        sanitize_text(str(error)),
        safe_context,
    )
