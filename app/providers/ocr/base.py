"""OCR provider contract (ARCHITECTURE.md §4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class Block:
    """A positioned text block within a page image."""

    text: str
    bbox: tuple[int, int, int, int] | None = None  # (x0, y0, x1, y1)


@dataclass
class OCRResult:
    """Recognized text for one image."""

    text: str
    lang: str
    confidence: float
    blocks: list[Block] = field(default_factory=list)


@runtime_checkable
class OCRProvider(Protocol):
    """Extracts text from an image. Implemented by paddle/surya/sarvam_vision."""

    def extract(self, image: bytes, lang_hint: str | None = None) -> OCRResult: ...
