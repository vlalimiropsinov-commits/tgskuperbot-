# -*- coding: utf-8 -*-
"""Простое хранилище на SQLite: кто и когда был принят."""

import sqlite3
from datetime import datetime, timezone

_conn: sqlite3.Connection | None = None


def init(db_path: str) -> None:
    global _conn
    _conn = sqlite3.connect(db_path, check_same_thread=False)
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS approved (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            username   TEXT,
            full_name  TEXT,
            chat_id    INTEGER NOT NULL,
            chat_title TEXT,
            status     TEXT NOT NULL DEFAULT 'approved',
            created_at TEXT NOT NULL
        )
        """
    )
    _conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_approved_chat ON approved(chat_id)"
    )
    _conn.commit()


def log_request(
    user_id: int,
    username: str | None,
    full_name: str,
    chat_id: int,
    chat_title: str,
    status: str = "approved",
) -> None:
    if _conn is None:
        return
    _conn.execute(
        "INSERT INTO approved (user_id, username, full_name, chat_id, chat_title, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            username,
            full_name,
            chat_id,
            chat_title,
            status,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    _conn.commit()


def total(status: str = "approved") -> int:
    if _conn is None:
        return 0
    row = _conn.execute(
        "SELECT COUNT(*) FROM approved WHERE status = ?", (status,)
    ).fetchone()
    return row[0] if row else 0


def today(status: str = "approved") -> int:
    if _conn is None:
        return 0
    prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = _conn.execute(
        "SELECT COUNT(*) FROM approved WHERE status = ? AND created_at LIKE ?",
        (status, prefix + "%"),
    ).fetchone()
    return row[0] if row else 0


def by_chat(limit: int = 10) -> list[tuple[str, int]]:
    if _conn is None:
        return []
    rows = _conn.execute(
        "SELECT COALESCE(chat_title, chat_id), COUNT(*) c FROM approved"
        " WHERE status = 'approved' GROUP BY chat_id ORDER BY c DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [(str(r[0]), int(r[1])) for r in rows]


def close() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
