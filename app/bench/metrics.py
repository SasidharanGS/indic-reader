"""Benchmark metrics: Character Error Rate and real-time factor (ARCHITECTURE.md §10).

Pure and dependency-free so they're unit-tested in CI without any models.
"""

from __future__ import annotations


def edit_distance(a: str, b: str) -> int:
    """Levenshtein edit distance between two strings."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
        previous = current
    return previous[-1]


def cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate: edit distance normalized by the reference length.

    0.0 is perfect. An empty reference scores 0.0 against empty output, else 1.0.
    """
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return edit_distance(reference, hypothesis) / len(reference)


def real_time_factor(processing_s: float, audio_s: float) -> float:
    """Processing seconds per second of audio produced. <1.0 is faster than realtime."""
    if audio_s <= 0:
        return float("inf")
    return processing_s / audio_s
