"""Single-file protection service."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from rifflock.files.format import build_container
from rifflock.files.items import ProtectedItemService
from rifflock.models import ProtectedItemRecord
from rifflock.storage import ProtectedItemRepository
from rifflock.utils.errors import FileOperationError

FILE_ENCRYPTION_ALGORITHM = "AES-256-GCM"
FILE_NONCE_LENGTH = 12


@dataclass(frozen=True)
class FileProtectionResult:
    source_path: Path
    output_path: Path
    protected_item: ProtectedItemRecord


class FileProtectionService:
    """Encrypt a local file into a `.rifflock` artifact safely."""

    def __init__(
        self,
        protected_item_repository: ProtectedItemRepository,
        temp_dir: Path | str,
    ) -> None:
        self._protected_item_repository = protected_item_repository
        self._protected_item_service = ProtectedItemService(protected_item_repository)
        self._temp_dir = Path(temp_dir)

    def protect_file(
        self,
        source_path: Path | str,
        data_key: bytes,
        output_path: Path | str | None = None,
    ) -> FileProtectionResult:
        source = Path(source_path)
        if not source.exists() or not source.is_file():
            raise FileOperationError("The selected file could not be protected.")

        final_output = Path(output_path) if output_path is not None else source.with_suffix(source.suffix + ".rifflock")
        if final_output.exists():
            raise FileOperationError("The selected output file already exists.")

        original_bytes = source.read_bytes()
        nonce = os.urandom(FILE_NONCE_LENGTH)
        ciphertext = AESGCM(data_key).encrypt(nonce, original_bytes, None)
        container = build_container(
            metadata={
                "algorithm": FILE_ENCRYPTION_ALGORITHM,
                "nonce": base64.b64encode(nonce).decode("ascii"),
                "original_filename": source.name,
                "original_size": len(original_bytes),
            },
            payload=ciphertext,
        )

        self._temp_dir.mkdir(parents=True, exist_ok=True)
        temp_output = self._temp_dir / f"{uuid4().hex}.rifflock.tmp"

        try:
            temp_output.write_bytes(container)
            if final_output.exists():
                raise FileOperationError("The selected output file already exists.")
            temp_output.rename(final_output)
            protected_item = self._protected_item_service.create_item(
                item_type="file",
                source_path=str(source),
                artifact_path=str(final_output),
                file_size=len(original_bytes),
            )
        except Exception:
            if temp_output.exists():
                temp_output.unlink()
            raise

        return FileProtectionResult(
            source_path=source,
            output_path=final_output,
            protected_item=protected_item,
        )
