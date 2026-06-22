"""Single-file restore service."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from rifflock.files.format import parse_container
from rifflock.files.items import STATUS_RESTORED, ProtectedItemService
from rifflock.models import ProtectedItemRecord
from rifflock.storage import ProtectedItemRepository
from rifflock.utils.errors import FileOperationError


@dataclass(frozen=True)
class FileRestoreResult:
    protected_path: Path
    restored_path: Path
    protected_item: ProtectedItemRecord | None


class FileRestoreService:
    """Restore a `.rifflock` artifact safely using the unlocked data key."""

    def __init__(
        self,
        protected_item_repository: ProtectedItemRepository,
        temp_dir: Path | str,
    ) -> None:
        self._protected_item_repository = protected_item_repository
        self._protected_item_service = ProtectedItemService(protected_item_repository)
        self._temp_dir = Path(temp_dir)

    def restore_file(
        self,
        protected_path: Path | str,
        data_key: bytes,
        output_path: Path | str | None = None,
    ) -> FileRestoreResult:
        protected = Path(protected_path)
        if not protected.exists() or not protected.is_file():
            raise FileOperationError("The selected .rifflock file could not be restored.")

        container = parse_container(protected.read_bytes())
        final_output = (
            Path(output_path)
            if output_path is not None
            else protected.with_name(str(container.metadata["original_filename"]))
        )
        if final_output.exists():
            raise FileOperationError("The selected output file already exists.")

        try:
            nonce = base64.b64decode(str(container.metadata["nonce"]))
            plaintext = AESGCM(data_key).decrypt(nonce, container.payload, None)
        except (ValueError, InvalidTag) as error:
            raise FileOperationError("The selected .rifflock file could not be restored.") from error

        self._temp_dir.mkdir(parents=True, exist_ok=True)
        temp_output = self._temp_dir / f"{uuid4().hex}.restore.tmp"

        try:
            temp_output.write_bytes(plaintext)
            if final_output.exists():
                raise FileOperationError("The selected output file already exists.")
            temp_output.rename(final_output)
            protected_item = self._update_metadata_after_restore(protected, final_output)
        except Exception:
            if temp_output.exists():
                temp_output.unlink()
            raise

        return FileRestoreResult(
            protected_path=protected,
            restored_path=final_output,
            protected_item=protected_item,
        )

    def _update_metadata_after_restore(
        self,
        protected_path: Path,
        restored_path: Path,
    ) -> ProtectedItemRecord | None:
        existing = self._protected_item_repository.get_by_artifact_path(str(protected_path))
        if existing is None:
            return None

        return self._protected_item_service.update_status(existing.id, STATUS_RESTORED)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
