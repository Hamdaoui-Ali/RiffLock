from __future__ import annotations

from pathlib import Path

import numpy as np

from rifflock.audio import RiffComparisonResult, RiffEnrollmentService, RiffFeatureTemplate
from rifflock.auth import (
    LoginService,
    OwnerSetupRequest,
    OwnerSetupService,
    SessionService,
)
from rifflock.auth.riff_verification import RiffVerificationService
from rifflock.config import AudioSettings, LockoutSettings
from rifflock.files import FileProtectionService, FileRestoreService, FolderProtectionService
from rifflock.settings import SettingsService
from rifflock.storage import (
    AppSettingRepository,
    AuthAttemptRepository,
    KeyVaultRepository,
    OwnerAccountRepository,
    ProtectedItemRepository,
    RiffTemplateRepository,
    initialize_database,
)


def test_app_restart_keeps_database_state_and_allows_login_restore_and_folder_protection(
    tmp_path: Path,
) -> None:
    services = _build_services(tmp_path)
    services.owner_setup_service.create_owner_account(
        OwnerSetupRequest(
            email="owner@example.com",
            password="StrongPass123!",
            password_confirmation="StrongPass123!",
            password_loss_acknowledged=True,
        )
    )

    login_result = services.login_service.login("owner@example.com", "StrongPass123!")
    assert login_result.session is not None

    source = tmp_path / "draft.txt"
    source.write_text("local secret", encoding="utf-8")
    protected = services.file_protection_service.protect_file(
        source,
        login_result.session.unlocked_data_key,
    )

    services.login_service.logout()
    restarted = _build_services(tmp_path)
    restored_login = restarted.login_service.login("owner@example.com", "StrongPass123!")
    assert restored_login.session is not None

    restored = restarted.file_restore_service.restore_file(
        protected.output_path,
        restored_login.session.unlocked_data_key,
        tmp_path / "restored.txt",
    )
    assert restored.restored_path.read_text(encoding="utf-8") == "local secret"

    folder = tmp_path / "album"
    (folder / "nested").mkdir(parents=True)
    (folder / "track1.txt").write_text("track1", encoding="utf-8")
    (folder / "nested" / "track2.txt").write_text("track2", encoding="utf-8")

    folder_result = restarted.folder_protection_service.protect_folder(
        folder,
        restored_login.session.unlocked_data_key,
    )
    assert folder_result.protected_count == 2
    assert restarted.owner_repository.get_owner_account() is not None


def test_password_change_and_riff_2fa_survive_restart_and_old_files_still_restore(
    tmp_path: Path,
) -> None:
    services = _build_services(tmp_path)
    setup_result = services.owner_setup_service.create_owner_account(
        OwnerSetupRequest(
            email="owner@example.com",
            password="StrongPass123!",
            password_confirmation="StrongPass123!",
            password_loss_acknowledged=True,
        )
    )

    initial_login = services.login_service.login("owner@example.com", "StrongPass123!")
    assert initial_login.session is not None

    source = tmp_path / "before-password-change.txt"
    source.write_text("restore me later", encoding="utf-8")
    protected = services.file_protection_service.protect_file(
        source,
        initial_login.session.unlocked_data_key,
    )

    services.settings_service.change_password(
        current_password="StrongPass123!",
        new_password="NewStrongPass123!",
        new_password_confirmation="NewStrongPass123!",
    )
    services.settings_service.start_riff_enrollment(password_confirmation="NewStrongPass123!")

    restarted = _build_services(tmp_path)
    login_result = restarted.login_service.login("owner@example.com", "NewStrongPass123!")
    assert login_result.next_screen == "riff_verification"
    assert login_result.pending_riff_verification is not None

    verified_session = restarted.riff_verification_service.verify(
        login_result.pending_riff_verification
    )
    assert verified_session.riff_2fa_enabled is True

    restored = restarted.file_restore_service.restore_file(
        protected.output_path,
        verified_session.unlocked_data_key,
        tmp_path / "restored-after-password-change.txt",
    )
    assert restored.restored_path.read_text(encoding="utf-8") == "restore me later"

    owner = restarted.owner_repository.get_owner_account()
    assert owner is not None
    assert owner.id == setup_result.owner_account.id


