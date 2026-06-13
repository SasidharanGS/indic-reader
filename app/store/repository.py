"""CRUD over the SQLite schema (ARCHITECTURE.md §8).

Thin functional repository: each call takes an open ``sqlite3.Connection`` (from
:func:`app.store.db.init_db`) and returns the typed dataclasses in
:mod:`app.store.models`. Writes commit immediately.
"""

from __future__ import annotations

import sqlite3

from app.store.models import Book, Chunk, Page, Playback


def _book(row: sqlite3.Row) -> Book:
    return Book(id=row["id"], title=row["title"], lang=row["lang"], created_at=row["created_at"])


def _page(row: sqlite3.Row) -> Page:
    return Page(
        id=row["id"],
        book_id=row["book_id"],
        page_no=row["page_no"],
        image_path=row["image_path"],
        text=row["text"],
        lang=row["lang"],
        status=row["status"],
    )


def _chunk(row: sqlite3.Row) -> Chunk:
    return Chunk(
        id=row["id"],
        page_id=row["page_id"],
        idx=row["idx"],
        text=row["text"],
        audio_path=row["audio_path"],
        voice=row["voice"],
        backend=row["backend"],
        hash=row["hash"],
    )


def _playback(row: sqlite3.Row) -> Playback:
    return Playback(
        book_id=row["book_id"],
        chunk_id=row["chunk_id"],
        offset_s=row["offset_s"],
        updated_at=row["updated_at"],
    )


# --- books -----------------------------------------------------------------


def create_book(conn: sqlite3.Connection, title: str, lang: str | None = None) -> Book:
    cur = conn.execute("INSERT INTO books (title, lang) VALUES (?, ?)", (title, lang))
    conn.commit()
    book = get_book(conn, cur.lastrowid)
    assert book is not None
    return book


def get_book(conn: sqlite3.Connection, book_id: int) -> Book | None:
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return _book(row) if row else None


def list_books(conn: sqlite3.Connection) -> list[Book]:
    rows = conn.execute("SELECT * FROM books ORDER BY created_at, id").fetchall()
    return [_book(row) for row in rows]


# --- pages -----------------------------------------------------------------


def next_page_no(conn: sqlite3.Connection, book_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(page_no), 0) + 1 AS n FROM pages WHERE book_id = ?", (book_id,)
    ).fetchone()
    return int(row["n"])


def add_page(
    conn: sqlite3.Connection,
    book_id: int,
    image_path: str | None = None,
    page_no: int | None = None,
    text: str | None = None,
    lang: str | None = None,
    status: str = "pending",
) -> Page:
    if page_no is None:
        page_no = next_page_no(conn, book_id)
    cur = conn.execute(
        "INSERT INTO pages (book_id, page_no, image_path, text, lang, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (book_id, page_no, image_path, text, lang, status),
    )
    conn.commit()
    page = get_page(conn, cur.lastrowid)
    assert page is not None
    return page


def get_page(conn: sqlite3.Connection, page_id: int) -> Page | None:
    row = conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
    return _page(row) if row else None


def list_pages(conn: sqlite3.Connection, book_id: int) -> list[Page]:
    rows = conn.execute(
        "SELECT * FROM pages WHERE book_id = ? ORDER BY page_no", (book_id,)
    ).fetchall()
    return [_page(row) for row in rows]


def set_page_result(
    conn: sqlite3.Connection,
    page_id: int,
    text: str,
    lang: str | None = None,
    status: str = "done",
) -> Page:
    conn.execute(
        "UPDATE pages SET text = ?, lang = ?, status = ? WHERE id = ?",
        (text, lang, status, page_id),
    )
    conn.commit()
    page = get_page(conn, page_id)
    assert page is not None
    return page


# --- chunks ----------------------------------------------------------------


def add_chunk(
    conn: sqlite3.Connection,
    page_id: int,
    idx: int,
    text: str,
    audio_path: str | None = None,
    voice: str | None = None,
    backend: str | None = None,
    chunk_hash: str | None = None,
) -> Chunk:
    cur = conn.execute(
        "INSERT INTO chunks (page_id, idx, text, audio_path, voice, backend, hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (page_id, idx, text, audio_path, voice, backend, chunk_hash),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM chunks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _chunk(row)


def list_chunks_for_book(conn: sqlite3.Connection, book_id: int) -> list[Chunk]:
    """Chunks in reading order across the book (page_no, then chunk idx)."""
    rows = conn.execute(
        """
        SELECT c.* FROM chunks c
        JOIN pages p ON p.id = c.page_id
        WHERE p.book_id = ?
        ORDER BY p.page_no, c.idx
        """,
        (book_id,),
    ).fetchall()
    return [_chunk(row) for row in rows]


def find_chunk_by_hash(conn: sqlite3.Connection, chunk_hash: str) -> Chunk | None:
    """Return a previously synthesized chunk with this hash (audio-cache reuse)."""
    row = conn.execute(
        "SELECT * FROM chunks WHERE hash = ? AND audio_path IS NOT NULL LIMIT 1",
        (chunk_hash,),
    ).fetchone()
    return _chunk(row) if row else None


def get_chunk(conn: sqlite3.Connection, chunk_id: int) -> Chunk | None:
    row = conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
    return _chunk(row) if row else None


def list_chunks_for_page(conn: sqlite3.Connection, page_id: int) -> list[Chunk]:
    rows = conn.execute(
        "SELECT * FROM chunks WHERE page_id = ? ORDER BY idx", (page_id,)
    ).fetchall()
    return [_chunk(row) for row in rows]


# --- playback --------------------------------------------------------------


def save_playback(
    conn: sqlite3.Connection,
    book_id: int,
    chunk_id: int | None = None,
    offset_s: float = 0.0,
) -> Playback:
    conn.execute(
        """
        INSERT INTO playback (book_id, chunk_id, offset_s, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(book_id) DO UPDATE SET
            chunk_id = excluded.chunk_id,
            offset_s = excluded.offset_s,
            updated_at = datetime('now')
        """,
        (book_id, chunk_id, offset_s),
    )
    conn.commit()
    playback = get_playback(conn, book_id)
    assert playback is not None
    return playback


def get_playback(conn: sqlite3.Connection, book_id: int) -> Playback | None:
    row = conn.execute("SELECT * FROM playback WHERE book_id = ?", (book_id,)).fetchone()
    return _playback(row) if row else None
