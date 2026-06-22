"""Definition and parsing for the `.rifflock` file format."""

from __future__ import annotations

import json
from dataclasses import dataclass

from rifflock.utils.errors import FileOperationError

RIFLOCK_MAGIC = b"RIFLOCK"
RIFLOCK_VERSION = 1
MAGIC_SIZE = len(RIFLOCK_MAGIC)
VERSION_SIZE = 1
METADATA_LENGTH_SIZE = 2
HEADER_SIZE = MAGIC_SIZE + VERSION_SIZE + METADATA_LENGTH_SIZE
REQUIRED_METADATA_FIELDS = {
    "algorithm",
    "nonce",
    "original_filename",
    "original_size",
}


@dataclass(frozen=True)
class RiffLockContainer:
    version: int
    metadata: dict[str, object]
    payload: bytes


def build_container(metadata: dict[str, object], payload: bytes) -> bytes:
    """Build a v1 `.rifflock` container from metadata and payload bytes."""

    _validate_metadata(metadata)
    metadata_bytes = json.dumps(
        metadata,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    metadata_length = len(metadata_bytes).to_bytes(METADATA_LENGTH_SIZE, byteorder="big")
    return RIFLOCK_MAGIC + bytes([RIFLOCK_VERSION]) + metadata_length + metadata_bytes + payload


def parse_container(blob: bytes) -> RiffLockContainer:
    """Parse and validate a `.rifflock` container."""

    if len(blob) < HEADER_SIZE:
        raise FileOperationError("The selected .rifflock file is invalid.")

    magic = blob[:MAGIC_SIZE]
    if magic != RIFLOCK_MAGIC:
        raise FileOperationError("The selected .rifflock file is invalid.")

    version = blob[MAGIC_SIZE]
    if version != RIFLOCK_VERSION:
        raise FileOperationError("This .rifflock file version is not supported.")

    metadata_length = int.from_bytes(
        blob[MAGIC_SIZE + VERSION_SIZE:HEADER_SIZE],
        byteorder="big",
    )
    metadata_end = HEADER_SIZE + metadata_length
    if metadata_end > len(blob):
        raise FileOperationError("The selected .rifflock file is invalid.")

    metadata_bytes = blob[HEADER_SIZE:metadata_end]
    try:
        metadata = json.loads(metadata_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FileOperationError("The selected .rifflock file is invalid.") from error

    _validate_metadata(metadata)
    payload = blob[metadata_end:]

    return RiffLockContainer(
        version=version,
        metadata=metadata,
        payload=payload,
    )


def _validate_metadata(metadata: object) -> None:
    if not isinstance(metadata, dict):
        raise FileOperationError("The selected .rifflock file is invalid.")

    missing_fields = REQUIRED_METADATA_FIELDS.difference(metadata.keys())
    if missing_fields:
        raise FileOperationError("The selected .rifflock file is invalid.")
