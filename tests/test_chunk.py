import pytest

from app.text.chunk import chunk, split_sentences


def test_split_on_period_and_danda():
    assert split_sentences("One. Two. Three.") == ["One.", "Two.", "Three."]
    assert split_sentences("पहला। दूसरा।") == ["पहला।", "दूसरा।"]


def test_split_empty():
    assert split_sentences("   ") == []


def test_chunk_packs_under_limit():
    text = "aaaa. bbbb. cccc. dddd."  # four 5-char sentences (incl. period)
    chunks = chunk(text, max_chars=12)
    assert all(len(c) <= 12 for c in chunks)
    assert chunks == ["aaaa. bbbb.", "cccc. dddd."]


def test_chunk_does_not_split_normal_sentences():
    text = "Hello there. General Kenobi."
    chunks = chunk(text, max_chars=100)
    assert chunks == ["Hello there. General Kenobi."]


def test_long_single_sentence_is_hard_split():
    sentence = "x" * 25  # no boundary, exceeds limit
    chunks = chunk(sentence, max_chars=10)
    assert all(len(c) <= 10 for c in chunks)
    assert "".join(chunks) == sentence


def test_invalid_max_chars():
    with pytest.raises(ValueError):
        chunk("text", max_chars=0)
