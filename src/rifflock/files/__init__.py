"""File protection domain package."""

from rifflock.files.format import (
    RIFLOCK_MAGIC,
    RIFLOCK_VERSION,
    RiffLockContainer,
    build_container,
    parse_container,
)
from rifflock.files.folder import (
    FailedFolderItem,
    FolderProtectionResult,
    FolderProtectionService,
    SkippedFolderItem,
)
from rifflock.files.items import (
    STATUS_ERROR,
    STATUS_MISSING_PROTECTED,
    STATUS_MISSING_SOURCE,
    STATUS_PROTECTED,
    STATUS_RESTORED,
    ProtectedItemService,
    ProtectedItemView,
)
from rifflock.files.protect import (
    FILE_ENCRYPTION_ALGORITHM,
    FileProtectionResult,
    FileProtectionService,
)
from rifflock.files.restore import (
    DecryptedFileResult,
    FileRestoreResult,
    FileRestoreService,
    FileViewingResult,
)

__all__ = [
    "FILE_ENCRYPTION_ALGORITHM",
    "DecryptedFileResult",
    "FailedFolderItem",
    "FileProtectionResult",
    "FileProtectionService",
    "FileRestoreResult",
    "FileRestoreService",
    "FileViewingResult",
    "FolderProtectionResult",
    "FolderProtectionService",
    "ProtectedItemService",
    "ProtectedItemView",
    "RIFLOCK_MAGIC",
    "RIFLOCK_VERSION",
    "RiffLockContainer",
    "STATUS_ERROR",
    "STATUS_MISSING_PROTECTED",
    "STATUS_MISSING_SOURCE",
    "STATUS_PROTECTED",
    "STATUS_RESTORED",
    "SkippedFolderItem",
    "build_container",
    "parse_container",
]
