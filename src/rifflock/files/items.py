"""Protected item repository helpers and status management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rifflock.models import ProtectedItemRecord
from rifflock.storage import ProtectedItemRepository
from rifflock.utils.errors import FileOperationError

STATUS_PROTECTED = "protected"
STATUS_RESTORED = "restored"
STATUS_MISSING_SOURCE = "missing_source"
STATUS_MISSING_PROTECTED = "missing_protected"
STATUS_ERROR = "error"

VALID_PROTECTED_ITEM_STATUSES = {
    STATUS_PROTECTED,
    STATUS_RESTORED,
    STATUS_MISSING_SOURCE,
    STATUS_MISSING_PROTECTED,
    STATUS_ERROR,
}


@dataclass(frozen=True)
class ProtectedItemView:
    record: ProtectedItemRecord
    source_exists: bool
    protected_exists: bool


class ProtectedItemService:
    """High-level protected-item listing and status operations."""

    def __init__(self, repository: ProtectedItemRepository) -> None:
        self._repository = repository

    def create_item(
        self,
        *,
        item_type: str,
        source_path: str,
        artifact_path: str,
        file_size: int | None,
        status: str = STATUS_PROTECTED,
    ) -> ProtectedItemRecord:
        self._validate_status(status)
        timestamp = _utc_now()
        return self._repository.save(
            ProtectedItemRecord(
                id=None,
                item_type=item_type,
                source_path=source_path,
                artifact_path=artifact_path,
                status=status,
                file_size=file_size,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )

    def list_items(self) -> list[ProtectedItemView]:
        items = self._repository.list_all()
        return [self._build_view(item) for item in items]

    def update_status(self, record_id: int, status: str) -> ProtectedItemRecord:
        self._validate_status(status)
        existing = self._repository.get_by_id(record_id)
        if existing is None:
            raise FileOperationError("The protected item metadata could not be updated.")

        return self._repository.save(
            ProtectedItemRecord(
                id=existing.id,
                item_type=existing.item_type,
                source_path=existing.source_path,
                artifact_path=existing.artifact_path,
                status=status,
                file_size=existing.file_size,
                created_at=existing.created_at,
                updated_at=_utc_now(),
            )
        )

    def refresh_missing_status(self, record_id: int) -> ProtectedItemRecord:
        existing = self._repository.get_by_id(record_id)
        if existing is None:
            raise FileOperationError("The protected item metadata could not be updated.")

        source_exists = Path(existing.source_path).exists()
        protected_exists = Path(existing.artifact_path).exists()

        if not protected_exists:
            new_status = STATUS_MISSING_PROTECTED
        elif not source_exists:
            new_status = STATUS_MISSING_SOURCE
        else:
            new_status = existing.status

        if new_status == existing.status:
            return existing

        return self.update_status(existing.id, new_status)

    def remove_metadata(self, record_id: int) -> bool:
        return self._repository.delete(record_id)

    def _build_view(self, record: ProtectedItemRecord) -> ProtectedItemView:
        return ProtectedItemView(
            record=record,
            source_exists=Path(record.source_path).exists(),
            protected_exists=Path(record.artifact_path).exists(),
        )

    def _validate_status(self, status: str) -> None:
        if status not in VALID_PROTECTED_ITEM_STATUSES:
            raise FileOperationError("The protected item metadata could not be updated.")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
