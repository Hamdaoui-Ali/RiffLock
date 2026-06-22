from __future__ import annotations

from pathlib import Path

import pytest

from rifflock.files import FileProtectionService, parse_container
from rifflock.storage import ProtectedItemRepository, create_connection, initialize_database
from rifflock.utils.errors import FileOperationError


def test_protected_output_is_created_with_rifflock_content(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    source = tmp_path / "demo.txt"
    source.write_text("hello world", encoding="utf-8")

    result = service.protect_file(source, _data_key())

    assert result.output_path.suffix == ".rifflock"
    assert result.output_path.exists()
    assert result.output_path.read_bytes() != source.read_bytes()
    parsed = parse_container(result.output_path.read_bytes())
    assert parsed.metadata["original_filename"] == "demo.txt"
    assert parsed.metadata["original_size"] == len(source.read_bytes())


def test_integration_metadata_is_saved(tmp_path: Path) -> None:
    database_path = _database_path(tmp_path)
    initialize_database(database_path)
    service = FileProtectionService(
        protected_item_repository=ProtectedItemRepository(database_path),
        temp_dir=tmp_path / "temp",
    )
    source = tmp_path / "notes.txt"
    source.write_text("protected text", encoding="utf-8")

    result = service.protect_file(source, _data_key())

    stored = ProtectedItemRepository(database_path).get_by_id(result.protected_item.id)
    assert stored is not None
    assert stored.source_path == str(source)
    assert stored.artifact_path == str(result.output_path)
    assert stored.status == "protected"


def test_same_file_protected_twice_produces_different_output(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    source = tmp_path / "repeat.txt"
    source.write_text("same content", encoding="utf-8")

    first_output = tmp_path / "first.rifflock"
    second_output = tmp_path / "second.rifflock"
    first = service.protect_file(source, _data_key(), output_path=first_output)
    second = service.protect_file(source, _data_key(), output_path=second_output)

    assert first.output_path.read_bytes() != second.output_path.read_bytes()


def test_original_file_remains_unchanged(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    source = tmp_path / "original.txt"
    original_text = "leave me alone"
    source.write_text(original_text, encoding="utf-8")

    service.protect_file(source, _data_key())

    assert source.read_text(encoding="utf-8") == original_text


def test_existing_output_is_not_overwritten_silently(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    source = tmp_path / "demo.txt"
    source.write_text("secret", encoding="utf-8")
    output = tmp_path / "existing.rifflock"
    output.write_bytes(b"existing-data")

    with pytest.raises(FileOperationError):
        service.protect_file(source, _data_key(), output_path=output)

    assert output.read_bytes() == b"existing-data"


def _build_service(tmp_path: Path) -> FileProtectionService:
    database_path = _database_path(tmp_path)
    initialize_database(database_path)
    return FileProtectionService(
        protected_item_repository=ProtectedItemRepository(database_path),
        temp_dir=tmp_path / "temp",
    )


def _database_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "rifflock.db"


def _data_key() -> bytes:
    return b"x" * 32
