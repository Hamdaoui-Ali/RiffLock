from __future__ import annotations

from pathlib import Path

from rifflock.files import FileProtectionService, ProtectedItemService
from rifflock.storage import ProtectedItemRepository, initialize_database
from rifflock.ui.dashboard import DashboardDataService, DeleteProtectedItemFlowService


def test_dashboard_data_loading_empty_state(tmp_path: Path) -> None:
    service = _build_dashboard_data_service(tmp_path)

    state = service.load()

    assert state.is_empty is True
    assert state.items == []


def test_dashboard_data_loading_with_items(tmp_path: Path) -> None:
    repository = ProtectedItemRepository(_database_path(tmp_path))
    initialize_database(_database_path(tmp_path))
    protected_item_service = ProtectedItemService(repository)
    protected_item_service.create_item(
        item_type="file",
        source_path=str(tmp_path / "source.txt"),
        artifact_path=str(tmp_path / "source.rifflock"),
        file_size=42,
    )

    state = DashboardDataService(protected_item_service).load()

    assert state.is_empty is False
    assert len(state.items) == 1
    assert state.items[0].record.item_type == "file"
    assert state.items[0].record.status == "protected"


def test_delete_protected_item_flow_removes_artifact_and_metadata(tmp_path: Path) -> None:
    repository = ProtectedItemRepository(_database_path(tmp_path))
    initialize_database(_database_path(tmp_path))
    dashboard_data_service = DashboardDataService(ProtectedItemService(repository))
    flow = DeleteProtectedItemFlowService(
        protected_item_service=ProtectedItemService(repository),
        dashboard_data_service=dashboard_data_service,
    )

    source = tmp_path / "source.txt"
    source.write_text("delete me", encoding="utf-8")
    protected = FileProtectionService(repository, tmp_path / "temp").protect_file(source, b"x" * 32)
    item = dashboard_data_service.load().items[0]

    result = flow.delete_item(item)

    assert result.succeeded is True
    assert result.message == f"Removed {protected.output_path.name} from protection."
    assert protected.output_path.exists() is False
    assert source.exists() is True
    assert repository.get_by_id(protected.protected_item.id) is None
    assert result.state.is_empty is True


def test_delete_protected_item_flow_handles_missing_artifact(tmp_path: Path) -> None:
    repository = ProtectedItemRepository(_database_path(tmp_path))
    initialize_database(_database_path(tmp_path))
    dashboard_data_service = DashboardDataService(ProtectedItemService(repository))
    flow = DeleteProtectedItemFlowService(
        protected_item_service=ProtectedItemService(repository),
        dashboard_data_service=dashboard_data_service,
    )

    source = tmp_path / "source.txt"
    source.write_text("delete me", encoding="utf-8")
    protected = FileProtectionService(repository, tmp_path / "temp").protect_file(source, b"x" * 32)
    protected.output_path.unlink()
    item = dashboard_data_service.load().items[0]

    result = flow.delete_item(item)

    assert result.succeeded is True
    assert repository.get_by_id(protected.protected_item.id) is None
    assert result.state.is_empty is True


def _build_dashboard_data_service(tmp_path: Path) -> DashboardDataService:
    database_path = _database_path(tmp_path)
    initialize_database(database_path)
    repository = ProtectedItemRepository(database_path)
    return DashboardDataService(ProtectedItemService(repository))


def _database_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "rifflock.db"
