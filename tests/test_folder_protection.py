from __future__ import annotations

from pathlib import Path

from rifflock.files import FolderProtectionService
from rifflock.storage import ProtectedItemRepository, initialize_database
from rifflock.utils.errors import FileOperationError


def test_folder_protection_recurses_and_stores_folder_metadata(tmp_path: Path) -> None:
    service, repository = _build_service(tmp_path)
    source = tmp_path / "source"
    (source / "nested").mkdir(parents=True)
    (source / "root.txt").write_text("root", encoding="utf-8")
    (source / "nested" / "child.txt").write_text("child", encoding="utf-8")

    result = service.protect_folder(source, _data_key())

    assert result.protected_count == 2
    assert result.skipped_count == 0
    assert result.failed_count == 0
    assert (result.output_path / "root.txt.rifflock").exists()
    assert (result.output_path / "nested" / "child.txt.rifflock").exists()
    stored = repository.list_all()
    assert len(stored) == 3
    assert stored[-1].item_type == "folder"
    assert stored[-1].artifact_path == str(result.output_path)


def test_folder_structure_preservation_and_empty_directories(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    source = tmp_path / "album"
    (source / "disc1" / "live").mkdir(parents=True)
    (source / "disc2").mkdir(parents=True)
    (source / "disc1" / "live" / "take.wav").write_text("audio", encoding="utf-8")

    result = service.protect_folder(source, _data_key())

    assert (result.output_path / "disc1" / "live" / "take.wav.rifflock").exists()
    assert (result.output_path / "disc2").is_dir()


def test_empty_folder_behavior_returns_zero_counts(tmp_path: Path) -> None:
    service, repository = _build_service(tmp_path)
    source = tmp_path / "empty-folder"
    (source / "subdir").mkdir(parents=True)

    result = service.protect_folder(source, _data_key())

    assert result.protected_count == 0
    assert result.skipped_count == 0
    assert result.failed_count == 0
    assert result.folder_item.item_type == "folder"
    assert repository.get_by_artifact_path(str(result.output_path)) == result.folder_item


def test_partial_failure_does_not_stop_other_files(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    (source / "good.txt").write_text("good", encoding="utf-8")
    (source / "conflict.txt").write_text("conflict", encoding="utf-8")
    output = tmp_path / "protected"
    output.mkdir()
    (output / "conflict.txt.rifflock").write_text("existing", encoding="utf-8")

    result = service.protect_folder(source, _data_key(), output_path=output)

    assert result.protected_count == 1
    assert result.failed_count == 1
    assert (output / "good.txt.rifflock").exists()
    assert (source / "good.txt").exists()
    assert (source / "conflict.txt").exists()
    assert result.failed_files[0].path == Path("conflict.txt")
    assert result.failed_files[0].reason == "The selected output file already exists."


def test_skipped_file_reporting_for_temporary_files(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    (source / "keep.txt").write_text("keep", encoding="utf-8")
    (source / "skip.tmp").write_text("skip", encoding="utf-8")
    (source / "~$scratch.txt").write_text("scratch", encoding="utf-8")

    result = service.protect_folder(source, _data_key())

    assert result.protected_count == 1
    assert result.skipped_count == 2
    assert sorted(item.path for item in result.skipped_files) == [
        Path("skip.tmp"),
        Path("~$scratch.txt"),
    ]


def test_invalid_source_folder_is_rejected(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)

    try:
        service.protect_folder(tmp_path / "missing", _data_key())
    except FileOperationError as error:
        assert error.user_message == "The selected folder could not be protected."
    else:
        raise AssertionError("Expected FileOperationError for missing folder.")


def _build_service(tmp_path: Path) -> tuple[FolderProtectionService, ProtectedItemRepository]:
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)
    repository = ProtectedItemRepository(database_path)
    return (
        FolderProtectionService(
            protected_item_repository=repository,
            temp_dir=tmp_path / "temp",
        ),
        repository,
    )


def _data_key() -> bytes:
    return b"x" * 32
