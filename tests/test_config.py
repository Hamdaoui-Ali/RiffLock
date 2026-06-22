from __future__ import annotations

from pathlib import Path

from rifflock.config import (
    APP_BASE_DIR_ENV_VAR,
    APP_NAME,
    DEFAULT_AUDIO_DURATION_SECONDS,
    DEFAULT_AUDIO_SAMPLE_RATE,
    DEFAULT_LOCKOUT_DURATION_SECONDS,
    DEFAULT_PASSWORD_LOCKOUT_THRESHOLD,
    DEFAULT_RIFF_LOCKOUT_THRESHOLD,
    DEFAULT_RIFF_SIMILARITY_THRESHOLD,
    build_app_paths,
    ensure_app_directories,
    get_default_base_dir,
    load_config,
)


def test_build_app_paths_generates_expected_subdirectories(tmp_path: Path) -> None:
    paths = build_app_paths(tmp_path)

    assert paths.base_dir == tmp_path.resolve()
    assert paths.data_dir == tmp_path / "data"
    assert paths.database_path == tmp_path / "data" / "rifflock.db"
    assert paths.vault_dir == tmp_path / "vault"
    assert paths.temp_dir == tmp_path / "temp"
    assert paths.logs_dir == tmp_path / "logs"
    assert paths.samples_dir == tmp_path / "samples"
    assert paths.exports_dir == tmp_path / "exports"


def test_ensure_app_directories_creates_required_folders(tmp_path: Path) -> None:
    paths = build_app_paths(tmp_path / "app")

    ensure_app_directories(paths)

    for directory in paths.all_dirs():
        assert directory.exists()
        assert directory.is_dir()


def test_load_config_can_override_real_appdata_with_env_var(
    tmp_path: Path,
    monkeypatch,
) -> None:
    override_dir = tmp_path / "test-rifflock"
    monkeypatch.setenv(APP_BASE_DIR_ENV_VAR, str(override_dir))

    config = load_config()

    assert config.app_name == APP_NAME
    assert config.paths.base_dir == override_dir.resolve()
    assert config.paths.base_dir != get_default_base_dir().resolve()
    assert config.audio.duration_seconds == DEFAULT_AUDIO_DURATION_SECONDS
    assert config.audio.sample_rate == DEFAULT_AUDIO_SAMPLE_RATE
    assert config.audio.similarity_threshold == DEFAULT_RIFF_SIMILARITY_THRESHOLD
    assert config.lockout.password_attempt_limit == DEFAULT_PASSWORD_LOCKOUT_THRESHOLD
    assert config.lockout.riff_attempt_limit == DEFAULT_RIFF_LOCKOUT_THRESHOLD
    assert config.lockout.duration_seconds == DEFAULT_LOCKOUT_DURATION_SECONDS
