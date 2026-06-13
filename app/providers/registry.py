"""Config-driven factory mapping backend strings to provider implementations.

Concrete ML providers (paddle, surya, sarvam_vision, indic_parler, indicf5,
bulbul) arrive in later milestones. Until a backend is wired here, selecting it
fails loudly with :class:`UnknownBackendError` rather than silently degrading.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.providers.ocr.base import OCRProvider
from app.providers.ocr.mock import MockOCRProvider
from app.providers.tts.base import TTSProvider
from app.providers.tts.mock import MockTTSProvider

_OCR_PROVIDERS: dict[str, type] = {
    "mock": MockOCRProvider,
}

_TTS_PROVIDERS: dict[str, type] = {
    "mock": MockTTSProvider,
}


class UnknownBackendError(ValueError):
    """A configured backend has no registered implementation (yet)."""


def _select(name: str, table: dict[str, type], kind: str):
    try:
        factory = table[name]
    except KeyError:
        available = ", ".join(sorted(table)) or "(none)"
        raise UnknownBackendError(
            f"{kind} backend {name!r} is not implemented yet. Available: {available}."
        ) from None
    return factory()


def get_ocr_provider(name: str | None = None, settings: Settings | None = None) -> OCRProvider:
    settings = settings or get_settings()
    return _select(name or settings.ocr_backend, _OCR_PROVIDERS, "OCR")


def get_tts_provider(name: str | None = None, settings: Settings | None = None) -> TTSProvider:
    settings = settings or get_settings()
    return _select(name or settings.tts_backend, _TTS_PROVIDERS, "TTS")
