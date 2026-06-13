"""A deterministic OCR provider for tests and pipeline smoke runs."""

from __future__ import annotations

from app.providers.ocr.base import Block, OCRResult


class MockOCRProvider:
    """Returns fixed text without loading any model."""

    def extract(self, image: bytes, lang_hint: str | None = None) -> OCRResult:
        text = "mock ocr text"
        return OCRResult(
            text=text,
            lang=lang_hint or "en",
            confidence=1.0,
            blocks=[Block(text=text)],
        )