class _FakeRecordingService:
    def record(self):
        from rifflock.audio.recording import AudioRecording

        return AudioRecording(
            samples=np.array([0.5, 0.4, 0.3, 0.2], dtype=np.float32),
            sample_rate=22050,
            duration_seconds=1,
        )


class _FakeFeatureExtractionService:
    def __init__(self, template: RiffFeatureTemplate) -> None:
        self._template = template

    def extract(self, samples, sample_rate):
        return self._template


class _FakeSimilarityService:
    def compare(self, stored_template, candidate_template):
        return RiffComparisonResult(
            score=0.95,
            passed=True,
            threshold=AudioSettings().similarity_threshold,
        )


class _Services:
    def __init__(self, tmp_path: Path) -> None:
        self.database_path = tmp_path / "data" / "rifflock.db"
        initialize_database(self.database_path)
        self.owner_repository = OwnerAccountRepository(self.database_path)
        self.key_vault_repository = KeyVaultRepository(self.database_path)
        self.riff_template_repository = RiffTemplateRepository(self.database_path)
        self.auth_attempt_repository = AuthAttemptRepository(self.database_path)
        self.app_setting_repository = AppSettingRepository(self.database_path)
        self.protected_item_repository = ProtectedItemRepository(self.database_path)

        self.owner_setup_service = OwnerSetupService(
            owner_repository=self.owner_repository,
            key_vault_repository=self.key_vault_repository,
        )
        self.session_service = SessionService()
        self.login_service = LoginService(
            owner_repository=self.owner_repository,
            key_vault_repository=self.key_vault_repository,
            session_service=self.session_service,
            auth_attempt_repository=self.auth_attempt_repository,
            lockout_settings=LockoutSettings(),
        )
        self.file_protection_service = FileProtectionService(
            protected_item_repository=self.protected_item_repository,
            temp_dir=tmp_path / "temp",
        )
        self.file_restore_service = FileRestoreService(
            protected_item_repository=self.protected_item_repository,
            temp_dir=tmp_path / "temp",
        )
        self.folder_protection_service = FolderProtectionService(
            protected_item_repository=self.protected_item_repository,
            temp_dir=tmp_path / "temp",
        )
        template = RiffFeatureTemplate(
            vector=np.asarray([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
            sample_rate=22050,
            chroma_sequence=np.tile(
                np.asarray([1.0, 2.0, 3.0, 4.0], dtype=np.float32).reshape(-1, 1),
                (1, 2),
            ),
            onset_count=2,
        )
        self.riff_enrollment_service = RiffEnrollmentService(
            owner_repository=self.owner_repository,
            riff_template_repository=self.riff_template_repository,
            recording_service=_FakeRecordingService(),
            feature_extraction_service=_FakeFeatureExtractionService(template),
        )
        self.settings_service = SettingsService(
            owner_repository=self.owner_repository,
            app_setting_repository=self.app_setting_repository,
            default_audio_settings=AudioSettings(),
            app_data_path=tmp_path / "app",
            key_vault_repository=self.key_vault_repository,
            riff_template_repository=self.riff_template_repository,
            riff_enrollment_service=self.riff_enrollment_service,
        )
        self.riff_verification_service = RiffVerificationService(
            owner_repository=self.owner_repository,
            key_vault_repository=self.key_vault_repository,
            riff_template_repository=self.riff_template_repository,
            recording_service=_FakeRecordingService(),
            feature_extraction_service=_FakeFeatureExtractionService(template),
            similarity_service=_FakeSimilarityService(),
            session_service=self.session_service,
        )


def _build_services(tmp_path: Path) -> _Services:
    return _Services(tmp_path)
