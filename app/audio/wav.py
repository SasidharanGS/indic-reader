"""Encode an Audio clip to in-memory WAV bytes (16-bit PCM, mono)."""

from __future__ import annotations

import io
import wave
from pathlib import Path

from app.providers.tts.base import Audio

DEFAULT_SAMPLE_RATE = 16_000


def to_wav_bytes(audio: Audio) -> bytes:
    """Serialize ``audio`` (16-bit PCM samples) into a WAV container."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit PCM
        wav.setframerate(audio.sample_rate or DEFAULT_SAMPLE_RATE)
        wav.writeframes(audio.samples or b"")
    return buffer.getvalue()


def read_wav(path: str | Path) -> Audio:
    """Load a 16-bit PCM mono WAV file into an :class:`Audio` clip."""
    with wave.open(str(path), "rb") as wav:
        sample_rate = wav.getframerate()
        n_frames = wav.getnframes()
        frames = wav.readframes(n_frames)
    duration = n_frames / sample_rate if sample_rate else 0.0
    return Audio(sample_rate=sample_rate, duration_s=duration, samples=frames)
