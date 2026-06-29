from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class UserRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    totp_secret_encrypted TEXT,
                    totp_enabled INTEGER NOT NULL DEFAULT 0,
                    totp_configured_at TEXT,
                    last_totp_counter INTEGER,
                    auth_version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )

    def create_demo_user(self, username: str, password_hash: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO users (username, password_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (username, password_hash, datetime.now(UTC).isoformat()),
            )

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        return dict(row) if row else None

    def set_pending_secret(self, username: str, encrypted_secret: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET totp_secret_encrypted = ?, totp_enabled = 0,
                    totp_configured_at = NULL, last_totp_counter = NULL
                WHERE username = ?
                """,
                (encrypted_secret, username),
            )

    def enable_totp(self, username: str, counter: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET totp_enabled = 1, totp_configured_at = ?, last_totp_counter = ?
                WHERE username = ?
                """,
                (datetime.now(UTC).isoformat(), counter, username),
            )

    def update_last_counter(self, username: str, counter: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET last_totp_counter = ? WHERE username = ?",
                (counter, username),
            )

    def reset_totp(self, username: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE users
                SET totp_secret_encrypted = NULL, totp_enabled = 0,
                    totp_configured_at = NULL, last_totp_counter = NULL,
                    auth_version = auth_version + 1
                WHERE username = ?
                """,
                (username,),
            )
        return cursor.rowcount == 1

