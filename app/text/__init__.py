"""Deterministic text processing: clean → detect language → chunk → normalize.

See ARCHITECTURE.md §7. Intentionally dependency-light so it runs fast in CI.
"""

from app.text.chunk import DEFAULT_MAX_CHARS, chunk, split_sentences
from app.text.clean import clean
from app.text.lang_detect import detect_lang, detect_script, is_code_mixed
from app.text.normalize import normalize

__all__ = [
    "DEFAULT_MAX_CHARS",
    "chunk",
    "clean",
    "detect_lang",
    "detect_script",
    "is_code_mixed",
    "normalize",
    "split_sentences",
]
