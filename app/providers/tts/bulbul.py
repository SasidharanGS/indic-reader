"""Sarvam Bulbul TTS provider (ARCHITECTURE.md §5).

HTTP adapter over Sarvam's sovereign TTS API:
``POST https://api.sarvam.ai/text-to-speech`` with an ``api-subscription-key``
header; the response returns base64-encoded WAV in ``audios[0]``. Requires
``SARVAM_API_KEY``. ``httpx`` is imported lazily so importing the registry stays
cheap. See https://docs.sarvam.ai/api-reference-docs/text-to-speech/convert
"""

from __future__ import annotations

import base64
import io
import wave

from app.audio.concat import concat
from app.config import get_settings
from app.providers.errors import ModelAccessError
from app.providers.tts.base import Audio
from app.text import chunk

ENDPOINT = "https://api.sarvam.ai/text-to-speech"
# Bulbul v3 accepts up to 2500 chars per request; keep a margin.
MAX_CHARS = 2400

# Our language codes -> Sarvam BCP-47 target_language_code.
_LANG_TO_BCP47 = {
    "hi": "hi-IN",
    "bn": "bn-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "or": "od-IN",
    "pa": "pa-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "gu": "gu-IN",
    "en": "en-IN",
}


def _target_language(lang: str) -> str:
    return _LANG_TO_BCP47.get(lang, "en-IN")


def _payload(text: str, lang: str, speaker: str, speed: float, model: str) -> dict:
    return {
        "text": text,
        "target_language_code": _target_language(lang),
        "speaker": speaker,
        "model": model,
        "pace": speed,
    }


def _decode_wav_base64(encoded: str) -> Audio:
    raw = base64.b64decode(encoded)
    with wave.open(io.BytesIO(raw), "rb") as wav:
        sample_rate = wav.getframerate()
        n_frames = wav.getnframes()
        frames = wav.readframes(n_frames)
    duration = n_frames / sample_rate if sample_rate else 0.0
    return Audio(sample_rate=sample_rate, duration_s=duration, samples=frames)


def _httpx_client():
    import httpx

    return httpx.Client(timeout=60.0)


class BulbulProvider:
    """Synthesizes speech via Sarvam Bulbul; an HTTP API (no local model)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "bulbul:v2",
        speaker: str = "anushka",
        session=None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._speaker = speaker
        self._session = session  # anything with .post(url, headers=, json=); default httpx

    def synthesize(
        self, text: str, lang: str, voice: str | None = None, speed: float = 1.0
    ) -> Audio:
        api_key = self._api_key or get_settings().sarvam_api_key
        if not api_key:
            raise ModelAccessError(
                "The 'bulbul' TTS backend needs a Sarvam API key. Set SARVAM_API_KEY in .env."
            )

        pieces = chunk(text, max_chars=MAX_CHARS) or [text]
        session = self._session or _httpx_client()
        speaker = voice or self._speaker
        headers = {"api-subscription-key": api_key}

        clips: list[Audio] = []
        for piece in pieces:
            response = session.post(
                ENDPOINT, headers=headers, json=_payload(piece, lang, speaker, speed, self._model)
            )
            response.raise_for_status()
            clips.append(_decode_wav_base64(response.json()["audios"][0]))

        return clips[0] if len(clips) == 1 else concat(clips)
