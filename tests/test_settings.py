from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from rifflock.auth import OwnerSetupRequest, OwnerSetupService
from rifflock.config import AudioSettings
from rifflock.crypto import KeyVaultService
from rifflock.files import FileProtectionService, FileRestoreService
from rifflock.models import RiffTemplateRecord
from rifflock.settings import (
    RECORDING_DURATION_KEY,
    SIMILARITY_THRESHOLD_KEY,
    SettingsService,
)
from rifflock.storage import (
    AppSettingRepository,
    KeyVaultRepository,
    OwnerAccountRepository,
    ProtectedItemRepository,
    RiffTemplateRepository,
    initialize_database,
)
from rifflock.utils.errors import AuthenticationError


def test_settings_service_loads_owner_and_defaults(tmp_path: Path) -> None:
    service, _, _, _, _, _ = _build_service(tmp_path)

    state = service.load()

    assert state.owner_email == "owner@example.com"
    assert state.riff_2fa_enabled is False
    assert state.recording_duration_seconds == 5
    assert state.similarity_threshold == pytest.approx(0.8)


def test_settings_service_saves_and_loads_audio_settings_from_sqlite(tmp_path: Path) -> None:
    service, _, _, app_setting_repository, _, _ = _build_service(tmp_path)

    state = service.save_audio_settings(
        recording_duration_seconds=9,
        similarity_threshold=0.67,
    )

    assert state.recording_duration_seconds == 9
    assert state.similarity_threshold == pytest.approx(0.67)
    assert app_setting_repository.get_by_key(RECORDING_DURATION_KEY).setting_value == "9"
    assert app_setting_repository.get_by_key(SIMILARITY_THRESHOLD_KEY).setting_value == "0.6700"
    assert service.load().recording_duration_seconds == 9
    assert service.load().similarity_threshold == pytest.approx(0.67)


def test_settings_service_can_start_riff_enrollment(tmp_path: Path) -> None:
    riff_enrollment_service = Mock()
    service, owner_repository, _, _, _, _ = _build_service(
        tmp_path,
        riff_enrollment_service=riff_enrollment_service,
    )
    owner = owner_repository.get_owner_account()
    assert owner is not None

    service.start_riff_enrollment(password_confirmation="StrongPass123!")

    riff_enrollment_service.enroll.assert_called_once_with(
        owner.id,
        "StrongPass123!",
        before_recording=None,
    )


def test_settings_service_cannot_disable_riff_2fa_without_password_confirmation(tmp_path: Path) -> None:
    service, owner_repository, _, _, _, _ = _build_service(tmp_path, riff_2fa_enabled=True)

    with pytest.raises(AuthenticationError) as error:
        service.disable_riff_2fa(password_confirmation="WrongPass123!")

    assert error.value.user_message == "Password confirmation failed."
    assert owner_repository.get_owner_account().riff_2fa_enabled is True


def test_settings_service_disables_riff_2fa_and_opens_app_data_folder(tmp_path: Path) -> None:
    opener = Mock()
    service, owner_repository, _, _, riff_repository, _ = _build_service(
        tmp_path,
        riff_2fa_enabled=True,
        folder_opener=opener,
        seed_riff_template=True,
    )

    state = service.disable_riff_2fa(password_confirmation="StrongPass123!")
    opened_path = service.open_app_data_folder()

    assert state.riff_2fa_enabled is False
    assert owner_repository.get_owner_account().riff_2fa_enabled is False
    assert riff_repository.get_by_owner_account_id(state.owner_account_id) is None
    opener.assert_called_once_with(str(tmp_path / "app"))
    assert opened_path == tmp_path / "app"


def test_settings_service_rejects_wrong_current_password_for_password_change(tmp_path: Path) -> None:
    service, owner_repository, key_vault_repository, _, _, _ = _build_service(tmp_path)

    with pytest.raises(AuthenticationError) as error:
        service.change_password(
            current_password="WrongPass123!",
            new_password="NewStrongPass123!",
            new_password_confirmation="NewStrongPass123!",
        )

    assert error.value.user_message == "Current password is incorrect."
    owner = owner_repository.get_owner_account()
    assert owner is not None
    key_vault = key_vault_repository.get_by_owner_account_id(owner.id)
    assert key_vault is not None
    assert KeyVaultService().unlock_data_key("StrongPass123!", key_vault) is not None


