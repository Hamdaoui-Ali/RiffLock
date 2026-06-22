from __future__ import annotations

from pathlib import Path

from rifflock.files import FileProtectionService, FileRestoreService, ProtectedItemService
from rifflock.storage import ProtectedItemRepository, initialize_database
from rifflock.ui.dashboard import DashboardDataService, RestoreFileFlowService


def test_restore_file_flow_uses_selected_output_and_refreshes_dashboard(tmp_path: Path) -> None:
    flow, protect_service = _build_flow(tmp_path)
    source = tmp_path / "demo.txt"
    source.write_text("hello", encoding="utf-8")
    protected = protect_service.protect_file(source, b"x" * 32)
    output = tmp_path / "exports" / "restored-demo.txt"

    result = flow.restore_file(
        protected_path=protected.output_path,
        data_key=b"x" * 32,
        output_path=output,
    )

    assert result.succeeded is True
    assert result.message.startswith("Restored file created at ")
    assert output.read_text(encoding="utf-8") == "hello"
    assert result.state.is_empty is False
    assert result.state.items[0].record.status == "restored"


def test_restore_file_flow_builds_default_output_name_from_container_metadata(tmp_path: Path) -> None:
    flow, protect_service = _build_flow(tmp_path)
    source = tmp_path / "track.wav"
    source.write_text("audio", encoding="utf-8")
    protected = protect_service.protect_file(source, b"x" * 32)

    default_output = flow.get_default_output_path(protected.output_path)

    assert default_output == protected.output_path.with_name("track.wav")


def test_restore_file_flow_returns_clean_failure_message(tmp_path: Path) -> None:
    flow, _ = _build_flow(tmp_path)
    missing = tmp_path / "missing.rifflock"

    result = flow.restore_file(
        protected_path=missing,
        data_key=b"x" * 32,
        output_path=tmp_path / "restored.txt",
    )

    assert result.succeeded is False
    assert result.message == "The selected .rifflock file could not be restored."
    assert result.state.is_empty is True


def _build_flow(tmp_path: Path) -> tuple[RestoreFileFlowService, FileProtectionService]:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)
    repository = ProtectedItemRepository(database_path)
    protected_item_service = ProtectedItemService(repository)
    dashboard_data_service = DashboardDataService(protected_item_service)
    temp_dir = tmp_path / "temp"
    return (
        RestoreFileFlowService(
            file_restore_service=FileRestoreService(
                protected_item_repository=repository,
                temp_dir=temp_dir,
            ),
            dashboard_data_service=dashboard_data_service,
        ),
        FileProtectionService(
            protected_item_repository=repository,
            temp_dir=temp_dir,
        ),
    )
