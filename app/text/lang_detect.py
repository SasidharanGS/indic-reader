"""Script/language detection via Unicode-block heuristics (ARCHITECTURE.md §7).

No model or external dependency: count characters per script block and pick the
dominant one. Good enough to route OCR recognizers and TTS languages; ambiguous
Latin is treated as English.
"""

from __future__ import annotations

from collections import Counter

# Unicode ranges for the scripts we route on.
_SCRIPT_RANGES: dict[str, tuple[int, int]] = {
    "devanagari": (0x0900, 0x097F),
    "bengali": (0x0980, 0x09FF),
    "gurmukhi": (0x0A00, 0x0A7F),
    "gujarati": (0x0A80, 0x0AFF),
    "oriya": (0x0B00, 0x0B7F),
    "tamil": (0x0B80, 0x0BFF),
    "telugu": (0x0C00, 0x0C7F),
    "kannada": (0x0C80, 0x0CFF),
    "malayalam": (0x0D00, 0x0D7F),
}

_SCRIPT_TO_LANG: dict[str, str] = {
    "devanagari": "hi",
    "bengali": "bn",
    "gurmukhi": "pa",
    "gujarati": "gu",
    "oriya": "or",
    "tamil": "ta",
    "telugu": "te",
    "kannada": "kn",
    "malayalam": "ml",
    "latin": "en",
}


def _script_counts(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for ch in text:
        if ch.isascii() and ch.isalpha():
            counts["latin"] += 1
            continue
        cp = ord(ch)
        for name, (lo, hi) in _SCRIPT_RANGES.items():
            if lo <= cp <= hi:
                counts[name] += 1
                break
    return counts


def detect_script(text: str) -> str:
    """Return the dominant script name; Indic scripts win ties over Latin."""
    counts = _script_counts(text)
    if not counts:
        return "latin"
    return max(counts, key=lambda s: (counts[s], s != "latin"))


def detect_lang(text: str) -> str:
    """Return a language code for the dominant script (``en`` when none/Latin)."""
    return _SCRIPT_TO_LANG.get(detect_script(text), "en")


def is_code_mixed(text: str) -> bool:
    """True when the text mixes Latin with at least one Indic script."""
    counts = _script_counts(text)
    has_latin = counts.get("latin", 0) > 0
    has_indic = any(name != "latin" and n > 0 for name, n in counts.items())
    return has_latin and has_indic
