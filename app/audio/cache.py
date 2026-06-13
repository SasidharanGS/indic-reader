"""Per-chunk synthesis cache (ARCHITECTURE.md §8).

Keyed by ``hash(text + voice + backend + speed)`` so identical chunks are never
re-synthesized — on replay or across backend experiments. This M1 cache is
in-memory; a file-backed cache arrives with book mode (M3).
"""

from __future__ import annotations

import hashlib

from app.providers.tts.base import Audio


def chunk_key(text: str, voice: str | None, backend: str, speed: float) -> str:
    """Stable cache key for one synthesized chunk."""
    raw = "\x00".join([backend, voice or "", f"{speed:g}", text]).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class AudioCache:
    """A minimal in-memory cache of synthesized clips."""

    def __init__(self) -> None:
        self._store: dict[str, Audio] = {}

    def get(self, key: str) -> Audio | None:
        return self._store.get(key)

    def set(self, key: str, audio: Audio) -> None:
        self._store[key] = audio

    def __contains__(self, key: str) -> bool:
        return key in self._store

    def __len__(self) -> int:
        return len(self._store)
