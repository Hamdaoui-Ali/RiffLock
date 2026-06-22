"""Central configuration values for RiffLock."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "RiffLock"
APP_BASE_DIR_ENV_VAR = "RIFFLOCK_BASE_DIR"

DEFAULT_AUDIO_DURATION_SECONDS = 5
DEFAULT_AUDIO_SAMPLE_RATE = 44100
DEFAULT_RIFF_SIMILARITY_THRESHOLD = 0.8
DEFAULT_PASSWORD_LOCKOUT_THRESHOLD = 3
DEFAULT_RIFF_LOCKOUT_THRESHOLD = 3
DEFAULT_LOCKOUT_DURATION_SECONDS = 60
DEFAULT_LOG_FILE_NAME = "rifflock.log"
DEFAULT_LOG_MAX_BYTES = 1048576
DEFAULT_LOG_BACKUP_COUNT = 3


@dataclass(frozen=True)
class AppPaths:
    """Resolved local paths used by the application."""

    base_dir: Path
    data_dir: Path
    database_path: Path
    vault_dir: Path
    temp_dir: Path
    logs_dir: Path
    log_file_path: Path
    samples_dir: Path
    exports_dir: Path

    def all_dirs(self) -> tuple[Path, ...]:
        return (
            self.base_dir,
            self.data_dir,
            self.temp_dir,
            self.vault_dir,
            self.logs_dir,
            self.samples_dir,
            self.exports_dir,
        )


@dataclass(frozen=True)
class AudioSettings:
    """Default audio configuration for riff enrollment and verification."""

    duration_seconds: int = DEFAULT_AUDIO_DURATION_SECONDS
    sample_rate: int = DEFAULT_AUDIO_SAMPLE_RATE
    similarity_threshold: float = DEFAULT_RIFF_SIMILARITY_THRESHOLD


@dataclass(frozen=True)
class LockoutSettings:
    """Default temporary lockout rules."""

    password_attempt_limit: int = DEFAULT_PASSWORD_LOCKOUT_THRESHOLD
    riff_attempt_limit: int = DEFAULT_RIFF_LOCKOUT_THRESHOLD
    duration_seconds: int = DEFAULT_LOCKOUT_DURATION_SECONDS


@dataclass(frozen=True)
class LoggingSettings:
    """Default file logging configuration."""

    file_name: str = DEFAULT_LOG_FILE_NAME
    max_bytes: int = DEFAULT_LOG_MAX_BYTES
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT


@dataclass(frozen=True)
class AppConfig:
    """Central application configuration."""

    app_name: str
    paths: AppPaths
    audio: AudioSettings
    lockout: LockoutSettings
    logging: LoggingSettings


def get_default_base_dir() -> Path:
    """Return the default Windows-compatible AppData base directory."""

    local_app_data = Path.home() / "AppData" / "Local"
    return local_app_data / APP_NAME


def resolve_base_dir(base_dir: Path | str | None = None) -> Path:
    """Resolve the base application directory, honoring test overrides."""

    if base_dir is not None:
        return Path(base_dir).expanduser().resolve()

    env_override = os.getenv(APP_BASE_DIR_ENV_VAR)
    if env_override:
        return Path(env_override).expanduser().resolve()

    return get_default_base_dir().resolve()


def build_app_paths(base_dir: Path | str | None = None) -> AppPaths:
    """Build all managed application paths from a base directory."""

    resolved_base = resolve_base_dir(base_dir)
    return AppPaths(
        base_dir=resolved_base,
        data_dir=resolved_base / "data",
        database_path=resolved_base / "data" / "rifflock.db",
        vault_dir=resolved_base / "vault",
        temp_dir=resolved_base / "temp",
        logs_dir=resolved_base / "logs",
        log_file_path=resolved_base / "logs" / DEFAULT_LOG_FILE_NAME,
        samples_dir=resolved_base / "samples",
        exports_dir=resolved_base / "exports",
    )


def ensure_app_directories(paths: AppPaths) -> AppPaths:
    """Create the managed local directory structure if it is missing."""

    for directory in paths.all_dirs():
        directory.mkdir(parents=True, exist_ok=True)
    return paths


def load_config(base_dir: Path | str | None = None) -> AppConfig:
    """Load the full application configuration."""

    return AppConfig(
        app_name=APP_NAME,
        paths=build_app_paths(base_dir),
        audio=AudioSettings(),
        lockout=LockoutSettings(),
        logging=LoggingSettings(),
    )
