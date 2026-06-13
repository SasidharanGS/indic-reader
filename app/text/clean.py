"""Cleanup of raw OCR text (ARCHITECTURE.md §7).

Conservative, single-page heuristics: de-hyphenate line wraps, drop standalone
page-number lines, and collapse whitespace. Cross-page header/footer detection
is deferred to book mode (M3), where multi-page context is available.
"""

from __future__ import annotations

import re

_HYPHEN_WRAP = re.compile(r"(\w)-\n\s*(\w)")
_PAGE_NUM_LINE = re.compile(r"^\s*(?:page\s+)?\d{1,4}\s*$", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


def dehyphenate(text: str) -> str:
    """Join words split by a hyphen at a line break (``exam-\\nple`` -> ``example``)."""
    return _HYPHEN_WRAP.sub(r"\1\2", text)


def strip_page_numbers(text: str) -> str:
    """Drop lines that are just a page number or ``Page N``."""
    lines = text.splitlines()
    return "\n".join(line for line in lines if not _PAGE_NUM_LINE.match(line))


def collapse_whitespace(text: str) -> str:
    """Collapse any run of whitespace to a single space and trim."""
    return _WHITESPACE.sub(" ", text).strip()


def clean(text: str) -> str:
    """Run the full cleanup pass (order matters: line-structure steps first)."""
    text = dehyphenate(text)
    text = strip_page_numbers(text)
    return collapse_whitespace(text)
