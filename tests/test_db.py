from app.store.db import init_db

EXPECTED_TABLES = {"books", "pages", "chunks", "playback"}


def _table_names(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def test_schema_created_in_memory():
    conn = init_db(":memory:")
    try:
        assert EXPECTED_TABLES <= _table_names(conn)
    finally:
        conn.close()


def test_init_is_idempotent(tmp_path):
    db = tmp_path / "indic_reader.sqlite3"
    init_db(db).close()
    conn = init_db(db)  # second call must not raise
    try:
        assert EXPECTED_TABLES <= _table_names(conn)
    finally:
        conn.close()


def test_creates_parent_directory(tmp_path):
    db = tmp_path / "nested" / "dir" / "db.sqlite3"
    conn = init_db(db)
    try:
        assert db.exists()
    finally:
        conn.close()
