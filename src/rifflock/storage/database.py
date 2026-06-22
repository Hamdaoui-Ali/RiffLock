"""SQLite connection and schema initialization."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS owner_account (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        password_policy_version INTEGER NOT NULL,
        riff_2fa_enabled INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS key_vault (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_account_id INTEGER NOT NULL UNIQUE,
        vault_version INTEGER NOT NULL,
        encryption_algorithm TEXT NOT NULL,
        kdf_algorithm TEXT NOT NULL,
        kdf_parameters TEXT NOT NULL,
        salt BLOB NOT NULL,
        nonce BLOB NOT NULL,
        ciphertext BLOB NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (owner_account_id) REFERENCES owner_account(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS riff_template (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_account_id INTEGER NOT NULL UNIQUE,
        template_version INTEGER NOT NULL,
        template_data BLOB NOT NULL,
        recording_count INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (owner_account_id) REFERENCES owner_account(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS protected_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_type TEXT NOT NULL,
        source_path TEXT NOT NULL,
        artifact_path TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL,
        file_size INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_type TEXT NOT NULL,
        identifier TEXT NOT NULL,
        was_successful INTEGER NOT NULL CHECK (was_successful IN (0, 1)),
        failure_reason TEXT,
        attempted_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS app_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT NOT NULL UNIQUE,
        setting_value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
)


def create_connection(database_path: Path | str) -> sqlite3.Connection:
    """Open a SQLite connection with the required connection settings."""

    connection = sqlite3.connect(Path(database_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path | str) -> None:
    """Create the SQLite database schema if it does not exist."""

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with create_connection(path) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        _apply_schema_migrations(connection)
        connection.commit()


def _apply_schema_migrations(connection: sqlite3.Connection) -> None:
    """Apply lightweight idempotent schema updates for local development."""

    key_vault_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(key_vault)").fetchall()
    }
    if "encryption_algorithm" not in key_vault_columns:
        connection.execute(
            """
            ALTER TABLE key_vault
            ADD COLUMN encryption_algorithm TEXT NOT NULL DEFAULT 'AES-256-GCM'
            """
        )

    owner_account_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(owner_account)").fetchall()
    }
    if "riff_2fa_enabled" not in owner_account_columns:
        connection.execute(
            """
            ALTER TABLE owner_account
            ADD COLUMN riff_2fa_enabled INTEGER NOT NULL DEFAULT 0
            """
        )
