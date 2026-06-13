from pathlib import Path

import pytest

from app.book import BookService
from app.config import Settings
from app.providers.ocr.base import Block, OCRResult
from app.providers.tts.base import Audio
from app.providers.tts.mock import MockTTSProvider
from app.store import repository as repo
from app.store.db import init_db

MOCK_SETTINGS = Settings(_env_file=None, ocr_backend="mock", tts_backend="mock")


class FakeOCR:
    def __init__(self, text: str) -> None:
        self.text = text

    def extract(self, image: bytes, lang_hint: str | None = None) -> OCRResult:
        return OCRResult(text=self.text, lang="en", confidence=1.0, blocks=[Block(self.text)])


class CountingTTS(MockTTSProvider):
    def __init__(self) -> None:
        self.calls = 0

    def synthesize(self, text, lang, voice=None, speed=1.0) -> Audio:
        self.calls += 1
        return super().synthesize(text, lang, voice=voice, speed=speed)


@pytest.fixture
def conn():
    connection = init_db(":memory:")
    try:
        yield connection
    finally:
        connection.close()


def _service(conn, tmp_path, tts=None):
    return BookService(
        conn,
        ocr=FakeOCR("One. Two."),
        tts=tts or CountingTTS(),
        settings=MOCK_SETTINGS,
        data_dir=tmp_path,
        max_chars=6,  # forces two chunks from "One. Two."
    )


def test_add_page_processes_and_persists(conn, tmp_path):
    svc = _service(conn, tmp_path)
    book = svc.create_book("My Book", lang="en")
    page = svc.add_page(book.id, b"image-bytes")

    assert page.status == "done"
    assert page.text
    assert page.image_path and Path(page.image_path).exists()

    chunks = repo.list_chunks_for_book(conn, book.id)
    assert len(chunks) == 2
    for c in chunks:
        assert c.hash
        assert c.audio_path and Path(c.audio_path).exists()


def test_add_page_reuses_cached_audio_by_hash(conn, tmp_path):
    tts = CountingTTS()
    svc = _service(conn, tmp_path, tts=tts)
    book = svc.create_book("My Book")

    svc.add_page(book.id, b"image-bytes")
    calls_after_first = tts.calls
    assert calls_after_first == 2  # two chunks synthesized

    svc.add_page(book.id, b"image-bytes")  # identical content
    assert tts.calls == calls_after_first  # reused cached audio, no re-synthesis


def test_pages_accumulate_in_a_book(conn, tmp_path):
    svc = _service(conn, tmp_path)
    book = svc.create_book("My Book")
    p1 = svc.add_page(book.id, b"img-a")
    p2 = svc.add_page(book.id, b"img-b")
    assert (p1.page_no, p2.page_no) == (1, 2)
    assert [p.page_no for p in repo.list_pages(conn, book.id)] == [1, 2]
