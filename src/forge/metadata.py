from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import ensure_dirs, get_db_path
from .fingerprint import PackageFingerprint


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    ensure_dirs()
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            python_version TEXT NOT NULL,
            python_tag TEXT NOT NULL,
            abi_tag TEXT NOT NULL,
            platform TEXT NOT NULL,
            accelerator TEXT NOT NULL,
            path TEXT NOT NULL,
            ref_count INTEGER NOT NULL DEFAULT 0,
            UNIQUE (
                name, version, python_version, python_tag, abi_tag,
                platform, accelerator
            )
        )
        """
    )
    conn.commit()


def register_package(
    conn: sqlite3.Connection,
    fingerprint: PackageFingerprint,
    path: Path,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO packages (
            name, version, python_version, python_tag, abi_tag,
            platform, accelerator, path, ref_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            fingerprint.name,
            fingerprint.version,
            fingerprint.python_version,
            fingerprint.python_tag,
            fingerprint.abi_tag,
            fingerprint.platform,
            fingerprint.accelerator,
            str(path),
        ),
    )
    conn.commit()


def get_package(
    conn: sqlite3.Connection,
    fingerprint: PackageFingerprint,
) -> sqlite3.Row | None:
    cursor = conn.execute(
        """
        SELECT *
        FROM packages
        WHERE name = ?
          AND version = ?
          AND python_version = ?
          AND python_tag = ?
          AND abi_tag = ?
          AND platform = ?
          AND accelerator = ?
        LIMIT 1
        """,
        (
            fingerprint.name,
            fingerprint.version,
            fingerprint.python_version,
            fingerprint.python_tag,
            fingerprint.abi_tag,
            fingerprint.platform,
            fingerprint.accelerator,
        ),
    )
    return cursor.fetchone()


def list_packages(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    cursor = conn.execute("SELECT * FROM packages ORDER BY name, version")
    return cursor.fetchall()


def increment_ref_count(conn: sqlite3.Connection, path: Path) -> None:
    conn.execute(
        "UPDATE packages SET ref_count = ref_count + 1 WHERE path = ?",
        (str(path),),
    )
    conn.commit()


def decrement_ref_count(conn: sqlite3.Connection, path: Path) -> None:
    conn.execute(
        """
        UPDATE packages
        SET ref_count = CASE WHEN ref_count > 0 THEN ref_count - 1 ELSE 0 END
        WHERE path = ?
        """,
        (str(path),),
    )
    conn.commit()
