import pytest

from app.book import BookService
from app.config import Settings
from app.providers.ocr.base import Block, OCRResult
from app.providers.tts.mock import MockTTSProvider
from app.store.db import init_db

MOCK_SETTINGS = Settings(_env_file=None, ocr_backend="mock", tts_backend="mock")


class FakeOCR:
    def extract(self, image: bytes, lang_hint: str | None = None) -> OCRResult:
        return OCRResult(text="One. Two.", lang="en", confidence=1.0, blocks=[Block("One. Two.")])


@pytest.fixture
def conn():
    connection = init_db(":memory:")
    try:
        yield connection
    finally:
        connection.close()


def _service(conn, tmp_path):
    return BookService(
        conn,
        ocr=FakeOCR(),
        tts=MockTTSProvider(),
        settings=MOCK_SETTINGS,
        data_dir=tmp_path,
        max_chars=6,
    )


def test_play_next_walks_pages_in_order(conn, tmp_path):
    svc = _service(conn, tmp_path)
    book = svc.create_book("B")
    svc.add_page(book.id, b"a")
    svc.add_page(book.id, b"b")

    page1, wav1 = svc.play_next(book.id)
    assert page1.page_no == 1
    assert wav1 and wav1[:4] == b"RIFF"

    page2, _ = svc.play_next(book.id)
    assert page2.page_no == 2

    assert svc.play_next(book.id) is None  # past the last page


def test_resume_with_a_fresh_service_same_db(conn, tmp_path):
    svc = _service(conn, tmp_path)
    book = svc.create_book("B")
    svc.add_page(book.id, b"a")
    svc.add_page(book.id, b"b")
    svc.play_next(book.id)  # page 1 played, position saved

    resumed = _service(conn, tmp_path)  # new instance, same DB
    page, _ = resumed.play_next(book.id)
    assert page.page_no == 2


def test_restart_replays_from_first_page(conn, tmp_path):
    svc = _service(conn, tmp_path)
    book = svc.create_book("B")
    svc.add_page(book.id, b"a")
    svc.play_next(book.id)
    assert svc.play_next(book.id) is None  # one page; now at end

    svc.restart(book.id)
    page, _ = svc.play_next(book.id)
    assert page.page_no == 1


def test_render_page_audio_is_valid_wav(conn, tmp_path):
    svc = _service(conn, tmp_path)
    book = svc.create_book("B")
    page = svc.add_page(book.id, b"a")
    wav = svc.render_page_audio(page.id)
    assert wav and wav[:4] == b"RIFF" and wav[8:12] == b"WAVE"
