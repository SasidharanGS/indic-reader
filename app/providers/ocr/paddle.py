"""PaddleOCR-backed OCR provider (ARCHITECTURE.md §5).

Targets PaddleOCR **3.x** (the `models` extra pins `paddleocr>=3.7`). Heavy
dependencies (``paddleocr``, ``paddlepaddle``, ``pillow``) are imported lazily
and are NOT part of the base install, so importing this module — and the
registry — stays cheap and CI needs no models. Install them with::

    uv sync --extra models

Selecting ``OCR_BACKEND=paddle`` without them raises
:class:`~app.providers.errors.MissingBackendDependencyError` with this hint.
"""

from __future__ import annotations

import io

from app.providers.errors import MissingBackendDependencyError
from app.providers.ocr.base import Block, OCRResult

_INSTALL_HINT = "uv sync --extra models"

# Our language codes (from text.lang_detect) -> PaddleOCR recognizer codes.
_LANG_TO_PADDLE = {
    "hi": "devanagari",
    "mr": "devanagari",
    "ne": "devanagari",
    "ta": "ta",
    "te": "te",
    "kn": "ka",
    "ml": "ml",
    "bn": "bn",
    "en": "en",
}
_DEFAULT_PADDLE_LANG = "en"


def _poly_to_bbox(poly) -> tuple[int, int, int, int] | None:
    """Axis-aligned bounding box from a 4-point polygon (or None)."""
    if poly is None:
        return None
    xs = [int(point[0]) for point in poly]
    ys = [int(point[1]) for point in poly]
    return (min(xs), min(ys), max(xs), max(ys))


def _extract_lines(result_item) -> tuple[list[str], list[float], list]:
    """Return (texts, scores, polys) from one PaddleOCR result item.

    Handles PaddleOCR 3.x (dict-like with parallel ``rec_texts`` / ``rec_scores``
    / ``rec_polys`` lists) and falls back to the 2.x format (a list of
    ``[box, (text, score)]`` entries).
    """
    try:  # PaddleOCR 3.x
        texts = list(result_item["rec_texts"])
        scores = [float(score) for score in result_item["rec_scores"]]
        polys = result_item.get("rec_polys")
        if polys is None:
            polys = result_item.get("dt_polys")
        polys = list(polys) if polys is not None else [None] * len(texts)
        return texts, scores, polys
    except (KeyError, TypeError, IndexError):
        pass

    texts: list[str] = []  # PaddleOCR 2.x
    scores: list[float] = []
    polys: list = []
    for box, (text, score) in result_item or []:
        texts.append(text)
        scores.append(float(score))
        polys.append(box)
    return texts, scores, polys


class PaddleOCRProvider:
    """Extracts text with PaddleOCR; recognizer chosen from the language hint."""

    def __init__(self, lang: str = "en") -> None:
        self._default_lang = lang
        self._engine = None
        self._engine_lang: str | None = None

    def _build_engine(self, paddle_lang: str):
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise MissingBackendDependencyError(
                f"The 'paddle' OCR backend needs extra packages. Install with: {_INSTALL_HINT}"
            ) from exc
        # Disable the optional doc-orientation / unwarping / textline-orientation
        # models (3.x): they add latency + extra downloads we don't need for
        # upright printed pages.
        return PaddleOCR(
            lang=paddle_lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )

    def _engine_for(self, lang: str):
        paddle_lang = _LANG_TO_PADDLE.get(lang, _DEFAULT_PADDLE_LANG)
        if self._engine is None or self._engine_lang != paddle_lang:
            self._engine = self._build_engine(paddle_lang)
            self._engine_lang = paddle_lang
        return self._engine

    def _decode_image(self, image: bytes):
        try:
            import numpy as np
            from PIL import Image
        except ImportError as exc:
            raise MissingBackendDependencyError(
                f"The 'paddle' OCR backend needs extra packages. Install with: {_INSTALL_HINT}"
            ) from exc
        return np.array(Image.open(io.BytesIO(image)).convert("RGB"))

    def extract(self, image: bytes, lang_hint: str | None = None) -> OCRResult:
        lang = lang_hint or self._default_lang
        engine = self._engine_for(lang)
        array = self._decode_image(image)

        raw = engine.ocr(array)
        if not raw:
            return OCRResult(text="", lang=lang, confidence=0.0, blocks=[])

        texts, scores, polys = _extract_lines(raw[0])
        blocks: list[Block] = []
        for idx, text in enumerate(texts):
            poly = polys[idx] if idx < len(polys) else None
            blocks.append(Block(text=text, bbox=_poly_to_bbox(poly)))

        # Reading order: top-to-bottom, then left-to-right (ARCHITECTURE §7).
        blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]) if b.bbox else (0, 0))
        text = "\n".join(block.text for block in blocks)
        confidence = sum(scores) / len(scores) if scores else 0.0
        return OCRResult(text=text, lang=lang, confidence=confidence, blocks=blocks)
