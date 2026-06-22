from __future__ import annotations

from pathlib import Path

from rifflock.files import (
    STATUS_MISSING_PROTECTED,
    STATUS_PROTECTED,
    STATUS_RESTORED,
    FileProtectionService,
    ProtectedItemService,
)
from rifflock.storage import ProtectedItemRepository, initialize_database


def test_saving_protected_item_metadata(tmp_path: Path) -> None:
    _, item_service, _ = _build_services(tmp_path)

    saved = item_service.create_item(
        item_type="file",
        source_path=str(tmp_path / "source.txt"),
        artifact_path=str(tmp_path / "artifact.rifflock"),
        file_size=123,
    )

    assert saved.id is not None
    assert saved.status == STATUS_PROTECTED


def test_listing_protected_items(tmp_path: Path) -> None:
    _, item_service, _ = _build_services(tmp_path)

    item_service.create_item(
        item_type="file",
        source_path=str(tmp_path / "a.txt"),
        artifact_path=str(tmp_path / "a.rifflock"),
        file_size=10,
    )
    item_service.create_item(
        item_type="folder",
        source_path=str(tmp_path / "docs"),
        artifact_path=str(tmp_path / "docs.rifflock"),
        file_size=None,
    )

    items = item_service.list_items()

    assert len(items) == 2
    assert items[0].record.item_type == "file"
    assert items[1].record.item_type == "folder"


def test_updating_status(tmp_path: Path) -> None:
    _, item_service, repository = _build_services(tmp_path)

    saved = item_service.create_item(
        item_type="file",
        source_path=str(tmp_path / "source.txt"),
        artifact_path=str(tmp_path / "artifact.rifflock"),
        file_size=1,
    )

    updated = item_service.update_status(saved.id, STATUS_RESTORED)
    stored = repository.get_by_id(saved.id)

    assert updated.status == STATUS_RESTORED
    assert stored is not None
    assert stored.status == STATUS_RESTORED


def test_removing_metadata_without_deleting_files(tmp_path: Path) -> None:
    _, item_service, repository = _build_services(tmp_path)
    artifact = tmp_path / "artifact.rifflock"
    artifact.write_bytes(b"keep-me")
    source = tmp_path / "source.txt"
    source.write_text("keep-me-too", encoding="utf-8")

    saved = item_service.create_item(
        item_type="file",
        source_path=str(source),
        artifact_path=str(artifact),
        file_size=8,
    )

    removed = item_service.remove_metadata(saved.id)

    assert removed is True
    assert repository.get_by_id(saved.id) is None
    assert artifact.exists()
    assert source.exists()


def test_missing_protected_file_status_detection(tmp_path: Path) -> None:
    protect_service, item_service, repository = _build_services(tmp_path)
    source = tmp_path / "source.txt"
    source.write_text("track", encoding="utf-8")
    protected = protect_service.protect_file(source, b"x" * 32)

    protected.output_path.unlink()
    updated = item_service.refresh_missing_status(protected.protected_item.id)
    stored = repository.get_by_id(protected.protected_item.id)

    assert updated.status == STATUS_MISSING_PROTECTED
    assert stored is not None
    assert stored.status == STATUS_MISSING_PROTECTED


def _build_services(tmp_path: Path):
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)
    repository = ProtectedItemRepository(database_path)
    return (
        FileProtectionService(repository, tmp_path / "temp"),
        ProtectedItemService(repository),
        repository,
    )
