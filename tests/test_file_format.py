from __future__ import annotations

import pytest

from rifflock.files import RIFLOCK_MAGIC, RIFLOCK_VERSION, build_container, parse_container
from rifflock.utils.errors import FileOperationError


def test_valid_header_parsing() -> None:
    blob = build_container(
        metadata={
            "algorithm": "AES-256-GCM",
            "nonce": "bm9uY2U=",
            "original_filename": "notes.txt",
            "original_size": 128,
        },
        payload=b"ciphertext",
    )

    parsed = parse_container(blob)

    assert parsed.version == RIFLOCK_VERSION
    assert parsed.metadata["algorithm"] == "AES-256-GCM"
    assert parsed.payload == b"ciphertext"
    assert blob.startswith(RIFLOCK_MAGIC)


def test_invalid_header_rejection() -> None:
    blob = b"BADLOCK" + bytes([RIFLOCK_VERSION]) + (0).to_bytes(2, "big")

    with pytest.raises(FileOperationError):
        parse_container(blob)


def test_unsupported_version_rejection() -> None:
    metadata = b'{"algorithm":"AES-256-GCM","nonce":"bm9uY2U=","original_filename":"notes.txt","original_size":128}'
    blob = RIFLOCK_MAGIC + bytes([99]) + len(metadata).to_bytes(2, "big") + metadata + b"ciphertext"

    with pytest.raises(FileOperationError):
        parse_container(blob)
