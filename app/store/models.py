"""Typed representations of the SQLite rows (ARCHITECTURE.md §8).

These mirror the schema in :mod:`app.store.db` and give the rest of the app a
typed view of persisted state. Used by book mode (M3).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Book:
    title: str
    lang: str | None = None
    id: int | None = None
    created_at: str | None = None


@dataclass
class Page:
    book_id: int
    page_no: int
    image_path: str | None = None
    text: str | None = None
    lang: str | None = None
    status: str = "pending"
    id: int | None = None


@dataclass
class Chunk:
    page_id: int
    idx: int
    text: str
    audio_path: str | None = None
    voice: str | None = None
    backend: str | None = None
    hash: str | None = None
    id: int | None = None


@dataclass
class Playback:
    book_id: int
    chunk_id: int | None = None
    offset_s: float = 0.0
    updated_at: str | None = None