def test_settings_service_changes_password_and_reprotects_key_vault(tmp_path: Path) -> None:
    service, owner_repository, key_vault_repository, _, _, _ = _build_service(tmp_path)
    owner = owner_repository.get_owner_account()
    assert owner is not None

    service.change_password(
        current_password="StrongPass123!",
        new_password="NewStrongPass123!",
        new_password_confirmation="NewStrongPass123!",
    )

    updated_owner = owner_repository.get_owner_account()
    assert updated_owner is not None
    assert updated_owner.password_hash != owner.password_hash

    updated_vault = key_vault_repository.get_by_owner_account_id(owner.id)
    assert updated_vault is not None
    key_vault_service = KeyVaultService()
    with pytest.raises(AuthenticationError):
        key_vault_service.unlock_data_key("StrongPass123!", updated_vault)
    assert key_vault_service.unlock_data_key("NewStrongPass123!", updated_vault) is not None


def test_files_protected_before_password_change_remain_restorable(tmp_path: Path) -> None:
    service, owner_repository, key_vault_repository, _, _, setup_result = _build_service(tmp_path)
    owner = owner_repository.get_owner_account()
    assert owner is not None
    key_vault_record = key_vault_repository.get_by_owner_account_id(owner.id)
    assert key_vault_record is not None

    key_vault_service = KeyVaultService()
    original_data_key = key_vault_service.unlock_data_key("StrongPass123!", key_vault_record)
    protected_item_repository = ProtectedItemRepository(tmp_path / "data" / "rifflock.db")
    protect_service = FileProtectionService(
        protected_item_repository=protected_item_repository,
        temp_dir=tmp_path / "temp",
    )
    restore_service = FileRestoreService(
        protected_item_repository=protected_item_repository,
        temp_dir=tmp_path / "temp",
    )
    source = tmp_path / "before-change.txt"
    source.write_text("keep restorable", encoding="utf-8")
    protected = protect_service.protect_file(source, original_data_key)

    service.change_password(
        current_password="StrongPass123!",
        new_password="NewStrongPass123!",
        new_password_confirmation="NewStrongPass123!",
    )

    updated_vault = key_vault_repository.get_by_owner_account_id(setup_result.owner_account.id)
    assert updated_vault is not None
    unlocked_after_change = key_vault_service.unlock_data_key("NewStrongPass123!", updated_vault)
    restored = restore_service.restore_file(
        protected.output_path,
        unlocked_after_change,
        tmp_path / "restored-after-change.txt",
    )

    assert restored.restored_path.read_text(encoding="utf-8") == "keep restorable"


def _build_service(
    tmp_path: Path,
    *,
    riff_2fa_enabled: bool = False,
    riff_enrollment_service=None,
    folder_opener=None,
    seed_riff_template: bool = False,
):
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)
    owner_repository = OwnerAccountRepository(database_path)
    key_vault_repository = KeyVaultRepository(database_path)
    app_setting_repository = AppSettingRepository(database_path)
    riff_repository = RiffTemplateRepository(database_path)
    owner_setup_service = OwnerSetupService(owner_repository, key_vault_repository)
    setup_result = owner_setup_service.create_owner_account(
        OwnerSetupRequest(
            email="owner@example.com",
            password="StrongPass123!",
            password_confirmation="StrongPass123!",
            password_loss_acknowledged=True,
        )
    )
    if riff_2fa_enabled:
        owner_repository.save(
            replace(
                setup_result.owner_account,
                riff_2fa_enabled=True,
                updated_at="2026-06-22T00:10:00Z",
            )
        )
    if seed_riff_template:
        riff_repository.save(
            RiffTemplateRecord(
                id=None,
                owner_account_id=setup_result.owner_account.id,
                template_version=1,
                template_data=b'{"sample_rate":22050,"vector":[1.0,2.0]}',
                recording_count=3,
                created_at="2026-06-22T00:00:00Z",
                updated_at="2026-06-22T00:00:00Z",
            )
        )
    service = SettingsService(
        owner_repository=owner_repository,
        app_setting_repository=app_setting_repository,
        default_audio_settings=AudioSettings(),
        app_data_path=tmp_path / "app",
        key_vault_repository=key_vault_repository,
        riff_template_repository=riff_repository,
        riff_enrollment_service=riff_enrollment_service,
        folder_opener=folder_opener,
    )
    return service, owner_repository, key_vault_repository, app_setting_repository, riff_repository, setup_result
