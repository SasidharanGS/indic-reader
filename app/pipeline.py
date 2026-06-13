"""Pipeline orchestrator: image -> OCR -> text -> TTS -> audio (ARCHITECTURE.md §6).

Glues the provider interfaces and the text pipeline into the headline loop.
Concrete OCR/TTS backends are resolved from config via the registry, so this
code never names a model — run it against the ``mock`` backends and it works
end-to-end without any heavy dependencies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.audio.cache import AudioCache, chunk_key
from app.audio.concat import concat
from app.config import Settings, get_settings
from app.providers.ocr.base import OCRProvider
from app.providers.registry import get_ocr_provider, get_tts_provider
from app.providers.tts.base import Audio, TTSProvider
from app.text import DEFAULT_MAX_CHARS, chunk, clean, detect_lang, normalize

logger = logging.getLogger(__name__)


@dataclass
class PageResult:
    """Outcome of running one image through the pipeline."""

    text: str
    lang: str
    chunks: list[str]
    audio: Audio | None
    cache_hits: int
    tts_error: str | None = None


class Pipeline:
    """Orchestrates a single image into recognized text and synthesized audio."""

    def __init__(
        self,
        ocr: OCRProvider | None = None,
        tts: TTSProvider | None = None,
        settings: Settings | None = None,
        cache: AudioCache | None = None,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> None:
        self.settings = settings or get_settings()
        self.ocr = ocr or get_ocr_provider(settings=self.settings)
        self.tts = tts or get_tts_provider(settings=self.settings)
        self.cache = cache if cache is not None else AudioCache()
        self.max_chars = max_chars

    def run(
        self,
        image: bytes,
        lang_hint: str | None = None,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> PageResult:
        ocr_result = self.ocr.extract(image, lang_hint=lang_hint)
        text = clean(ocr_result.text)
        lang = lang_hint or detect_lang(text)
        text = normalize(text, lang)
        chunks = chunk(text, max_chars=self.max_chars)

        backend = self.settings.tts_backend
        clips: list[Audio] = []
        cache_hits = 0
        tts_error: str | None = None
        try:
            for piece in chunks:
                key = chunk_key(piece, voice, backend, speed)
                cached = self.cache.get(key)
                if cached is not None:
                    cache_hits += 1
                    clips.append(cached)
                    continue
                clip = self.tts.synthesize(piece, lang=lang, voice=voice, speed=speed)
                self.cache.set(key, clip)
                clips.append(clip)
        except Exception as exc:
            # Degrade gracefully: keep the recognized text (ARCHITECTURE §13).
            logger.warning("TTS failed (%s); returning text only: %s", type(exc).__name__, exc)
            tts_error = str(exc)
            clips = []
            cache_hits = 0

        audio = concat(clips) if clips else None
        return PageResult(
            text=text,
            lang=lang,
            chunks=chunks,
            audio=audio,
            cache_hits=cache_hits,
            tts_error=tts_error,
        )
