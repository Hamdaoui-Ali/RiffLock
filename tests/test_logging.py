from __future__ import annotations

from pathlib import Path

from rifflock.config import LoggingSettings
from rifflock.utils import (
    CryptoOperationError,
    FileOperationError,
    configure_file_logger,
    log_exception,
    sanitize_value,
    to_user_message,
)


def test_logger_writes_to_managed_log_file(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logger = configure_file_logger(
        logs_dir,
        LoggingSettings(file_name="test.log", max_bytes=256, backup_count=1),
        logger_name="rifflock.tests.write",
    )

    logger.info("startup complete")

    log_contents = (logs_dir / "test.log").read_text(encoding="utf-8")
    assert "startup complete" in log_contents


def test_sensitive_fields_are_masked_in_logged_messages(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logger = configure_file_logger(
        logs_dir,
        LoggingSettings(file_name="masked.log", max_bytes=256, backup_count=1),
        logger_name="rifflock.tests.masking",
    )

    logger.info(
        "password=hunter2 key=abcd ciphertext=payload",
    )
    logger.info(
        "structured payload: %s",
        {"password": "hunter2", "safe_path": r"C:\exports\demo.rifflock"},
    )

    log_contents = (logs_dir / "masked.log").read_text(encoding="utf-8")
    assert "hunter2" not in log_contents
    assert "ciphertext=payload" not in log_contents
    assert "password=***" in log_contents
    assert "key=***" in log_contents
    assert "safe_path" in log_contents


def test_exception_logging_and_user_messages_do_not_expose_secrets(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logger = configure_file_logger(
        logs_dir,
        LoggingSettings(file_name="errors.log", max_bytes=4096, backup_count=1),
        logger_name="rifflock.tests.errors",
    )

    crypto_error = CryptoOperationError(
        "Unable to unlock data.",
        log_message="key=abcdef ciphertext=secret-bytes",
        security_sensitive=True,
    )
    file_error = FileOperationError(
        "Unable to restore the file.",
        log_message="source_path=C:\\temp\\input.txt file_content=secret",
    )

    log_exception(logger, "Crypto failure during restore.", crypto_error, context={"password": "hunter2"})
    log_exception(logger, "File restore failure.", file_error)

    log_contents = (logs_dir / "errors.log").read_text(encoding="utf-8")
    assert "hunter2" not in log_contents
    assert "abcdef" not in log_contents
    assert "secret-bytes" not in log_contents
    assert "details=redacted" in log_contents
    assert "file_content=secret" not in log_contents

    assert to_user_message(crypto_error) == "The operation could not be completed. Please try again."
    assert to_user_message(file_error) == "Unable to restore the file."
    assert sanitize_value({"raw_audio": b"abc", "password": "hunter2"}) == {
        "raw_audio": "***",
        "password": "***",
    }
