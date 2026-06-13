"""Text normalization before synthesis (ARCHITECTURE.md §7).

For now: Unicode NFC normalization (important for Indic combining characters so
the same grapheme has one canonical code-point sequence). Number/abbreviation
expansion is a documented hook for later, per-language work; code-mix is
preserved untouched.
"""

from __future__ import annotations

import unicodedata


def normalize(text: str, lang: str = "en") -> str:
    """Return NFC-normalized text. ``lang`` reserved for future expansion rules."""
    return unicodedata.normalize("NFC", text)
