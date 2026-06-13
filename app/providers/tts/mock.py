"""A model-free TTS provider for tests and pipeline smoke runs."""

from __future__ import annotations

from app.providers.tts.base import Audio


class MockTTSProvider:
    """Returns a tiny empty clip whose duration scales with text length."""

    SAMPLE_RATE = 16_000

    def synthesize(
        self, text: str, lang: str, voice: str | None = None, speed: float = 1.0
    ) -> Audio:
        duration = max(0.1, len(text) / 16.0 / max(speed, 0.1))
        return Audio(sample_rate=self.SAMPLE_RATE, duration_s=duration, samples=b"")
