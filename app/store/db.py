"""SQLite initialization and connections (ARCHITECTURE.md §8)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data/indic_reader.sqlite3")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    lang       TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id    INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    page_no    INTEGER NOT NULL,
    image_path TEXT,
    text       TEXT,
    lang       TEXT,
    status     TEXT NOT NULL DEFAULT 'pending',
    UNIQUE (book_id, page_no)
);

CREATE TABLE IF NOT EXISTS chunks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id    INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    idx        INTEGER NOT NULL,
    text       TEXT NOT NULL,
    audio_path TEXT,
    voice      TEXT,
    backend    TEXT,
    hash       TEXT
);

CREATE TABLE IF NOT EXISTS playback (
    book_id    INTEGER PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
    chunk_id   INTEGER REFERENCES chunks(id),
    offset_s   REAL NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection, creating parent dirs and enabling foreign keys."""
    path = Path(db_path)
    if str(path) != ":memory:" and path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create the schema if absent and return an open connection. Idempotent."""
    conn = connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
