"""Book service: capture pages into a book, process them, persist chunks + audio.

Second piece of M3. Ties the persistence layer (:mod:`app.store.repository`) to
the providers and text pipeline, and caches each synthesized chunk on disk
(``data/audio_cache/<hash>.wav``) so audio survives restarts and is reused across
pages and books.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.audio.cache import chunk_key
from app.audio.wav import to_wav_bytes
from app.config import Settings, get_settings
from app.providers.ocr.base import OCRProvider
from app.providers.registry import get_ocr_provider, get_tts_provider
from app.providers.tts.base import TTSProvider
from app.store import repository as repo
from app.store.models import Book, Page
from app.text import DEFAULT_MAX_CHARS, chunk, clean, detect_lang, normalize


class BookService:
    """Create books and process captured pages into stored, synthesized chunks."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        ocr: OCRProvider | None = None,
        tts: TTSProvider | None = None,
        settings: Settings | None = None,
        data_dir: str | Path = "data",
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> None:
        self.conn = conn
        self.settings = settings or get_settings()
        self.ocr = ocr or get_ocr_provider(settings=self.settings)
        self.tts = tts or get_tts_provider(settings=self.settings)
        self.data_dir = Path(data_dir)
        self.audio_dir = self.data_dir / "audio_cache"
        self.pages_dir = self.data_dir / "pages"
        self.max_chars = max_chars

    def create_book(self, title: str, lang: str | None = None) -> Book:
        return repo.create_book(self.conn, title, lang=lang)

    def add_page(
        self,
        book_id: int,
        image: bytes,
        lang_hint: str | None = None,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> Page:
        """OCR, chunk, and synthesize one page; persist the page + its chunks."""
        page_no = repo.next_page_no(self.conn, book_id)
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        image_path = self.pages_dir / f"book{book_id}_page{page_no}.img"
        image_path.write_bytes(image)
        page = repo.add_page(
            self.conn, book_id, image_path=str(image_path), page_no=page_no, status="processing"
        )

        ocr_result = self.ocr.extract(image, lang_hint=lang_hint)
        cleaned = clean(ocr_result.text)
        lang = lang_hint or detect_lang(cleaned)
        text = normalize(cleaned, lang)
        pieces = chunk(text, max_chars=self.max_chars)
        repo.set_page_result(self.conn, page.id, text=text, lang=lang, status="done")

        backend = self.settings.tts_backend
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        for idx, piece in enumerate(pieces):
            audio_hash = chunk_key(piece, voice, backend, speed)
            audio_path = self._cached_audio_path(audio_hash)
            if audio_path is None:
                clip = self.tts.synthesize(piece, lang=lang, voice=voice, speed=speed)
                out = self.audio_dir / f"{audio_hash}.wav"
                out.write_bytes(to_wav_bytes(clip))
                audio_path = str(out)
            repo.add_chunk(
                self.conn,
                page.id,
                idx=idx,
                text=piece,
                audio_path=audio_path,
                voice=voice,
                backend=backend,
                chunk_hash=audio_hash,
            )

        result = repo.get_page(self.conn, page.id)
        assert result is not None
        return result

    def _cached_audio_path(self, audio_hash: str) -> str | None:
        """Return an existing on-disk clip for this hash, or None."""
        cached = repo.find_chunk_by_hash(self.conn, audio_hash)
        if cached and cached.audio_path and Path(cached.audio_path).exists():
            return cached.audio_path
        return None
