from __future__ import annotations

from pathlib import Path

import pytest

from rifflock.files import FileProtectionService, FileRestoreService
from rifflock.storage import ProtectedItemRepository, initialize_database
from rifflock.utils.errors import FileOperationError


def test_restore_round_trip_returns_original_bytes(tmp_path: Path) -> None:
    protect_service, restore_service, _ = _build_services(tmp_path)
    source = tmp_path / "demo.txt"
    original_bytes = b"restore me exactly"
    source.write_bytes(original_bytes)

    protected = protect_service.protect_file(source, _data_key())
    restored_path = tmp_path / "restored.txt"
    result = restore_service.restore_file(protected.output_path, _data_key(), restored_path)

    assert result.restored_path.read_bytes() == original_bytes


def test_wrong_key_cannot_restore_file(tmp_path: Path) -> None:
    protect_service, restore_service, _ = _build_services(tmp_path)
    source = tmp_path / "wrong-key.txt"
    source.write_text("secret", encoding="utf-8")
    protected = protect_service.protect_file(source, _data_key())

    with pytest.raises(FileOperationError):
        restore_service.restore_file(protected.output_path, b"y" * 32, tmp_path / "wrong.txt")


def test_tampered_protected_file_cannot_be_restored(tmp_path: Path) -> None:
    protect_service, restore_service, _ = _build_services(tmp_path)
    source = tmp_path / "tamper.txt"
    source.write_text("tamper target", encoding="utf-8")
    protected = protect_service.protect_file(source, _data_key())

    tampered = bytearray(protected.output_path.read_bytes())
    tampered[-1] ^= 0x01
    protected.output_path.write_bytes(bytes(tampered))

    with pytest.raises(FileOperationError):
        restore_service.restore_file(protected.output_path, _data_key(), tmp_path / "tampered.txt")


def test_existing_output_is_not_overwritten_silently(tmp_path: Path) -> None:
    protect_service, restore_service, _ = _build_services(tmp_path)
    source = tmp_path / "existing.txt"
    source.write_text("hello", encoding="utf-8")
    protected = protect_service.protect_file(source, _data_key())
    output = tmp_path / "already-there.txt"
    output.write_text("existing", encoding="utf-8")

    with pytest.raises(FileOperationError):
        restore_service.restore_file(protected.output_path, _data_key(), output)

    assert output.read_text(encoding="utf-8") == "existing"


def test_failed_restore_does_not_leave_corrupted_final_file(tmp_path: Path) -> None:
    protect_service, restore_service, _ = _build_services(tmp_path)
    source = tmp_path / "corrupt.txt"
    source.write_text("content", encoding="utf-8")
    protected = protect_service.protect_file(source, _data_key())
    final_output = tmp_path / "final.txt"

    with pytest.raises(FileOperationError):
        restore_service.restore_file(protected.output_path, b"z" * 32, final_output)

    assert not final_output.exists()


def test_restore_updates_metadata_status_where_available(tmp_path: Path) -> None:
    protect_service, restore_service, repository = _build_services(tmp_path)
    source = tmp_path / "metadata.txt"
    source.write_text("track me", encoding="utf-8")
    protected = protect_service.protect_file(source, _data_key())

    result = restore_service.restore_file(
        protected.output_path,
        _data_key(),
        tmp_path / "metadata-restored.txt",
    )

    assert result.protected_item is not None
    stored = repository.get_by_id(result.protected_item.id)
    assert stored is not None
    assert stored.status == "restored"


def _build_services(tmp_path: Path):
    database_path = tmp_path / "data" / "rifflock.db"
    initialize_database(database_path)
    repository = ProtectedItemRepository(database_path)
    temp_dir = tmp_path / "temp"
    return (
        FileProtectionService(repository, temp_dir),
        FileRestoreService(repository, temp_dir),
        repository,
    )


def _data_key() -> bytes:
    return b"x" * 32
