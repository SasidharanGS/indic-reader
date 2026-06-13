"""Concatenate per-chunk clips into one (ARCHITECTURE.md §6).

Operates on raw in-memory samples with a shared sample rate — the model used by
the providers in this project. File-based mixing (if ever needed) would belong
behind the same function.
"""

from __future__ import annotations

from app.providers.tts.base import Audio


def concat(clips: list[Audio]) -> Audio:
    """Join clips in order; requires a consistent sample rate."""
    if not clips:
        raise ValueError("no audio clips to concatenate")

    sample_rate = clips[0].sample_rate
    if any(clip.sample_rate != sample_rate for clip in clips):
        raise ValueError("cannot concatenate clips with differing sample rates")

    samples = b"".join(clip.samples or b"" for clip in clips)
    duration = sum(clip.duration_s for clip in clips)
    return Audio(sample_rate=sample_rate, duration_s=duration, samples=samples)
