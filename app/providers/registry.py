"""Config-driven factory mapping backend strings to provider implementations.

Wired so far: ``mock`` plus the M1 defaults ``paddle`` (OCR) and ``indic_parler``
(TTS). Remaining backends (surya, sarvam_vision, indicf5, bulbul) arrive in later
milestones; selecting an unwired one fails loudly with :class:`UnknownBackendError`.
A wired backend whose optional heavy dependencies are not installed raises
:class:`~app.providers.errors.MissingBackendDependencyError` when first used.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.providers.ocr.base import OCRProvider
from app.providers.ocr.mock import MockOCRProvider
from app.providers.ocr.paddle import PaddleOCRProvider
from app.providers.tts.base import TTSProvider
from app.providers.tts.bulbul import BulbulProvider
from app.providers.tts.indic_parler import IndicParlerProvider
from app.providers.tts.mock import MockTTSProvider

_OCR_PROVIDERS: dict[str, type] = {
    "mock": MockOCRProvider,
    "paddle": PaddleOCRProvider,
}

_TTS_PROVIDERS: dict[str, type] = {
    "mock": MockTTSProvider,
    "indic_parler": IndicParlerProvider,
    "bulbul": BulbulProvider,
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
