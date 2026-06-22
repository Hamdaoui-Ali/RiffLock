"""Owner settings service and persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from rifflock.audio.enrollment import RiffEnrollmentService
from rifflock.auth.passwords import PasswordService
from rifflock.config import AudioSettings
from rifflock.crypto import KeyVaultService
from rifflock.models import AppSettingRecord, OwnerAccountRecord
from rifflock.storage import (
    AppSettingRepository,
    KeyVaultRepository,
    OwnerAccountRepository,
    RiffTemplateRepository,
    create_connection,
)
from rifflock.utils.errors import AuthenticationError, StorageError, ValidationError

RECORDING_DURATION_KEY = "audio.recording_duration_seconds"
SIMILARITY_THRESHOLD_KEY = "audio.similarity_threshold"


@dataclass(frozen=True)
class SettingsState:
    owner_account_id: int
    owner_email: str
    riff_2fa_enabled: bool
    recording_duration_seconds: int
    similarity_threshold: float
    app_data_path: Path


class SettingsService:
    """Load and persist owner settings and 2FA preferences."""

    def __init__(
        self,
        owner_repository: OwnerAccountRepository,
        app_setting_repository: AppSettingRepository,
        *,
        default_audio_settings: AudioSettings,
        app_data_path: Path | str,
        key_vault_repository: KeyVaultRepository | None = None,
        riff_template_repository: RiffTemplateRepository | None = None,
        riff_enrollment_service: RiffEnrollmentService | None = None,
        password_service: PasswordService | None = None,
        key_vault_service: KeyVaultService | None = None,
        folder_opener: Callable[[str], object] | None = None,
    ) -> None:
        self._owner_repository = owner_repository
        self._app_setting_repository = app_setting_repository
        self._default_audio_settings = default_audio_settings
        self._app_data_path = Path(app_data_path)
        self._key_vault_repository = key_vault_repository
        self._riff_template_repository = riff_template_repository
        self._riff_enrollment_service = riff_enrollment_service
        self._password_service = password_service or PasswordService()
        self._key_vault_service = key_vault_service or KeyVaultService()
        self._folder_opener = folder_opener or _default_folder_opener

    def load(self) -> SettingsState:
        owner = self._get_owner()
        return SettingsState(
            owner_account_id=owner.id,
            owner_email=owner.email,
            riff_2fa_enabled=owner.riff_2fa_enabled,
            recording_duration_seconds=self._get_recording_duration_seconds(),
            similarity_threshold=self._get_similarity_threshold(),
            app_data_path=self._app_data_path,
        )

    def save_audio_settings(
        self,
        *,
        recording_duration_seconds: int,
        similarity_threshold: float,
    ) -> SettingsState:
        validated_duration = self._validate_duration(recording_duration_seconds)
        validated_threshold = self._validate_threshold(similarity_threshold)
        self._save_setting(RECORDING_DURATION_KEY, str(validated_duration))
        self._save_setting(SIMILARITY_THRESHOLD_KEY, f"{validated_threshold:.4f}")
        return self.load()

    def start_riff_enrollment(self, *, password_confirmation: str) -> SettingsState:
        if self._riff_enrollment_service is None:
            raise StorageError("Riff enrollment is not available.")
        self._riff_enrollment_service.enroll(
            self._get_owner().id,
            password_confirmation,
        )
        return self.load()

    def disable_riff_2fa(self, *, password_confirmation: str) -> SettingsState:
        owner = self._get_owner()
        if not self._password_service.verify_password(password_confirmation, owner.password_hash):
            raise AuthenticationError("Password confirmation failed.")

        updated_owner = self._owner_repository.save(
            OwnerAccountRecord(
                id=owner.id,
                email=owner.email,
                password_hash=owner.password_hash,
                password_policy_version=owner.password_policy_version,
                riff_2fa_enabled=False,
                created_at=owner.created_at,
                updated_at=_utc_now(),
            )
        )
        if self._riff_template_repository is not None:
            existing = self._riff_template_repository.get_by_owner_account_id(updated_owner.id)
            if existing is not None:
                self._riff_template_repository.delete(existing.id)
        return self.load()

    def change_password(
        self,
        *,
        current_password: str,
        new_password: str,
        new_password_confirmation: str,
    ) -> SettingsState:
        owner = self._get_owner()
        if not self._password_service.verify_password(current_password, owner.password_hash):
            raise AuthenticationError("Current password is incorrect.")
        if new_password != new_password_confirmation:
            raise ValidationError("New password confirmation does not match.")
        if self._key_vault_repository is None:
            raise StorageError("Password change is not available.")

        key_vault_record = self._key_vault_repository.get_by_owner_account_id(owner.id)
        if key_vault_record is None or key_vault_record.id is None:
            raise StorageError("Protected key vault is not available.")

        updated_password_hash = self._password_service.hash_password(new_password)
        updated_key_vault = self._key_vault_service.reprotect_data_key(
            current_password=current_password,
            new_password=new_password,
            record=key_vault_record,
        )
        updated_at = _utc_now()

        with create_connection(self._owner_repository.database_path) as connection:
            self._owner_repository.update_password(
                owner_account_id=owner.id,
                password_hash=updated_password_hash,
                password_policy_version=owner.password_policy_version,
                updated_at=updated_at,
                connection=connection,
            )
            self._key_vault_repository.update_protected_data(
                record_id=updated_key_vault.id,
                kdf_parameters=updated_key_vault.kdf_parameters,
                salt=updated_key_vault.salt,
                nonce=updated_key_vault.nonce,
                ciphertext=updated_key_vault.ciphertext,
                updated_at=updated_key_vault.updated_at,
                connection=connection,
            )
            connection.commit()

        return self.load()

    def open_app_data_folder(self) -> Path:
        self._folder_opener(str(self._app_data_path))
        return self._app_data_path

    def _get_owner(self) -> OwnerAccountRecord:
        owner = self._owner_repository.get_owner_account()
        if owner is None or owner.id is None:
            raise StorageError("Owner settings are not available.")
        return owner

    def _get_recording_duration_seconds(self) -> int:
        record = self._app_setting_repository.get_by_key(RECORDING_DURATION_KEY)
        if record is None:
            return self._default_audio_settings.duration_seconds
        return self._validate_duration(int(record.setting_value))

    def _get_similarity_threshold(self) -> float:
        record = self._app_setting_repository.get_by_key(SIMILARITY_THRESHOLD_KEY)
        if record is None:
            return self._default_audio_settings.similarity_threshold
        return self._validate_threshold(float(record.setting_value))

    def _save_setting(self, key: str, value: str) -> AppSettingRecord:
        existing = self._app_setting_repository.get_by_key(key)
        return self._app_setting_repository.save(
            AppSettingRecord(
                id=None if existing is None else existing.id,
                setting_key=key,
                setting_value=value,
                updated_at=_utc_now(),
            )
        )

    def _validate_duration(self, value: int) -> int:
        if value <= 0 or value > 60:
            raise ValidationError("Recording duration must be between 1 and 60 seconds.")
        return value

    def _validate_threshold(self, value: float) -> float:
        if value <= 0 or value > 1:
            raise ValidationError("Riff similarity threshold must be greater than 0 and at most 1.")
        return value


def _default_folder_opener(path: str) -> None:
    import os

    if hasattr(os, "startfile"):
        os.startfile(path)
        return

    import subprocess

    subprocess.Popen(["explorer", path])


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
