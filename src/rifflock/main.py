"""Application bootstrap for the RiffLock desktop app."""

from rifflock.auth import LoginService, LockoutService, OwnerSetupService, SessionService
from rifflock.audio import (
    RiffEnrollmentService,
    RiffFeatureExtractionService,
    RiffSimilarityService,
)
from rifflock.audio.recording import MicrophoneRecordingService
from rifflock.auth.riff_verification import RiffVerificationService
from rifflock.config import ensure_app_directories, load_config
from rifflock.files import (
    FileProtectionService,
    FileRestoreService,
    FolderProtectionService,
    ProtectedItemService,
)
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
from rifflock.ui.app import launch_app
from rifflock.ui.dashboard import (
    DashboardDataService,
    DeleteProtectedItemFlowService,
    ProtectFileFlowService,
    ProtectFolderFlowService,
    RestoreFileFlowService,
)
from rifflock.ui.routes import determine_initial_route
from rifflock.utils import configure_file_logger, log_exception


def main() -> int:
    """Start the desktop application."""
    config = load_config()
    ensure_app_directories(config.paths)
    logger = configure_file_logger(config.paths.logs_dir, config.logging)

    try:
        initialize_database(config.paths.database_path)
        owner_repository = OwnerAccountRepository(config.paths.database_path)
        key_vault_repository = KeyVaultRepository(config.paths.database_path)
        riff_template_repository = RiffTemplateRepository(config.paths.database_path)
        auth_attempt_repository = AuthAttemptRepository(config.paths.database_path)
        app_setting_repository = AppSettingRepository(config.paths.database_path)
        protected_item_repository = ProtectedItemRepository(config.paths.database_path)
        owner_setup_service = OwnerSetupService(
            owner_repository=owner_repository,
            key_vault_repository=key_vault_repository,
            logger=logger,
        )
        session_service = SessionService()
        lockout_service = LockoutService(
            auth_attempt_repository=auth_attempt_repository,
            lockout_settings=config.lockout,
            logger=logger,
        )
        login_service = LoginService(
            owner_repository=owner_repository,
            key_vault_repository=key_vault_repository,
            session_service=session_service,
            lockout_service=lockout_service,
            logger=logger,
        )
        recording_service = MicrophoneRecordingService(config.audio, logger=logger)
        feature_extraction_service = RiffFeatureExtractionService(logger=logger)
        protected_item_service = ProtectedItemService(protected_item_repository)
        dashboard_data_service = DashboardDataService(protected_item_service)
        protect_file_flow_service = ProtectFileFlowService(
            file_protection_service=FileProtectionService(
                protected_item_repository=protected_item_repository,
                temp_dir=config.paths.temp_dir,
            ),
            dashboard_data_service=dashboard_data_service,
            default_output_dir=config.paths.vault_dir,
        )
        protect_folder_flow_service = ProtectFolderFlowService(
            folder_protection_service=FolderProtectionService(
                protected_item_repository=protected_item_repository,
                temp_dir=config.paths.temp_dir,
            ),
            dashboard_data_service=dashboard_data_service,
            default_output_dir=config.paths.vault_dir,
        )
        restore_file_flow_service = RestoreFileFlowService(
            file_restore_service=FileRestoreService(
                protected_item_repository=protected_item_repository,
                temp_dir=config.paths.temp_dir,
            ),
            dashboard_data_service=dashboard_data_service,
        )
        delete_protected_item_flow_service = DeleteProtectedItemFlowService(
            protected_item_service=protected_item_service,
            dashboard_data_service=dashboard_data_service,
        )
        settings_service = SettingsService(
            owner_repository=owner_repository,
            app_setting_repository=app_setting_repository,
            default_audio_settings=config.audio,
            app_data_path=config.paths.base_dir,
            key_vault_repository=key_vault_repository,
            riff_template_repository=riff_template_repository,
            riff_enrollment_service=RiffEnrollmentService(
                owner_repository=owner_repository,
                riff_template_repository=riff_template_repository,
                recording_service=recording_service,
                feature_extraction_service=feature_extraction_service,
                logger=logger,
            ),
        )
        riff_verification_service = RiffVerificationService(
            owner_repository=owner_repository,
            key_vault_repository=key_vault_repository,
            riff_template_repository=riff_template_repository,
            recording_service=recording_service,
            feature_extraction_service=feature_extraction_service,
            similarity_service=RiffSimilarityService(config.audio, logger=logger),
            session_service=session_service,
            lockout_service=lockout_service,
            logger=logger,
        )
        route = determine_initial_route(owner_setup_service)
        logger.info("Application startup initialized successfully.")
        launch_app(
            config,
            route,
            dashboard_data_service=dashboard_data_service,
            protect_file_flow_service=protect_file_flow_service,
            protect_folder_flow_service=protect_folder_flow_service,
            restore_file_flow_service=restore_file_flow_service,
            delete_protected_item_flow_service=delete_protected_item_flow_service,
            settings_service=settings_service,
            owner_setup_service=owner_setup_service,
            login_service=login_service,
            riff_verification_service=riff_verification_service,
        )
    except Exception as error:
        log_exception(logger, "Application startup failed.", error)
        raise

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
