"""PaddleOCR-backed OCR provider (ARCHITECTURE.md §5).

Heavy dependencies (``paddleocr``, ``paddlepaddle``, ``pillow``) are imported
lazily and are NOT part of the base install, so importing this module — and the
registry — stays cheap and CI needs no models. Install them into the project
venv to use this backend::

    uv pip install paddleocr paddlepaddle pillow

Selecting ``OCR_BACKEND=paddle`` without them raises
:class:`~app.providers.errors.MissingBackendDependencyError` with this hint.

Note: PaddleOCR's API and language set vary across versions; verify/pin locally.
"""

from __future__ import annotations

import io

from app.providers.errors import MissingBackendDependencyError
from app.providers.ocr.base import Block, OCRResult

_INSTALL_HINT = "uv pip install paddleocr paddlepaddle pillow"

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
        return PaddleOCR(use_angle_cls=True, lang=paddle_lang)

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

        # PaddleOCR returns one list of lines per image: [[ [box, (text, conf)], ... ]].
        raw = engine.ocr(array, cls=True)
        lines = raw[0] if raw and raw[0] else []

        blocks: list[Block] = []
        confidences: list[float] = []
        for box, (text, conf) in lines:
            xs = [int(point[0]) for point in box]
            ys = [int(point[1]) for point in box]
            blocks.append(Block(text=text, bbox=(min(xs), min(ys), max(xs), max(ys))))
            confidences.append(float(conf))

        # Reading order: top-to-bottom, then left-to-right (ARCHITECTURE §7).
        blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]) if b.bbox else (0, 0))
        text = "\n".join(block.text for block in blocks)
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return OCRResult(text=text, lang=lang, confidence=confidence, blocks=blocks)
