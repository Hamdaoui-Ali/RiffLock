# RiffLock File Format

Last updated: 2026-06-22
Source issue: `HAM-114` / `RLD-010`

## Purpose

This document defines the v1 `.rifflock` protected file format.

The format must remain stable enough for future restore support even if application internals evolve.

## Goals

- identify valid `.rifflock` artifacts quickly
- reject malformed or unsupported files safely
- preserve enough metadata to restore the original file later
- separate format metadata from encrypted payload bytes

## v1 Binary Layout

The `.rifflock` v1 layout is:

```text
Offset  Size  Field
0       8     magic header: ASCII `RIFLOCK`
8       1     format version: unsigned byte, value `1`
9       2     metadata length: unsigned big-endian integer
11      N     metadata JSON encoded as UTF-8
11+N    M     encrypted payload bytes
```

## Required Metadata Fields

The metadata JSON object must include:

- `algorithm`: file encryption algorithm identifier
- `nonce`: base64-encoded nonce used for payload encryption
- `original_filename`: original source filename
- `original_size`: original plaintext file size in bytes

The v1 implementation uses:

- `algorithm`: `AES-256-GCM`

Optional future-safe fields may be added, but v1 readers only require the fields above.

## Example Metadata

```json
{
  "algorithm": "AES-256-GCM",
  "nonce": "c29tZS1iYXNlNjQtbm9uY2U=",
  "original_filename": "notes.txt",
  "original_size": 128
}
```

## Validation Rules

Readers must reject a file when:

- the magic header is not exactly `RIFLOCK`
- the format version is unsupported
- the metadata length is inconsistent with the available bytes
- the metadata JSON is invalid
- required metadata fields are missing

## Compatibility Rules

- v1 readers support only version `1`
- future version values must be rejected explicitly
- restore logic must validate the format before attempting decryption

## Notes

- The payload remains opaque to the format layer
- The nonce is stored in metadata for v1 simplicity
- The data key is never stored inside the `.rifflock` file
