from __future__ import annotations

from pathlib import Path

from rifflock.files import ProtectedItemService
from rifflock.models import AuthAttemptRecord
from rifflock.storage import AuthAttemptRepository, ProtectedItemRepository, initialize_database
from rifflock.ui.activity import ActivityDataService
from rifflock.ui.dashboard import DashboardDataService


def test_activity_data_service_combines_auth_attempts_and_vault_events(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)

    source = tmp_path / "demo.wav"
    artifact = tmp_path / "demo.wav.rifflock"
    source.write_text("demo", encoding="utf-8")
    artifact.write_text("encrypted", encoding="utf-8")

    auth_attempt_repository = AuthAttemptRepository(database_path)
    auth_attempt_repository.save(
        AuthAttemptRecord(
            id=None,
            attempt_type="password",
            identifier="owner@example.com",
            was_successful=False,
            failure_reason="invalid_credentials",
            attempted_at="2026-06-22T00:00:02Z",
        )
    )

    protected_item_service = ProtectedItemService(ProtectedItemRepository(database_path))
    protected_item_service.create_item(
        item_type="file",
        source_path=str(source),
        artifact_path=str(artifact),
        file_size=512,
    )

    service = ActivityDataService(
        auth_attempt_repository,
        DashboardDataService(protected_item_service),
        password_attempt_limit=3,
        riff_attempt_limit=3,
    )

    state = service.load(owner_email="owner@example.com")

    assert state.failed_password_attempts == 1
    assert state.protected_count == 1
    assert any(event.title == "Password Auth" for event in state.events)
    assert any(event.title == "File Protected" for event in state.events)
