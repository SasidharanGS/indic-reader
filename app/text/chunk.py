"""Sentence splitting and chunking for TTS (ARCHITECTURE.md §7).

Splits on the Devanagari danda (``।``) / double danda (``॥``) and standard
punctuation, then packs sentences into chunks under a char limit so each fits a
TTS backend's request size. Sentences are never split unless a single sentence
alone exceeds the limit.
"""

from __future__ import annotations

import re

# Default keeps a margin under Bulbul's 2500-char REST limit (ARCHITECTURE §5).
DEFAULT_MAX_CHARS = 2000

# Split after sentence-ending punctuation followed by whitespace.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[।॥.!?])\s+")


def split_sentences(text: str) -> list[str]:
    """Split text into trimmed, non-empty sentences."""
    text = text.strip()
    if not text:
        return []
    return [part.strip() for part in _SENTENCE_BOUNDARY.split(text) if part.strip()]


def chunk(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Pack sentences into chunks no longer than ``max_chars``."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    chunks: list[str] = []
    current = ""
    for sentence in split_sentences(text):
        # Hard-split a single sentence that is itself too long.
        while len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        if not sentence:
            continue

        if not current:
            current = sentence
        elif len(current) + 1 + len(sentence) <= max_chars:
            current = f"{current} {sentence}"
        else:
            chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)
    return chunks
