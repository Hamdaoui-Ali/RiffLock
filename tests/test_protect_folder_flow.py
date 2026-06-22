from __future__ import annotations

from pathlib import Path

from rifflock.files import FolderProtectionService, ProtectedItemService
from rifflock.storage import ProtectedItemRepository, initialize_database
from rifflock.ui.dashboard import DashboardDataService, ProtectFolderFlowService


def test_protect_folder_flow_uses_default_vault_location_and_refreshes_dashboard(tmp_path: Path) -> None:
    flow = _build_flow(tmp_path)
    source = tmp_path / "session"
    source.mkdir()
    (source / "track.txt").write_text("hello", encoding="utf-8")

    result = flow.protect_folder(
        source_path=source,
        data_key=b"x" * 32,
    )

    assert result.succeeded is True
    assert result.message.startswith("Folder protection finished at ")
    assert "Protected: 1." in result.message
    assert "Skipped: 0." in result.message
    assert "Failed: 0." in result.message
    assert result.state.is_empty is False
    assert any(item.record.item_type == "folder" for item in result.state.items)
    assert (tmp_path / "vault" / "session.rifflock" / "track.txt.rifflock").exists()


def test_protect_folder_flow_reports_partial_failures_clearly(tmp_path: Path) -> None:
    flow = _build_flow(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    (source / "good.txt").write_text("good", encoding="utf-8")
    (source / "conflict.txt").write_text("conflict", encoding="utf-8")
    output = tmp_path / "vault" / "source.rifflock"
    output.mkdir(parents=True)
    (output / "conflict.txt.rifflock").write_text("existing", encoding="utf-8")

    result = flow.protect_folder(
        source_path=source,
        data_key=b"x" * 32,
        output_path=output,
    )

    assert result.succeeded is False
    assert "Protected: 1." in result.message
    assert "Failed: 1." in result.message
    assert "First failure: conflict.txt - The selected output file already exists." in result.message
    assert (output / "good.txt.rifflock").exists()
    assert source.exists()


def test_protect_folder_flow_returns_clean_failure_message(tmp_path: Path) -> None:
    flow = _build_flow(tmp_path)

    result = flow.protect_folder(
        source_path=tmp_path / "missing",
        data_key=b"x" * 32,
    )

    assert result.succeeded is False
    assert result.message == "The selected folder could not be protected."
    assert result.state.is_empty is True


def _build_flow(tmp_path: Path) -> ProtectFolderFlowService:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)
    repository = ProtectedItemRepository(database_path)
    protected_item_service = ProtectedItemService(repository)
    dashboard_data_service = DashboardDataService(protected_item_service)
    return ProtectFolderFlowService(
        folder_protection_service=FolderProtectionService(
            protected_item_repository=repository,
            temp_dir=tmp_path / "temp",
        ),
        dashboard_data_service=dashboard_data_service,
        default_output_dir=tmp_path / "vault",
    )
