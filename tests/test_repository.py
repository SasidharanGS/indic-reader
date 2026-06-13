import pytest

from app.store import repository as repo
from app.store.db import init_db


@pytest.fixture
def conn():
    connection = init_db(":memory:")
    try:
        yield connection
    finally:
        connection.close()


def test_book_crud(conn):
    book = repo.create_book(conn, "Ponniyin Selvan", lang="ta")
    assert book.id is not None
    assert book.title == "Ponniyin Selvan"
    assert book.lang == "ta"
    assert book.created_at  # set by SQLite default
    assert repo.get_book(conn, book.id).title == "Ponniyin Selvan"
    assert [b.id for b in repo.list_books(conn)] == [book.id]


def test_pages_auto_number_and_update(conn):
    book = repo.create_book(conn, "Book")
    p1 = repo.add_page(conn, book.id, image_path="p1.jpg")
    p2 = repo.add_page(conn, book.id, image_path="p2.jpg")
    assert (p1.page_no, p2.page_no) == (1, 2)

    updated = repo.set_page_result(conn, p1.id, text="hello", lang="en", status="done")
    assert updated.text == "hello"
    assert updated.status == "done"
    assert [p.page_no for p in repo.list_pages(conn, book.id)] == [1, 2]


def test_chunks_reading_order_across_pages(conn):
    book = repo.create_book(conn, "Book")
    p1 = repo.add_page(conn, book.id)
    p2 = repo.add_page(conn, book.id)
    # insert out of order; reading order must come from (page_no, idx)
    repo.add_chunk(conn, p2.id, idx=0, text="page2-c0")
    repo.add_chunk(conn, p1.id, idx=1, text="page1-c1")
    repo.add_chunk(conn, p1.id, idx=0, text="page1-c0")
    assert [c.text for c in repo.list_chunks_for_book(conn, book.id)] == [
        "page1-c0",
        "page1-c1",
        "page2-c0",
    ]


def test_find_chunk_by_hash(conn):
    book = repo.create_book(conn, "Book")
    page = repo.add_page(conn, book.id)
    assert repo.find_chunk_by_hash(conn, "abc") is None
    repo.add_chunk(conn, page.id, idx=0, text="t", audio_path="/a.wav", chunk_hash="abc")
    found = repo.find_chunk_by_hash(conn, "abc")
    assert found is not None
    assert found.audio_path == "/a.wav"


def test_playback_upsert_keeps_one_row(conn):
    book = repo.create_book(conn, "Book")
    page = repo.add_page(conn, book.id)
    chunk = repo.add_chunk(conn, page.id, idx=0, text="t")

    repo.save_playback(conn, book.id, chunk_id=None, offset_s=1.5)
    assert repo.get_playback(conn, book.id).offset_s == 1.5

    repo.save_playback(conn, book.id, chunk_id=chunk.id, offset_s=9.0)
    pb = repo.get_playback(conn, book.id)
    assert pb.offset_s == 9.0
    assert pb.chunk_id == chunk.id
    assert conn.execute("SELECT COUNT(*) FROM playback").fetchone()[0] == 1


def test_cascade_delete_removes_pages_and_chunks(conn):
    book = repo.create_book(conn, "Book")
    page = repo.add_page(conn, book.id)
    repo.add_chunk(conn, page.id, idx=0, text="t")
    conn.execute("DELETE FROM books WHERE id = ?", (book.id,))
    conn.commit()
    assert repo.list_pages(conn, book.id) == []
    assert conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 0
