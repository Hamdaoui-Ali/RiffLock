from __future__ import annotations

from pathlib import Path

from rifflock.files import FileProtectionService, ProtectedItemService
from rifflock.storage import ProtectedItemRepository, initialize_database
from rifflock.ui.dashboard import DashboardDataService, ProtectFileFlowService


def test_protect_file_flow_uses_default_vault_location_and_refreshes_dashboard(tmp_path: Path) -> None:
    flow = _build_flow(tmp_path)
    source = tmp_path / "demo.txt"
    source.write_text("hello", encoding="utf-8")

    result = flow.protect_file(
        source_path=source,
        data_key=b"x" * 32,
    )

    assert result.succeeded is True
    assert result.message.startswith("Protected file created at ")
    assert result.state.is_empty is False
    assert len(result.state.items) == 1
    assert Path(result.state.items[0].record.artifact_path).parent == tmp_path / "vault"
    assert (tmp_path / "vault" / "demo.txt.rifflock").exists()


def test_protect_file_flow_uses_selected_output_location(tmp_path: Path) -> None:
    flow = _build_flow(tmp_path)
    source = tmp_path / "demo.txt"
    source.write_text("hello", encoding="utf-8")
    output = tmp_path / "exports" / "custom-name.rifflock"

    result = flow.protect_file(
        source_path=source,
        data_key=b"x" * 32,
        output_path=output,
    )

    assert result.succeeded is True
    assert output.exists()
    assert Path(result.state.items[0].record.artifact_path) == output


def test_protect_file_flow_returns_clean_failure_message(tmp_path: Path) -> None:
    flow = _build_flow(tmp_path)
    source = tmp_path / "missing.txt"

    result = flow.protect_file(
        source_path=source,
        data_key=b"x" * 32,
    )

    assert result.succeeded is False
    assert result.message == "The selected file could not be protected."
    assert result.state.is_empty is True


def _build_flow(tmp_path: Path) -> ProtectFileFlowService:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)
    repository = ProtectedItemRepository(database_path)
    protected_item_service = ProtectedItemService(repository)
    dashboard_data_service = DashboardDataService(protected_item_service)
    return ProtectFileFlowService(
        file_protection_service=FileProtectionService(
            protected_item_repository=repository,
            temp_dir=tmp_path / "temp",
        ),
        dashboard_data_service=dashboard_data_service,
        default_output_dir=tmp_path / "vault",
    )
