from __future__ import annotations

from pathlib import Path

from rifflock.files import ProtectedItemService
from rifflock.storage import ProtectedItemRepository, initialize_database
from rifflock.ui.dashboard import DashboardDataService


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


def _build_dashboard_data_service(tmp_path: Path) -> DashboardDataService:
    database_path = _database_path(tmp_path)
    initialize_database(database_path)
    repository = ProtectedItemRepository(database_path)
    return DashboardDataService(ProtectedItemService(repository))


def _database_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "rifflock.db"
