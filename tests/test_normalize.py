import unicodedata

from app.text.normalize import normalize


def test_nfc_composes_decomposed_sequence():
    decomposed = "é"  # 'e' + combining acute accent
    result = normalize(decomposed)
    assert result == "é"
    assert len(result) == 1


def test_normalize_is_idempotent():
    text = "नमस्ते"
    once = normalize(text)
    assert normalize(once) == once
    assert unicodedata.is_normalized("NFC", once)
