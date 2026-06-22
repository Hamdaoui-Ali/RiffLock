"""Recursive folder protection service built on the single-file pipeline."""

from __future__ import annotations

import stat
import os
from dataclasses import dataclass
from pathlib import Path

from rifflock.files.items import ProtectedItemService
from rifflock.files.protect import FileProtectionResult, FileProtectionService
from rifflock.models import ProtectedItemRecord
from rifflock.storage import ProtectedItemRepository
from rifflock.utils.errors import FileOperationError

TEMPORARY_FILE_SUFFIXES = {".tmp", ".temp"}
TEMPORARY_FILE_PREFIXES = ("~$",)
WINDOWS_HIDDEN_FLAG = getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0)
WINDOWS_SYSTEM_FLAG = getattr(stat, "FILE_ATTRIBUTE_SYSTEM", 0)


@dataclass(frozen=True)
class SkippedFolderItem:
    path: Path
    reason: str


@dataclass(frozen=True)
class FailedFolderItem:
    path: Path
    reason: str


@dataclass(frozen=True)
class FolderProtectionResult:
    source_path: Path
    output_path: Path
    folder_item: ProtectedItemRecord
    protected_files: list[FileProtectionResult]
    skipped_files: list[SkippedFolderItem]
    failed_files: list[FailedFolderItem]

    @property
    def protected_count(self) -> int:
        return len(self.protected_files)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped_files)

    @property
    def failed_count(self) -> int:
        return len(self.failed_files)


class FolderProtectionService:
    """Protect a folder recursively without deleting the source tree."""

    def __init__(
        self,
        protected_item_repository: ProtectedItemRepository,
        temp_dir: Path | str,
    ) -> None:
        self._protected_item_service = ProtectedItemService(protected_item_repository)
        self._file_protection_service = FileProtectionService(
            protected_item_repository=protected_item_repository,
            temp_dir=temp_dir,
        )

    def protect_folder(
        self,
        source_path: Path | str,
        data_key: bytes,
        output_path: Path | str | None = None,
    ) -> FolderProtectionResult:
        source = Path(source_path)
        if not source.exists() or not source.is_dir():
            raise FileOperationError("The selected folder could not be protected.")

        final_output = (
            Path(output_path)
            if output_path is not None
            else source.parent / f"{source.name}.rifflock"
        )
        final_output.mkdir(parents=True, exist_ok=True)

        protected_files: list[FileProtectionResult] = []
        skipped_files: list[SkippedFolderItem] = []
        failed_files: list[FailedFolderItem] = []

        for current_root, _, file_names in self._walk_source(source):
            current_path = Path(current_root)
            relative_dir = current_path.relative_to(source)
            target_dir = final_output / relative_dir
            target_dir.mkdir(parents=True, exist_ok=True)

            for file_name in sorted(file_names):
                source_file = current_path / file_name
                relative_file = source_file.relative_to(source)
                if self._should_skip_file(source_file):
                    skipped_files.append(
                        SkippedFolderItem(
                            path=relative_file,
                            reason="Skipped temporary or system file.",
                        )
                    )
                    continue

                target_file = target_dir / f"{source_file.name}.rifflock"
                try:
                    protected_files.append(
                        self._file_protection_service.protect_file(
                            source_path=source_file,
                            data_key=data_key,
                            output_path=target_file,
                        )
                    )
                except Exception as error:
                    failed_files.append(
                        FailedFolderItem(
                            path=relative_file,
                            reason=self._to_failure_reason(error),
                        )
                    )

        folder_item = self._protected_item_service.create_item(
            item_type="folder",
            source_path=str(source),
            artifact_path=str(final_output),
            file_size=None,
        )
        return FolderProtectionResult(
            source_path=source,
            output_path=final_output,
            folder_item=folder_item,
            protected_files=protected_files,
            skipped_files=skipped_files,
            failed_files=failed_files,
        )

    def _walk_source(self, source: Path):
        return os.walk(source)

    def _should_skip_file(self, path: Path) -> bool:
        name = path.name.lower()
        if name.startswith(TEMPORARY_FILE_PREFIXES):
            return True
        if path.suffix.lower() in TEMPORARY_FILE_SUFFIXES:
            return True

        file_attributes = getattr(path.stat(), "st_file_attributes", 0)
        return bool(file_attributes & (WINDOWS_HIDDEN_FLAG | WINDOWS_SYSTEM_FLAG))

    def _to_failure_reason(self, error: Exception) -> str:
        if isinstance(error, FileOperationError):
            return error.user_message
        return "The file could not be protected."
