"""TTS provider contract (ARCHITECTURE.md §4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class Audio:
    """Synthesized audio — either in-memory samples or a path to a file."""

    sample_rate: int
    duration_s: float
    file_path: str | None = None
    samples: bytes | None = None


@runtime_checkable
class TTSProvider(Protocol):
    """Synthesizes speech. Implemented by indic_parler/indicf5/bulbul."""

    def synthesize(
        self, text: str, lang: str, voice: str | None = None, speed: float = 1.0
    ) -> Audio: ...
